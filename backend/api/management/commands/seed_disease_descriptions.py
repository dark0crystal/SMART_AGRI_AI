"""
Push the bilingual disease descriptions / treatments from
``docs/Disease name, Description .docx`` into the Firestore ``diseases``
collection for the Lemon plant (plant_id=1).

Existing documents are REPLACED (full overwrite) so the new copy is the sole
source of truth. ``name_en`` for every existing disease is kept exactly as
the trained vision model emits it ("Anthracnose", "Sooty Mould",
"Witch's Broom", ...) so disease prediction continues to work unchanged.

Usage:
    python manage.py seed_disease_descriptions
    python manage.py seed_disease_descriptions --dry-run
    python manage.py seed_disease_descriptions --plant-id 1 --merge

``--merge`` switches to ``set(merge=True)`` so unspecified Firestore fields
on each doc are preserved instead of overwritten.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandParser

from api.firestore_repository import (
    get_default_lemon_plant,
    get_plant,
    upsert_diseases_for_plant,
)

# Each entry's ``id`` matches the existing Firestore document id seeded by
# ``seed_firestore_catalog`` so we OVERWRITE (not duplicate) the catalog row.
# ``name_en`` is the exact label the vision model emits — DO NOT change it for
# the seeded ids 1..10 unless you also retrain the model.
#
# "Citrus Greening" is a new disease (id=12). The vision model does not predict
# it, but it shows up in the admin catalog and in any text/manual lookup.

DISEASES: list[dict[str, object]] = [
    {
        "id": 1,
        "name_en": "Anthracnose",
        "name_ar": "الأنثراكنوز",
        "description_en": (
            "Anthracnose is a fungal disease caused mainly by Colletotrichum "
            "species. It affects leaves, twigs, flowers, and fruits, producing "
            "dark, sunken lesions. The disease is common in humid conditions "
            "and can cause leaf drop, fruit rot, and reduced crop quality."
        ),
        "description_ar": (
            "الأنثراكنوز هو مرض فطري تسببه بشكل رئيسي أنواع فطر Colletotrichum. "
            "يؤثر على الأوراق والأغصان والأزهار والثمار، مسببًا بقعًا داكنة "
            "غائرة. ينتشر المرض في الظروف الرطبة وقد يسبب تساقط الأوراق وتعفن "
            "الثمار وانخفاض جودة المحصول."
        ),
        "causes_en": None,
        "causes_ar": None,
        "treatment_en": (
            "Apply recommended fungicides such as copper fungicides or "
            "azoxystrobin. Improve air circulation by proper pruning. Avoid "
            "overhead irrigation and remove infected plant debris from the "
            "orchard."
        ),
        "treatment_ar": (
            "استخدم المبيدات الفطرية الموصى بها مثل المبيدات النحاسية أو "
            "الأزوكسيستروبين. حسّن التهوية من خلال التقليم الصحيح. تجنب الري "
            "العلوي وقم بإزالة بقايا النباتات المصابة من البستان."
        ),
    },
    {
        "id": 3,
        "name_en": "Citrus Canker",
        "name_ar": "اللفحة البكتيرية للحمضيات",
        "description_en": (
            "Citrus Canker is a bacterial disease caused by Xanthomonas citri. "
            "It produces raised lesions on leaves, stems, and fruits, often "
            "surrounded by yellow halos. The disease spreads quickly through "
            "wind-driven rain, contaminated tools, and infected plant "
            "materials. Severe infections can lead to defoliation and reduced "
            "fruit quality."
        ),
        "description_ar": (
            "اللفحة البكتيرية للحمضيات هي مرض بكتيري تسببه بكتيريا Xanthomonas "
            "citri. يسبب ظهور تقرحات بارزة على الأوراق والسيقان والثمار، "
            "وغالبًا ما تكون محاطة بهالات صفراء. ينتشر المرض بسرعة عبر "
            "الأمطار المصحوبة بالرياح، والأدوات الملوثة، والمواد النباتية "
            "المصابة. وقد تؤدي الإصابات الشديدة إلى تساقط الأوراق وانخفاض "
            "جودة الثمار."
        ),
        "causes_en": None,
        "causes_ar": None,
        "treatment_en": (
            "Remove infected leaves and branches. Apply copper-based "
            "bactericides to control the spread. Use disease-free planting "
            "materials and disinfect tools. Implement quarantine and "
            "sanitation practices in orchards."
        ),
        "treatment_ar": (
            "قم بإزالة الأوراق والأغصان المصابة. استخدم مبيدات بكتيرية قائمة "
            "على النحاس للحد من انتشار المرض. استخدم مواد زراعية خالية من "
            "الأمراض وقم بتعقيم الأدوات. طبّق إجراءات الحجر الزراعي والنظافة "
            "في البساتين."
        ),
    },
    {
        "id": 4,
        "name_en": "Curl Virus",
        "name_ar": "فيروس تجعد الأوراق",
        "description_en": (
            "Leaf Curl Virus is a viral disease that affects plant leaves, "
            "causing curling, distortion, and stunted growth. Infected plants "
            "often show reduced leaf size, yellowing, and poor fruit "
            "production. The virus is commonly spread by insect vectors such "
            "as whiteflies."
        ),
        "description_ar": (
            "فيروس تجعد الأوراق هو مرض فيروسي يؤثر على أوراق النبات، مسببًا "
            "التفافها وتشوهها وضعف نموها. تُظهر النباتات المصابة غالبًا صغر "
            "حجم الأوراق، واصفرارها، وضعف إنتاج الثمار. وينتقل الفيروس عادةً "
            "عن طريق الحشرات الناقلة مثل الذباب الأبيض."
        ),
        "causes_en": None,
        "causes_ar": None,
        "treatment_en": (
            "Control insect vectors (especially whiteflies) using approved "
            "insecticides. Remove and destroy infected plant parts to prevent "
            "spread. Use resistant plant varieties and maintain proper field "
            "hygiene."
        ),
        "treatment_ar": (
            "قم بمكافحة الحشرات الناقلة (خصوصًا الذباب الأبيض) باستخدام "
            "مبيدات حشرية معتمدة. قم بإزالة وتدمير الأجزاء المصابة من النبات "
            "لمنع انتشار المرض. استخدم أصناف نباتية مقاومة وحافظ على نظافة "
            "المزرعة."
        ),
    },
    {
        "id": 5,
        "name_en": "Deficiency Leaf",
        "name_ar": "نقص العناصر الغذائية",
        "description_en": (
            "Nutrient deficiency occurs when citrus plants lack essential "
            "nutrients such as nitrogen, iron, magnesium, or potassium. "
            "Symptoms usually appear as yellowing of leaves (chlorosis), poor "
            "growth, weak stems, and reduced fruit yield. Different "
            "deficiencies show different leaf patterns, such as yellow leaves "
            "with green veins in iron deficiency."
        ),
        "description_ar": (
            "يحدث نقص العناصر الغذائية عندما تفتقر نباتات الحمضيات إلى عناصر "
            "أساسية مثل النيتروجين أو الحديد أو المغنيسيوم أو البوتاسيوم. "
            "تظهر الأعراض عادة على شكل اصفرار الأوراق (الكلوروز)، وضعف "
            "النمو، وسيقان ضعيفة، وانخفاض في إنتاج الثمار. وتظهر أنواع النقص "
            "المختلفة أنماطًا مختلفة على الأوراق، مثل الأوراق الصفراء مع "
            "عروق خضراء في حالة نقص الحديد."
        ),
        "causes_en": None,
        "causes_ar": None,
        "treatment_en": (
            "Apply appropriate fertilizers based on soil analysis. Use "
            "balanced fertilizers containing nitrogen, phosphorus, and "
            "potassium. For iron deficiency, apply iron chelate sprays or "
            "soil treatments. Improve soil fertility and irrigation "
            "management."
        ),
        "treatment_ar": (
            "قم باستخدام الأسمدة المناسبة بناءً على تحليل التربة. استخدم "
            "أسمدة متوازنة تحتوي على النيتروجين والفوسفور والبوتاسيوم. في "
            "حالة نقص الحديد، استخدم رشات مخلّبات الحديد أو المعالجات "
            "الأرضية. قم بتحسين خصوبة التربة وإدارة الري."
        ),
    },
    {
        "id": 8,
        "name_en": "Sooty Mould",
        "name_ar": "العفن الأسود",
        "description_en": (
            "Sooty mold is a fungal disease that commonly affects citrus "
            "trees. It grows as a black, powdery coating on leaves, stems, "
            "and fruits. The fungus itself does not directly infect plant "
            "tissue but grows on the honeydew secreted by sap-sucking insects "
            "such as aphids, whiteflies, scales, and psyllids.\n\n"
            "The presence of sooty mold reduces photosynthesis by blocking "
            "sunlight from reaching the leaf surface, which can weaken the "
            "tree and reduce fruit yield and quality. The disease is mostly "
            "cosmetic in early stages, but heavy infestations can have a "
            "significant impact on plant health and aesthetics."
        ),
        "description_ar": (
            "العفن الأسود هو مرض فطري شائع يصيب أشجار الحمضيات. يظهر على شكل "
            "طبقة سوداء مسحوقية على الأوراق والسيقان والثمار. لا يخترق الفطر "
            "أنسجة النبات مباشرة، بل ينمو على الندوة العسلية التي تفرزها "
            "الحشرات الماصة للعصارة مثل المنّ، الذباب الأبيض، الحشرات "
            "القشرية، والبسيلا.\n\n"
            "يؤدي العفن الأسود إلى تقليل قدرة النبات على التمثيل الضوئي "
            "نتيجة حجب أشعة الشمس عن سطح الأوراق، مما قد يضعف الشجرة ويقلل "
            "من كمية وجودة الثمار. في المراحل المبكرة، يكون تأثير المرض "
            "تجميليًا، لكن في الحالات الشديدة يمكن أن يؤثر على صحة الشجرة "
            "بشكل ملحوظ."
        ),
        "causes_en": None,
        "causes_ar": None,
        "treatment_en": (
            "Control sap-sucking insects (aphids, whiteflies, scales) that "
            "produce honeydew.\n"
            "Wash leaves with water to remove mold deposits.\n"
            "Apply insecticides or horticultural oils if insect populations "
            "are high.\n"
            "Maintain good air circulation around trees."
        ),
        "treatment_ar": (
            "مكافحة الحشرات الماصة للعصارة مثل المنّ والذباب الأبيض والحشرات "
            "القشرية.\n"
            "غسل الأوراق بالماء لإزالة طبقة العفن.\n"
            "استخدام الزيوت الزراعية أو المبيدات المناسبة عند زيادة "
            "الحشرات.\n"
            "تحسين التهوية حول الأشجار."
        ),
    },
    {
        "id": 9,
        "name_en": "Spider Mites",
        "name_ar": "العناكب الدقيقة",
        "description_en": (
            "Spider mites are tiny arachnid pests that feed on the undersides "
            "of citrus leaves. The most common species affecting citrus are "
            "Tetranychus urticae (two-spotted spider mite). These pests "
            "pierce leaf cells and suck out the contents, leading to tiny "
            "yellow or white speckles (stippling) on leaves. Heavy "
            "infestations cause leaves to become bronzed, dry, and eventually "
            "fall off. Fine webbing may be visible on leaves and stems, "
            "especially in severe cases.\n\n"
            "Spider mite damage reduces the plant's ability to photosynthesize "
            "effectively, weakens tree vigor, and can reduce fruit yield and "
            "quality if unmanaged. Hot, dry conditions often increase spider "
            "mite populations because these pests thrive when humidity is low."
        ),
        "description_ar": (
            "العناكب الدقيقة هي آفات صغيرة جدًا تنتمي إلى العنكبيات، وتهاجم "
            "جانب الأوراق السفلي في أشجار الحمضيات. النوع الأكثر انتشارًا هو "
            "Tetranychus urticae (العنكبوتية ذات النقطتين). تقوم هذه الحشرات "
            "بثقب خلايا الورقة وسحب محتواها، مما يؤدي إلى ظهور بقع صغيرة "
            "صفراء أو بيضاء على الأوراق (تغلغل النسيج). في الحالات الشديدة، "
            "تصبح الأوراق برونزية اللون، جافة، وقد تسقط في نهاية المطاف. كما "
            "قد تظهر خيوط عنكبوتية رفيعة على الأوراق والسيقان.\n\n"
            "يُضعف هذا الضرر قدرة النبات على القيام بعملية التمثيل الضوئي "
            "بشكل فعال، ويقلل من قوة الشجرة وجودة وكمية الثمار، خاصةً في "
            "الظروف الحارة والجافة التي تفضل تكاثر هذه الآفة."
        ),
        "causes_en": None,
        "causes_ar": None,
        "treatment_en": (
            "Spray water to remove mites from leaves.\n"
            "Apply miticides or insecticidal soap when infestation is "
            "severe.\n"
            "Introduce natural predators such as predatory mites.\n"
            "Maintain proper irrigation to reduce plant stress."
        ),
        "treatment_ar": (
            "رش الأوراق بالماء لإزالة العناكب الدقيقة.\n"
            "استخدام مبيدات خاصة بالعناكب عند الإصابة الشديدة.\n"
            "تشجيع الأعداء الحيوية مثل العناكب المفترسة.\n"
            "الحفاظ على ري مناسب لتقليل إجهاد النبات."
        ),
    },
    {
        # IMPORTANT: name_en MUST stay "Witch's Broom" (with ASCII apostrophe)
        # to match the trained vision model class label.
        "id": 10,
        "name_en": "Witch's Broom",
        "name_ar": "مرض المكانس الساحرة",
        "description_en": (
            "Witches' Broom Disease of Lime (WBDL) is a serious "
            "phytoplasma-associated disease affecting acid lime and other "
            "citrus species. It is caused by Candidatus Phytoplasma "
            "aurantifolia, a microorganism that infects the phloem tissue of "
            "the plant and disrupts normal growth.\n\n"
            "The disease is characterized by the excessive development of "
            "thin, weak shoots that grow in dense clusters, giving the plant "
            "a \"broom-like\" appearance. Infected trees show small, pale "
            "leaves, shortened internodes, reduced flowering, and significant "
            "decline in fruit production. Over time, the tree becomes "
            "severely weakened and may die within a few years if untreated."
        ),
        "description_ar": (
            "يُعد مرض المكانس الساحرة من الأمراض الخطيرة التي تصيب أشجار "
            "الليمون والحمضيات، ويسببه كائن دقيق يُعرف باسم فيتوبلازما "
            "Candidatus Phytoplasma aurantifolia، والتي تعيش داخل أنسجة "
            "اللحاء في النبات وتؤثر على النمو الطبيعي للشجرة.\n\n"
            "تتميز الإصابة بظهور نمو كثيف لأفرع رفيعة وضعيفة متقاربة من "
            "بعضها، مما يعطي الشجرة مظهرًا يشبه المكنسة. كما تظهر أوراق "
            "صغيرة باهتة اللون، وقصر في السلاميات، وضعف في الإزهار، وانخفاض "
            "كبير في إنتاج الثمار. ومع تقدم الإصابة، تضعف الشجرة تدريجيًا "
            "وقد تموت خلال عدة سنوات."
        ),
        "causes_en": None,
        "causes_ar": None,
        "treatment_en": (
            "Remove infected branches or entire trees if infection is "
            "severe.\n"
            "Use certified disease-free seedlings.\n"
            "Control insect vectors that spread phytoplasma.\n"
            "Maintain orchard sanitation and regular monitoring."
        ),
        "treatment_ar": (
            "إزالة الأفرع المصابة أو اقتلاع الأشجار المصابة بشدة.\n"
            "استخدام شتلات خالية من المرض ومعتمدة.\n"
            "مكافحة الحشرات الناقلة للمرض.\n"
            "الحفاظ على نظافة المزرعة والمراقبة المستمرة للأشجار."
        ),
    },
    {
        # New disease, not part of the trained vision model class set.
        # Catalog-only entry (admin can edit it; it won't be predicted by the
        # current model checkpoint).
        "id": 12,
        "name_en": "Citrus Greening",
        "name_ar": "اخضرار الحمضيات",
        "description_en": (
            "Citrus greening, also known as Huanglongbing (HLB), is one of "
            "the most serious and destructive diseases affecting citrus "
            "trees worldwide. It is caused by a phloem-limited bacterium, "
            "most commonly Candidatus Liberibacter asiaticus, and is "
            "transmitted by citrus psyllid insects.\n\n"
            "The disease is characterized by yellowing of leaves (often "
            "asymmetrical), blotchy mottling patterns, stunted tree growth, "
            "and premature fruit drop. Infected fruits are usually small, "
            "misshapen, unevenly colored, and may have a bitter taste. Over "
            "time, the disease weakens the tree significantly and can "
            "eventually lead to tree death."
        ),
        "description_ar": (
            "يُعد مرض اخضرار الحمضيات من أخطر الأمراض التي تصيب أشجار "
            "الحمضيات على مستوى العالم. يسببه نوع من البكتيريا التي تعيش "
            "داخل أنسجة اللحاء في النبات، وينتقل المرض بواسطة حشرة بسيلا "
            "الحمضيات.\n\n"
            "تظهر أعراض المرض على شكل اصفرار غير منتظم في الأوراق مع بقع "
            "متداخلة، وضعف في نمو الشجرة، وتساقط مبكر للثمار. كما تكون "
            "الثمار المصابة صغيرة الحجم، مشوهة الشكل، غير متجانسة اللون، "
            "وقد يكون طعمها مرًّا. ومع تقدم الإصابة، تضعف الشجرة تدريجيًا "
            "وقد تموت في الحالات الشديدة."
        ),
        "causes_en": None,
        "causes_ar": None,
        "treatment_en": (
            "Remove and destroy infected trees to prevent disease spread.\n"
            "Control the insect vector (Asian citrus psyllid) using approved "
            "insecticides.\n"
            "Use certified disease-free planting materials.\n"
            "Monitor orchards regularly for early detection."
        ),
        "treatment_ar": (
            "إزالة الأشجار المصابة والتخلص منها لمنع انتشار المرض.\n"
            "مكافحة الحشرة الناقلة للمرض (بسيلا الحمضيات) باستخدام المبيدات "
            "المناسبة.\n"
            "استخدام شتلات سليمة وخالية من المرض.\n"
            "المراقبة المستمرة للبساتين للكشف المبكر عن الإصابة."
        ),
    },
]


class Command(BaseCommand):
    help = (
        "Push bilingual disease descriptions/treatments (from "
        "docs/Disease name, Description .docx) to the Firestore 'diseases' "
        "collection. Existing docs are replaced unless --merge is given."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--plant-id",
            type=int,
            default=None,
            help=(
                "Plant id to attach the diseases to (defaults to the seeded "
                "Lemon plant; falls back to id=1 if not found)."
            ),
        )
        parser.add_argument(
            "--merge",
            action="store_true",
            help=(
                "Use Firestore set(merge=True) so untouched fields on the "
                "existing docs are preserved. Default is full overwrite."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be written, do NOT touch Firestore.",
        )

    def handle(self, *args, **options) -> None:
        plant_id_arg: int | None = options.get("plant_id")
        merge: bool = bool(options.get("merge"))
        dry_run: bool = bool(options.get("dry_run"))

        if plant_id_arg is None:
            lemon = get_default_lemon_plant()
            plant_id = int(lemon["id"]) if lemon else 1
            if not lemon:
                self.stdout.write(
                    self.style.WARNING(
                        "No 'Lemon' plant found in Firestore; defaulting to "
                        "plant_id=1. Run `python manage.py "
                        "seed_firestore_catalog` first if needed."
                    )
                )
        else:
            plant_id = plant_id_arg
            if not get_plant(plant_id):
                self.stdout.write(
                    self.style.WARNING(
                        f"plant_id={plant_id} does not exist in Firestore. "
                        "The disease docs will still be written with this "
                        "plant_id, but they will not link to a plant doc "
                        "until you create one."
                    )
                )

        mode = "MERGE (preserve untouched fields)" if merge else "REPLACE (full overwrite)"
        self.stdout.write(
            self.style.NOTICE(
                f"Target: diseases for plant_id={plant_id} | mode={mode} | "
                f"docs={len(DISEASES)}"
            )
        )

        for d in DISEASES:
            self.stdout.write(
                f"  id={d['id']:>2}  name_en={d['name_en']!r}  "
                f"description_en={len(str(d['description_en']))} chars  "
                f"treatment_en={len(str(d['treatment_en']))} chars"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "--dry-run: no Firestore writes performed. Sample payload:"
                )
            )
            self.stdout.write(json.dumps(DISEASES[0], ensure_ascii=False, indent=2))
            return

        written = upsert_diseases_for_plant(
            plant_id=plant_id,
            diseases=DISEASES,
            replace=not merge,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {written} disease docs to Firestore (plant_id={plant_id})."
            )
        )
