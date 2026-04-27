from rest_framework import serializers

class UserSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    username = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    role = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True, allow_null=True)


class UserSyncSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class PlantSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name_en = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    name_ar = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    description_en = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    description_ar = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)


class DiseaseCatalogWriteSerializer(serializers.Serializer):
    """Admin PATCH: optional bilingual fields (omit keys you do not change)."""

    name_en = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    name_ar = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description_en = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description_ar = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    causes_en = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    causes_ar = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    treatment_en = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    treatment_ar = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class PlantCatalogWriteSerializer(serializers.Serializer):
    name_en = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    name_ar = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description_en = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description_ar = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class DiseaseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    plant = PlantSerializer(read_only=True, allow_null=True)
    name_en = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    name_ar = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    description_en = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    description_ar = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    causes_en = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    causes_ar = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    treatment_en = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    treatment_ar = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)


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


class DiagnosisReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user = serializers.CharField(read_only=True)
    disease = DiseaseSerializer(read_only=True)
    input_type = serializers.ChoiceField(choices=["image", "text"], read_only=True)
    image_url = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    text_input = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    confidence_score = serializers.FloatField(read_only=True, allow_null=True)
    created_at = serializers.CharField(read_only=True, allow_null=True)
