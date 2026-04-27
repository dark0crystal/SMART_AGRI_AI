# Replace stub lemon diseases with catalog aligned to vision model class names.

from django.db import migrations

CLASS_NAMES = [
    "Anthracnose",
    "Bacterial Blight",
    "Citrus Canker",
    "Curl Virus",
    "Deficiency Leaf",
    "Dry Leaf",
    "Healthy Leaf",
    "Sooty Mould",
    "Spider Mites",
    "Witch's Broom",
]

LABEL_HINTS = {
    "Anthracnose": "Fungal Disease",
    "Bacterial Blight": "Bacterial disease",
    "Citrus Canker": "Bacterial disease",
    "Curl Virus": "Nutrient / physiological disorder",
    "Deficiency Leaf": "Nutrient / physiological disorder",
    "Dry Leaf": "Physiological stress",
    "Healthy Leaf": "Healthy",
    "Sooty Mould": "Honeydew / sooty mould",
    "Spider Mites": "Pest infestation",
    "Witch's Broom": "Nutrient / physiological disorder",
}

UNKNOWN_NAME_EN = "Unknown / low confidence"


def _row_for_class(name_en: str) -> dict:
    hint = LABEL_HINTS.get(name_en, "Plant leaf condition")
    body = (
        f"{name_en} ({hint}). Lemon leaf class used by the trained vision model; "
        "extend causes/treatment in the database or admin as needed."
    )
    return {
        "name_ar": name_en,
        "description_en": body,
        "description_ar": body,
        "causes_en": None,
        "causes_ar": None,
        "treatment_en": "See local extension or plant pathologist for treatment options.",
        "treatment_ar": "See local extension or plant pathologist for treatment options.",
    }


def replace_lemon_catalog(apps, schema_editor):
    Plant = apps.get_model("api", "Plant")
    Disease = apps.get_model("api", "Disease")

    lemon = Plant.objects.filter(name_en__iexact="Lemon").first()
    if not lemon:
        lemon = Plant.objects.create(
            name_en="Lemon",
            name_ar="ليمون",
            description_en="Citrus × limon — lemon trees.",
            description_ar="أشجار الليمون.",
        )

    Disease.objects.filter(plant=lemon).delete()

    for name_en in CLASS_NAMES:
        Disease.objects.create(plant=lemon, name_en=name_en, **_row_for_class(name_en))

    Disease.objects.create(
        plant=lemon,
        name_en=UNKNOWN_NAME_EN,
        name_ar="غير معروف / ثقة منخفضة",
        description_en=(
            "Used when the model's top probability is below the server threshold "
            "or the predicted label is not in the catalog."
        ),
        description_ar=(
            "يُستخدم عندما تقل احتمالية النموذج عن عتبة الخادم "
            "أو عند عدم وجود التسمية المتوقعة في القائمة."
        ),
        causes_en=None,
        causes_ar=None,
        treatment_en="Re-capture a clearer image or consult an expert.",
        treatment_ar="أعد التقاط صورة أوضح أو استشر خبيراً.",
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0003_seed_lemon_catalog"),
    ]

    operations = [
        migrations.RunPython(replace_lemon_catalog, noop_reverse),
    ]
