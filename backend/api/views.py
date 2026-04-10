from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .ai_service import get_default_lemon_plant, predict_lemon_disease
from .models import AILog, Diagnosis, Disease, Plant, User
from .serializers import (
    DiagnosisCreateSerializer,
    DiagnosisReadSerializer,
    UserSerializer,
    UserSyncSerializer,
)
from .storage_validation import is_allowed_storage_image_url


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "service": "smart-agri-api"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sync_user(request):
    """
    Upsert `users` row from Firebase ID token (Bearer).
    Optional body: {"username": "..."} applied on create or when provided.
    """
    uid = getattr(request.user, "uid", None)
    raw_email = getattr(request.user, "email", None)
    if not uid:
        return Response(
            {"detail": "Invalid auth: missing uid."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    # Anonymous / guest Firebase users have no email — use a stable synthetic address.
    email = (raw_email or "").strip().lower() or f"{uid}@guest.local"

    ser = UserSyncSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    username = ser.validated_data.get("username")

    user, created = User.objects.get_or_create(
        pk=uid,
        defaults={
            "email": email,
            "username": username or None,
        },
    )

    if not created:
        user.email = email
        if username is not None:
            user.username = username or None
        try:
            user.save(update_fields=["email", "username"])
        except IntegrityError:
            return Response(
                {
                    "detail": "This email is already linked to another account.",
                },
                status=status.HTTP_409_CONFLICT,
            )
    else:
        try:
            user.save()
        except IntegrityError:
            return Response(
                {
                    "detail": "This email is already linked to another account.",
                },
                status=status.HTTP_409_CONFLICT,
            )

    return Response(
        UserSerializer(user).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    uid = getattr(request.user, "uid", None)
    if not uid:
        return Response(
            {"detail": "Invalid auth: missing uid."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    user = get_object_or_404(User, pk=uid)
    return Response(UserSerializer(user).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def diagnoses_list(request):
    """List diagnoses (GET) or create via AI stub (POST)."""
    uid = getattr(request.user, "uid", None)
    if not uid:
        return Response(
            {"detail": "Invalid auth: missing uid."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    user = get_object_or_404(User, pk=uid)

    if request.method == "GET":
        qs = (
            Diagnosis.objects.filter(user=user)
            .select_related("disease", "disease__plant")
            .order_by("-created_at")
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        ser = DiagnosisReadSerializer(page, many=True)
        return paginator.get_paginated_response(ser.data)

    ser = DiagnosisCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data
    plant_id = data.get("plant_id")
    if plant_id is None:
        lemon = get_default_lemon_plant()
        if not lemon:
            return Response(
                {"detail": "Lemon catalog is not seeded. Run migrations."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plant_id = lemon.id
    else:
        get_object_or_404(Plant, pk=plant_id)

    it = data["input_type"]
    text_input = (data.get("text_input") or "").strip()
    image_url = (data.get("image_url") or "").strip()

    if it == "image" and not is_allowed_storage_image_url(image_url):
        return Response(
            {"detail": "Invalid or disallowed image URL (use Firebase Storage https URL)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        pred = predict_lemon_disease(
            plant_id=plant_id,
            input_type=it,
            text_input=text_input or None,
            image_url=image_url or None,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    disease = get_object_or_404(
        Disease.objects.filter(plant_id=plant_id),
        pk=pred["disease_id"],
    )

    with transaction.atomic():
        diagnosis = Diagnosis.objects.create(
            user=user,
            disease=disease,
            input_type=it,
            image_url=image_url or None,
            text_input=text_input or None,
            confidence_score=pred["confidence"],
        )
        AILog.objects.create(
            diagnosis=diagnosis,
            input_data=pred["raw_debug"],
            predicted_disease=disease.name_en,
            confidence_score=pred["confidence"],
        )

    out = DiagnosisReadSerializer(diagnosis)
    return Response(out.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def diagnoses_detail(request, pk):
    uid = getattr(request.user, "uid", None)
    if not uid:
        return Response(
            {"detail": "Invalid auth: missing uid."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    user = get_object_or_404(User, pk=uid)
    diagnosis = get_object_or_404(
        Diagnosis.objects.select_related("disease", "disease__plant"),
        pk=pk,
        user=user,
    )
    return Response(DiagnosisReadSerializer(diagnosis).data)
