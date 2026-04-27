from django.db import models


class User(models.Model):
    """App user keyed by Firebase UID (`users` table)."""

    class Role(models.TextChoices):
        USER = "user", "user"
        ADMIN = "admin", "admin"

    id = models.CharField(max_length=128, primary_key=True)
    email = models.EmailField(max_length=255, unique=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"


class Plant(models.Model):
    """Bilingual plant catalog (`plants` table)."""

    name_en = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255)
    description_en = models.TextField(blank=True, null=True)
    description_ar = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plants"


class Disease(models.Model):
    """Bilingual disease catalog per plant (`diseases` table)."""

    plant = models.ForeignKey(
        Plant,
        on_delete=models.PROTECT,
        db_column="plant_id",
        related_name="diseases",
    )
    name_en = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255)
    description_en = models.TextField(blank=True, null=True)
    description_ar = models.TextField(blank=True, null=True)
    causes_en = models.TextField(blank=True, null=True)
    causes_ar = models.TextField(blank=True, null=True)
    treatment_en = models.TextField(blank=True, null=True)
    treatment_ar = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "diseases"


class Diagnosis(models.Model):
    """Per-user diagnosis record (`diagnoses` table)."""

    class InputType(models.TextChoices):
        IMAGE = "image", "image"
        TEXT = "text", "text"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="diagnoses",
    )
    disease = models.ForeignKey(
        Disease,
        on_delete=models.CASCADE,
        db_column="disease_id",
        related_name="diagnoses",
    )
    input_type = models.CharField(
        max_length=10,
        choices=InputType.choices,
    )
    image_url = models.TextField(blank=True, null=True)
    text_input = models.TextField(blank=True, null=True)
    confidence_score = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "diagnoses"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    input_type__in=["image", "text"],
                ),
                name="diagnoses_input_type_check",
            ),
        ]


class AILog(models.Model):
    """AI inference log (`ai_logs` table)."""

    diagnosis = models.ForeignKey(
        Diagnosis,
        on_delete=models.SET_NULL,
        db_column="diagnosis_id",
        related_name="ai_logs",
        blank=True,
        null=True,
    )
    input_data = models.TextField(blank=True, null=True)
    predicted_disease = models.CharField(max_length=255, blank=True, null=True)
    confidence_score = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_logs"


class Review(models.Model):
    """User review of a diagnosis (`reviews` table)."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="reviews",
    )
    diagnosis = models.ForeignKey(
        Diagnosis,
        on_delete=models.CASCADE,
        db_column="diagnosis_id",
        related_name="reviews",
    )
    rating = models.IntegerField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reviews"
