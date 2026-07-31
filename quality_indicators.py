"""
ProtonAI - Quality Indicators
إشارات المرور السريرية (clear quality indicators): 🟢/🟡/🔴/❓ لكل معيار
العتبات سريرية معرّفة وقابلة للتخصيص. overall = أسوأ إشارة (السلامة = الأسوأ يحكم)
أي مؤشر مفقود = UNKNOWN (لا نفترض السلامة). يقرأ من أقسام TreatmentPlan
"""

import logging
from enum import IntEnum
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

from treatment_plan import TreatmentPlan

logger = logging.getLogger("ProtonAI.QualityIndicators")


class Status(IntEnum):
    """حالة المؤشر (القيمة = الشدة، للأسوأ يحكم)"""
    UNKNOWN = -1   # ❓ غير متوفر (لا يُدخل بالـ overall)
    GREEN = 0      # 🟢 مقبول
    AMBER = 1      # 🟡 تحذير
    RED = 2        # 🔴 مرفوض / خطر


_STATUS_SYMBOL = {
    Status.GREEN: "🟢", Status.AMBER: "🟡",
    Status.RED: "🔴", Status.UNKNOWN: "❓",
}


@dataclass
class Indicator:
    """مؤشر جودة واحد"""
    name: str
    label: str
    value: Any
    status: Status
    message: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.name
        d["symbol"] = _STATUS_SYMBOL[self.status]
        return d


class QualityIndicators:
    """
    مقيّم مؤشرات الجودة.
    - evaluate(metrics): يقيّم قاموس مقاييس مسطّح → قائمة Indicator + overall.
    - evaluate_plan(plan): يستخرج المقاييس من أقسام الخطة ثم يقيّم.
    العتبات قابلة للتخصيص بالـ __init__ (افتراضيات سريرية معقولة).
    """

    def __init__(
        self,
        gamma_green: float = 0.95,
        gamma_amber: float = 0.90,
        coverage_green: float = 0.05,
        coverage_amber: float = 0.10,
        completeness_green: float = 1.0,
        completeness_amber: float = 0.5,
    ):
        if not (0 <= gamma_amber <= gamma_green <= 1):
            raise ValueError("عتبات gamma غير صالحة: 0 <= amber <= green <= 1")
        if not (0 <= coverage_green <= coverage_amber):
            raise ValueError("عتبات coverage غير صالحة: 0 <= green <= amber")
        if not (0 <= completeness_amber <= completeness_green <= 1):
            raise ValueError("عتبات completeness غير صالحة: 0 <= amber <= green <= 1")
        self.gamma_green = gamma_green
        self.gamma_amber = gamma_amber
        self.coverage_green = coverage_green
        self.coverage_amber = coverage_amber
        self.completeness_green = completeness_green
        self.completeness_amber = completeness_amber

    # --- مؤشرات فردية (ترجع status + message) ---

    def _eval_gamma(self, v: Any):
        if v is None:
            return Status.UNKNOWN, "معدل Gamma غير متوفر"
        v = float(v)
        if v >= self.gamma_green:
            return Status.GREEN, f"Gamma مقبول ({v:.0%})"
        if v >= self.gamma_amber:
            return Status.AMBER, f"Gamma تحذيري ({v:.0%}) — راجع التوزيع"
        return Status.RED, f"Gamma مرفوض ({v:.0%}) — يلزم تصحيح التوزيع"

    def _eval_range(self, v: Any):
        if v is None:
            return Status.UNKNOWN, "حالة المدى غير متوفرة"
        if bool(v):
            return Status.GREEN, "المدى داخل منطقة الهدف"
        return Status.RED, "المدى خارج منطقة الهدف — خطر سريري"

    def _eval_coverage(self, v: Any):
        if v is None:
            return Status.UNKNOWN, "انهيار التغطية غير متوفر"
        v = float(v)
        if v <= self.coverage_green:
            return Status.GREEN, f"التغطية متينة (انهيار {v:.0%})"
        if v <= self.coverage_amber:
            return Status.AMBER, f"انهيار تغطية تحذيري ({v:.0%})"
        return Status.RED, f"انهيار تغطية خطير ({v:.0%}) — يلزم إعادة تخطيط"

    def _eval_benchmark(self, v: Any):
        if v is None:
            return Status.UNKNOWN, "فحص المعايير الفيزيائية غير متوفر"
        if bool(v):
            return Status.GREEN, "المعايير الفيزيائية مجتازة"
        return Status.RED, "فشل بالمعايير الفيزيائية المرجعية"

    def _eval_completeness(self, v: Any):
        if v is None:
            return Status.UNKNOWN, "اكتمال الخطة غير متوفر"
        v = float(v)
        if v >= self.completeness_green:
            return Status.GREEN, "الخطة مكتملة البيانات"
        if v >= self.completeness_amber:
            return Status.AMBER, f"الخطة مكتملة جزئياً ({v:.0%})"
        return Status.RED, f"الخطة ناقصة البيانات ({v:.0%})"

    def _eval_reviews(self, v: Any):
        if v is None:
            return Status.UNKNOWN, "حالة توقيع المراجعات غير متوفرة"
        if bool(v):
            return Status.GREEN, "المراجعات البشرية موقّعة"
        return Status.RED, "المراجعات البشرية غير مكتملة — القرار النهائي معلّق"

    def evaluate(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """تقييم قاموس مقاييس → مؤشرات + overall + ملخص"""
        specs = [
            ("gamma_pass_rate", "Gamma Index", self._eval_gamma),
            ("range_in_target", "المدى بالهدف", self._eval_range),
            ("coverage_drop", "انهيار التغطية", self._eval_coverage),
            ("benchmark_passed", "المعايير الفيزيائية", self._eval_benchmark),
            ("completeness", "اكتمال الخطة", self._eval_completeness),
            ("reviews_signed", "توقيع المراجعات", self._eval_reviews),
        ]
        indicators: List[Indicator] = []
        for key, label, fn in specs:
            val = metrics.get(key)
            status, message = fn(val)
            indicators.append(Indicator(key, label, val, status, message))

        evaluated = [i.status for i in indicators if i.status != Status.UNKNOWN]
        if evaluated:
            overall = max(evaluated)
        else:
            overall = Status.UNKNOWN
        n_unknown = sum(1 for i in indicators if i.status == Status.UNKNOWN)
        n_red = sum(1 for i in indicators if i.status == Status.RED)
        n_amber = sum(1 for i in indicators if i.status == Status.AMBER)
        logger.info(f"quality: overall={overall.name}, red={n_red}, "
                    f"amber={n_amber}, unknown={n_unknown}")
        return {
            "indicators": indicators,
            "overall": overall,
            "overall_symbol": _STATUS_SYMBOL[overall],
            "n_red": n_red, "n_amber": n_amber, "n_unknown": n_unknown,
        }

    def evaluate_plan(self, plan: TreatmentPlan) -> Dict[str, Any]:
        """استخراج المقاييس من أقسام الخطة ثم تقييمها"""
        metrics = {
            "gamma_pass_rate": plan.physics.get("gamma_pass_rate"),
            "range_in_target": plan.physics.get("range_in_target"),
            "coverage_drop": plan.physics.get("coverage_drop"),
            "benchmark_passed": plan.physics.get("benchmark_passed"),
            "completeness": plan.completeness(),  # دايماً متوفر
            "reviews_signed": plan.reviews.get("signed"),
        }
        return self.evaluate(metrics)
