from rest_framework import serializers

from .models import Diagnosis, Disease, Plant, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "username", "role", "created_at")
        read_only_fields = ("id", "role", "created_at")


class UserSyncSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plant
        fields = ("id", "name_en", "name_ar", "description_en", "description_ar")


class DiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disease
        fields = (
            "id",
            "plant",
            "name_en",
            "name_ar",
            "description_en",
            "description_ar",
            "causes_en",
            "causes_ar",
            "treatment_en",
            "treatment_ar",
        )


class DiagnosisCreateSerializer(serializers.Serializer):
    input_type = serializers.ChoiceField(choices=["image", "text"])
    text_input = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    image_url = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2048,
    )
    plant_id = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        it = attrs["input_type"]
        text = (attrs.get("text_input") or "").strip()
        img = (attrs.get("image_url") or "").strip()
        if it == "text" and not text:
            raise serializers.ValidationError(
                {"text_input": "Required when input_type is text."}
            )
        if it == "image" and not img:
            raise serializers.ValidationError(
                {"image_url": "Required when input_type is image."}
            )
        if it == "text" and img:
            raise serializers.ValidationError(
                {"image_url": "Must be empty when input_type is text."}
            )
        if it == "image" and text:
            raise serializers.ValidationError(
                {"text_input": "Must be empty when input_type is image."}
            )
        return attrs


class DiagnosisReadSerializer(serializers.ModelSerializer):
    disease = DiseaseSerializer(read_only=True)

    class Meta:
        model = Diagnosis
        fields = (
            "id",
            "user",
            "disease",
            "input_type",
            "image_url",
            "text_input",
            "confidence_score",
            "created_at",
        )
        read_only_fields = fields
