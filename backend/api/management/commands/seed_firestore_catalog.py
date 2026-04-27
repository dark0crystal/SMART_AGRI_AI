from __future__ import annotations

from django.core.management.base import BaseCommand

from api.firestore_repository import seed_plant_and_diseases

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
UNKNOWN_NAME_EN = "Unknown / low confidence"


def _row_for_class(name_en: str) -> dict:
    body = (
        f"{name_en} (Lemon leaf class). "
        "Catalog aligned with the trained vision model; extend as needed."
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


class Command(BaseCommand):
    help = "Seed Firestore plant/disease catalog for lemon diagnosis."

    def handle(self, *args, **options):
        plant = {
            "id": 1,
            "name_en": "Lemon",
            "name_ar": "ليمون",
            "description_en": "Citrus × limon — lemon trees.",
            "description_ar": "أشجار الليمون.",
        }
        diseases: list[dict] = []
        for idx, name_en in enumerate(CLASS_NAMES, start=1):
            row = _row_for_class(name_en)
            diseases.append(
                {
                    "id": idx,
                    "name_en": name_en,
                    **row,
                }
            )
        diseases.append(
            {
                "id": len(CLASS_NAMES) + 1,
                "name_en": UNKNOWN_NAME_EN,
                "name_ar": "غير معروف / ثقة منخفضة",
                "description_en": (
                    "Used when the model probability is below threshold "
                    "or predicted label is not in the catalog."
                ),
                "description_ar": (
                    "يُستخدم عندما تقل احتمالية النموذج عن العتبة "
                    "أو لا توجد التسمية المتوقعة في القائمة."
                ),
                "causes_en": None,
                "causes_ar": None,
                "treatment_en": "Re-capture a clearer image or consult an expert.",
                "treatment_ar": "أعد التقاط صورة أوضح أو استشر خبيراً.",
            }
        )
        seed_plant_and_diseases(plant=plant, diseases=diseases)
        self.stdout.write(self.style.SUCCESS("Seeded Firestore lemon catalog."))
