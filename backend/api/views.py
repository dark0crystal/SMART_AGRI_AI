import json
from html import escape

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .ai_service import (
    VisionDependenciesMissing,
    get_default_lemon_plant,
    predict_lemon_disease,
    predict_lemon_uploaded_image,
)
from .firestore_repository import (
    create_diagnosis_with_log,
    get_diagnosis_for_user,
    get_disease_by_id,
    get_disease_for_plant,
    get_plant,
    get_user,
    list_all_plants,
    list_diagnoses_for_user,
    list_diseases_for_plant,
    update_disease_fields,
    update_plant_fields,
    upsert_user,
)
from .serializers import (
    DiagnosisCreateSerializer,
    DiagnosisReadSerializer,
    DiseaseCatalogWriteSerializer,
    DiseaseSerializer,
    PlantCatalogWriteSerializer,
    PlantSerializer,
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

    try:
        user, created = upsert_user(uid=uid, email=email, username=username)
    except ValueError:
        return Response(
            {"detail": "This email is already linked to another account."},
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
    user = get_user(uid)
    if not user:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(UserSerializer(user).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def diagnoses_list(request):
    """
    GET: paginated list of the caller's diagnoses.

    POST: create a diagnosis. Image input runs the PyTorch checkpoint (`VISION_MODEL_PATH`);
    text input runs TF-IDF cosine similarity against disease descriptions (`tfidf_v1` in ai_logs).
    """
    uid = getattr(request.user, "uid", None)
    if not uid:
        return Response(
            {"detail": "Invalid auth: missing uid."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    user = get_user(uid)
    if not user:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        try:
            page_number = int(request.query_params.get("page", "1") or "1")
        except ValueError:
            page_number = 1
        if page_number < 1:
            page_number = 1
        page_size = int(getattr(settings, "REST_FRAMEWORK", {}).get("PAGE_SIZE", 20))
        payload = list_diagnoses_for_user(user_id=uid, page=page_number, page_size=page_size)
        base = request.build_absolute_uri(request.path)
        if payload["next"] is not None:
            payload["next"] = f"{base}?page={payload['next']}"
        else:
            payload["next"] = None
        if payload["previous"] is not None:
            payload["previous"] = f"{base}?page={payload['previous']}"
        else:
            payload["previous"] = None
        ser = DiagnosisReadSerializer(payload["results"], many=True)
        return Response(
            {
                "count": payload["count"],
                "next": payload["next"],
                "previous": payload["previous"],
                "results": ser.data,
            }
        )

    ser = DiagnosisCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data
    plant_id = data.get("plant_id")
    if plant_id is None:
        lemon = get_default_lemon_plant()
        if not lemon:
            return Response(
                {"detail": "Lemon catalog is not seeded in Firestore."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plant_id = int(lemon["id"])
    else:
        plant = get_plant(plant_id)
        if not plant:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

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
    except VisionDependenciesMissing as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    disease = get_disease_for_plant(plant_id=plant_id, disease_id=int(pred["disease_id"]))
    if not disease:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    diagnosis = create_diagnosis_with_log(
        user_id=uid,
        disease=disease,
        input_type=it,
        image_url=image_url or None,
        text_input=text_input or None,
        confidence_score=float(pred["confidence"]),
        raw_debug=pred["raw_debug"],
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
    user = get_user(uid)
    if not user:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    diagnosis = get_diagnosis_for_user(user_id=uid, diagnosis_id=pk)
    if not diagnosis:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(DiagnosisReadSerializer(diagnosis).data)


def _admin_error_response(request) -> Response | None:
    """If the Firebase user is not an admin, return an error Response; else None."""
    uid = getattr(request.user, "uid", None)
    if not uid:
        return Response(
            {"detail": "Invalid auth: missing uid."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    user = get_user(uid)
    if not user:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    if (user.get("role") or "user").lower() != "admin":
        return Response(
            {"detail": "Administrator role required."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_catalog_plants(request):
    err = _admin_error_response(request)
    if err is not None:
        return err
    plants = list_all_plants()
    return Response({"results": PlantSerializer(plants, many=True).data})


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def admin_catalog_plant_detail(request, plant_id):
    err = _admin_error_response(request)
    if err is not None:
        return err
    if request.method == "GET":
        plant = get_plant(plant_id)
        if not plant:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PlantSerializer(plant).data)
    ser = PlantCatalogWriteSerializer(data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    if not ser.validated_data:
        return Response(
            {"detail": "No valid fields to update."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    updated = update_plant_fields(plant_id, dict(ser.validated_data))
    if not updated:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(PlantSerializer(updated).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_catalog_plant_diseases(request, plant_id):
    err = _admin_error_response(request)
    if err is not None:
        return err
    plant = get_plant(plant_id)
    if not plant:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    rows = list_diseases_for_plant(plant_id)
    return Response(
        {
            "plant": PlantSerializer(plant).data,
            "results": rows,
        }
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def admin_catalog_disease_detail(request, disease_id):
    err = _admin_error_response(request)
    if err is not None:
        return err
    if request.method == "GET":
        row = get_disease_by_id(disease_id)
        if not row:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        plant = get_plant(int(row["plant"])) if row.get("plant") else None
        nested = {**row, "plant": plant} if plant else row
        return Response(DiseaseSerializer(_disease_nested_payload(nested)).data)

    ser = DiseaseCatalogWriteSerializer(data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    if not ser.validated_data:
        return Response(
            {"detail": "No valid fields to update."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    updated = update_disease_fields(disease_id, dict(ser.validated_data))
    if not updated:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    plant = (
        get_plant(int(updated["plant"]))
        if updated.get("plant")
        else None
    )
    nested = {**updated, "plant": plant} if plant else updated
    return Response(DiseaseSerializer(_disease_nested_payload(nested)).data)


def _disease_nested_payload(row: dict) -> dict:
    """Shape expected by DiseaseSerializer (plant nested)."""
    plant = row.get("plant")
    if isinstance(plant, dict):
        return row
    pid = row.get("plant")
    if pid is None:
        return {**row, "plant": None}
    p = get_plant(int(pid))
    return {**row, "plant": p}


@csrf_exempt
def vision_test_page(request):
    """
    Debug-only web UI to test image inference and Witch's Broom guard behavior.
    """
    if not settings.DEBUG:
        return HttpResponse("Not found.", status=404)

    result_html = ""
    error_html = ""

    if request.method == "POST":
        f = request.FILES.get("image")
        if not f:
            error_html = "<p style='color:#b00020;'>Please choose an image file.</p>"
        else:
            try:
                out = predict_lemon_uploaded_image(image_bytes=f.read())
                raw = json.loads(out["raw_debug"])
                top_k = raw.get("top_k", [])
                guard = raw.get("witch_broom_guard", {})
                rows = "".join(
                    f"<tr><td>{escape(str(i + 1))}</td><td>{escape(str(row.get('name')))}</td>"
                    f"<td>{float(row.get('prob', 0.0)):.4f}</td></tr>"
                    for i, row in enumerate(top_k)
                )
                result_html = f"""
                <h3>Prediction Result</h3>
                <p><b>Chosen disease:</b> {escape(str(out.get('chosen_disease')))}</p>
                <p><b>Confidence (top-1 prob):</b> {float(out.get('confidence', 0.0)):.4f}</p>
                <p><b>Witch's Broom guard:</b> {escape(str(guard))}</p>
                <table border="1" cellpadding="8" cellspacing="0">
                  <thead><tr><th>Rank</th><th>Class</th><th>Probability</th></tr></thead>
                  <tbody>{rows}</tbody>
                </table>
                <details style="margin-top:12px;">
                  <summary>Raw debug JSON</summary>
                  <pre>{escape(json.dumps(raw, indent=2, ensure_ascii=False))}</pre>
                </details>
                """
            except VisionDependenciesMissing as exc:
                error_html = f"<p style='color:#b00020;'>{escape(str(exc))}</p>"
            except ValueError as exc:
                error_html = f"<p style='color:#b00020;'>{escape(str(exc))}</p>"
            except Exception as exc:
                error_html = f"<p style='color:#b00020;'>Unexpected error: {escape(str(exc))}</p>"

    html = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Vision Model Test</title>
      </head>
      <body style="font-family: Arial, sans-serif; margin: 24px; max-width: 900px;">
        <h2>Vision Model Test (Debug)</h2>
        <p>Upload an image to test backend inference and Witch's Broom condition.</p>
        <form method="post" enctype="multipart/form-data">
          <input type="file" name="image" accept="image/*" required />
          <button type="submit" style="margin-left:8px;">Run Prediction</button>
        </form>
        <hr />
        {error_html}
        {result_html}
      </body>
    </html>
    """
    return HttpResponse(html)
