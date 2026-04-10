# Generated manually — lemon plant + disease catalog for diagnosis stub / AI mapping.

from django.db import migrations


def seed_lemon_catalog(apps, schema_editor):
    Plant = apps.get_model("api", "Plant")
    Disease = apps.get_model("api", "Disease")

    lemon, _ = Plant.objects.get_or_create(
        name_en="Lemon",
        defaults={
            "name_ar": "ليمون",
            "description_en": "Citrus × limon — lemon trees (scenario 3.1.2 target crop).",
            "description_ar": "أشجار الليمون (محصول السيناريو).",
        },
    )

    catalog = [
        {
            "name_en": "Citrus canker",
            "name_ar": "تفحم الحمضيات",
            "description_en": "Bacterial disease causing raised corky lesions on leaves and fruit.",
            "description_ar": "مرض بكتيري يسبب بثوراً على الأوراق والثمار.",
            "causes_en": "Xanthomonas citri; spread by wind, rain, and tools.",
            "causes_ar": "بكتيريا الزانثوموناس؛ الانتشار بالرياح والمطر.",
            "treatment_en": "Copper sprays, remove infected material, avoid overhead irrigation.",
            "treatment_ar": "رش النحاس، إزالة الأجزاء المصابة، تجنب الري العلوي.",
        },
        {
            "name_en": "Greasy spot",
            "name_ar": "البقعة الزيتية",
            "description_en": "Fungal disease with dark blister-like spots on leaves.",
            "description_ar": "مرض فطري ببقع داكنة مثل البثور على الأوراق.",
            "causes_en": "Mycosphaerella citri; favors humid warm conditions.",
            "causes_ar": "فطر الميكوسفايريلا؛ يفضل الرطوبة والدفء.",
            "treatment_en": "Fungicide applications; improve canopy airflow.",
            "treatment_ar": "مبيدات فطرية؛ تحسين تدفق الهواء في المظلة.",
        },
        {
            "name_en": "Unknown / unclassified symptoms",
            "name_ar": "أعراض غير مصنفة",
            "description_en": "Fallback when the model cannot match a catalog disease.",
            "description_ar": "حالة احتياطية عندما لا يطابق النموذج مرضاً في القائمة.",
            "causes_en": "Various biotic or abiotic factors; confirm with expert review.",
            "causes_ar": "عوامل حيوية أو غير حيوية متنوعة؛ يُنصح بمراجعة خبير.",
            "treatment_en": "Monitor the tree; collect samples for lab diagnosis if symptoms persist.",
            "treatment_ar": "راقب الشجرة؛ أرسل عينات للمختبر إذا استمرت الأعراض.",
        },
    ]

    for row in catalog:
        Disease.objects.get_or_create(
            plant=lemon,
            name_en=row["name_en"],
            defaults={k: v for k, v in row.items() if k not in ("name_en",)},
        )


def unseed_lemon_catalog(apps, schema_editor):
    Plant = apps.get_model("api", "Plant")
    Disease = apps.get_model("api", "Disease")
    lemon = Plant.objects.filter(name_en="Lemon").first()
    if not lemon:
        return
    Disease.objects.filter(plant=lemon).delete()
    lemon.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0002_plants_aillogs_reviews"),
    ]

    operations = [
        migrations.RunPython(seed_lemon_catalog, unseed_lemon_catalog),
    ]
