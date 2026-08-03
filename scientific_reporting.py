"""
ProtonAI - Scientific Reporting
تقرير علمي بدرجة نشر: ملخص ← منهج ← نتائج (جداول) ← قيود ← خاتمة
يجمع مقاييس كل المراحل بوثيقة وحدة. القيود تُولّد تلقائياً وبصراحة
(الورقة اللي تعترف بحدودها هي اللي تُقبل)
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ProtonAI.ScientificReporting")

# قيود افتراضية صادقة، مبنية على قرارات التصميم الحقيقية بالمنصة
DEFAULT_LIMITATIONS: List[str] = [
    "التحقق استعادي وبأثر رجعي على بيانات تاريخية؛ يلزم تحقق مستقبلي متعدد المراكز.",
    "نماذج الفيزياء تحليلية مبسطة (CSDA تقريبي) وليست محاكاة Monte Carlo كاملة.",
    "التكامل مع PACS/FHIR على مستوى العقود فقط؛ الاتصال الحي غير مُقيّم.",
    "العينات التجريبية (الديمو) اصطناعية لأغراض الاختبار والعرض.",
]

# المنهج: وصف موجز لطبقات المنصة (بالترتيب)
METHODS_BULLETS: List[str] = [
    "بوابة بيانات بعقود وتحقق وإخفاء هوية تلقائي (المرحلتان 1-2).",
    "تقييم علمي بفواصل ثقة 95% وتكرار ببصمة ومراجعة طبيب (المرحلة 3).",
    "محرك AI بتفسير وضبط ذاتي وensemble ومكتبة نماذج (المرحلة 4).",
    "قمة تصوير: DICOM + تقسيم أنسجة/OAR + هامش تنفس (2.5/4-Imaging).",
    "محرك فيزياء بروتون مع عدم يقين وGamma ومعايير مرجعية (المرحلة 5).",
    "دعم قرار سريري بحالات محروسة وقرار بشري نهائي (المرحلة 6).",
    "جاهزية مؤسسية: RBAC + تدقيق + maker-checker + مراقبة + FHIR (المرحلة 7).",
    "تحقق استعادي وتقييم تعميم خارجي (المرحلة 8).",
]


def _fmt(value: Any) -> str:
    """تنسيق قيمة للجدول (float → 3 منازل)"""
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, bool):
        return "نعم" if value else "لا"
    return str(value)


class ScientificReporting:
    """
    مُجمّع التقرير العلمي.
    - add_stage: يضيف حزمة مقاييس مرحلة (تظهر كجدول بالنتائج).
    - set_abstract / add_limitation: تخصيص.
    - build: قاموس منظم (title/authors/abstract/methods/results/limitations/conclusion).
    - to_markdown: وثيقة Markdown ببنية ورقة علمية.
    """

    def __init__(
        self,
        title: str = "ProtonAI: منصة متكاملة لدعم قرار علاج البروتون",
        authors: Optional[List[str]] = None,
    ):
        self.title = title
        self.authors = list(authors) if authors else []
        self.stages: Dict[str, Dict[str, Any]] = {}
        self.limitations: List[str] = list(DEFAULT_LIMITATIONS)
        self._abstract: Optional[str] = None

    def add_stage(self, name: str, metrics: Dict[str, Any]) -> None:
        """إضافة حزمة مقاييس مرحلة"""
        if not str(name).strip():
            raise ValueError("اسم المرحلة لا يمكن أن يكون فارغاً")
        self.stages[name] = dict(metrics)

    def add_limitation(self, text: str) -> None:
        """إضافة قيد مخصص"""
        self.limitations.append(str(text))

    def set_abstract(self, text: str) -> None:
        """تعيين الملخص يدوياً"""
        self._abstract = str(text)

    def _auto_abstract(self) -> str:
        """ملخص مولّد تلقائياً من عدد المراحل والمقاييس"""
        n_metrics = sum(len(m) for m in self.stages.values())
        return (f"نقدّم ProtonAI، منصة متكاملة لدعم قرار علاج البروتون تغطي "
                f"{len(self.stages)} حزم نتائج و{n_metrics} مقياساً، بمنهجية تحقق "
                f"استعادي وتعميم خارجي، مع إقرار صريح بالقيود.")

    def build(self) -> Dict[str, Any]:
        """بناء القاموس المنظم للتقرير"""
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self._abstract or self._auto_abstract(),
            "methods": list(METHODS_BULLETS),
            "results": {k: dict(v) for k, v in self.stages.items()},
            "limitations": list(self.limitations),
            "conclusion": ("المنصة تُظهر أداءً متماسكاً داخلياً وخارجياً مع فجوة تعميم "
                           "مضبوطة، وتوفر سلسلة مساءلة كاملة من البيانات للقرار؛ "
                           "يلزم تحقق مستقبلي متعدد المراكز قبل النشر السريري."),
        }

    def _results_markdown(self, results: Dict[str, Dict[str, Any]]) -> str:
        """جداول النتائج لكل مرحلة"""
        if not results:
            return "_لا توجد نتائج مضافة بعد._"
        out: List[str] = []
        for name, metrics in results.items():
            out.append(f"### {name}\n")
            out.append("| المقياس | القيمة |\n|---------|:------:|")
            for k, v in metrics.items():
                out.append(f"| {k} | {_fmt(v)} |")
            out.append("")
        return "\n".join(out)

    def to_markdown(self) -> str:
        """تصدير وثيقة Markdown ببنية ورقة علمية"""
        b = self.build()
        lines = [f"# {b['title']}", ""]
        if b["authors"]:
            lines.append(f"**المؤلفون:** {', '.join(b['authors'])}  ")
        lines += ["", "## الملخص (Abstract)", "", b["abstract"], "",
                  "## المنهج (Methods)", ""]
        lines += [f"- {m}" for m in b["methods"]]
        lines += ["", "## النتائج (Results)", "", self._results_markdown(b["results"]),
                  "## القيود (Limitations)", ""]
        lines += [f"- {l}" for l in b["limitations"]]
        lines += ["", "## الخاتمة (Conclusion)", "", b["conclusion"], ""]
        return "\n".join(lines)
