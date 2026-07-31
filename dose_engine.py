"""
ProtonAI - Dose Engine
محرك الجرعة السريري الموحد: تنبؤ + عدم يقين + تفسير + تحقق بروتوكول
يعطي الطبيب إجابة كاملة لكل مريض بواجهة واحدة (يربط 4 وحدات معاً)
"""

import logging
from typing import List, Dict, Any, Optional

from uncertainty import UncertaintyEstimator
from explainability import Explainability

logger = logging.getLogger("ProtonAI.DoseEngine")

# النطاقات المرجعية الافتراضية (Gy(RBE)) — من ICRU 78 / NCCN
# (مضمّنة هنا لفك الارتباط؛ يمكن تجاوزها عبر protocols بالـ __init__)
DEFAULT_PROTOCOLS: Dict[str, tuple] = {
    "lung": (60.0, 70.0),
    "brain": (54.0, 60.0),
    "prostate": (74.0, 78.0),
    "breast": (50.0, 60.0),
    "head_neck": (66.0, 70.0),
}

# حالات التحقق من البروتوكول
STATUS_IN_RANGE = "in_range"
STATUS_ABOVE = "above_range"
STATUS_BELOW = "below_range"
STATUS_UNKNOWN = "unknown_tumor"
STATUS_NA = "not_applicable"


class DoseEngine:
    """
    محرك الجرعة.
    - recommend: إجابة كاملة لسجل واحد (تنبؤ + يقين + تفسير + بروتوكول + توصية).
    - recommend_batch: قائمة إجابات.
    للتنبؤ (regression): فحص نطاق البروتوكول. للتصنيف: يُعلّم not_applicable ويحيل للمراجعة.
    """

    def __init__(
        self,
        model: Any,
        tumor_type_key: str = "tumor_type",
        protocols: Optional[Dict[str, tuple]] = None,
        top_k: int = 3,
        unit: str = "Gy(RBE)",
        seed: int = 42,
    ):
        if top_k < 1:
            raise ValueError("top_k يجب أن يكون >= 1")
        self.model = model
        self.tumor_type_key = tumor_type_key
        self.top_k = top_k
        self.unit = unit
        # تطبيع مفاتيح البروتوكولات لحروف صغيرة (مطابقة مرنة)
        src = protocols if protocols is not None else DEFAULT_PROTOCOLS
        self.protocols = {str(k).strip().lower(): tuple(v) for k, v in src.items()}
        self.unc = UncertaintyEstimator()
        self.explainer = Explainability(seed=seed)

    def _top_factors(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """أهم k ميزات لهذا السجل (قيمته + أهميتها العالمية)"""
        local = self.explainer.local_explanation(self.model, record)
        feats = local.get("features", [])
        ranked = sorted(feats, key=lambda f: f.get("global_importance", 0.0), reverse=True)
        return [{
            "feature": f["feature"], "value": f["value"],
            "importance": f.get("global_importance", 0.0),
        } for f in ranked[:self.top_k]]

    def _check_protocol(self, pred: float, tumor: str) -> Dict[str, Any]:
        """فحص الجرعة مقابل النطاق المرجعي لنوع الورم"""
        proto = self.protocols.get(tumor)
        if proto is None:
            return {"range": None, "status": STATUS_UNKNOWN, "in_range": False}
        lo, hi = proto
        if pred < lo:
            status = STATUS_BELOW
        elif pred > hi:
            status = STATUS_ABOVE
        else:
            status = STATUS_IN_RANGE
        return {"range": [lo, hi], "status": status, "in_range": status == STATUS_IN_RANGE}

    def _text_regression(
        self, pred: float, tumor: str, proto: Dict[str, Any]
    ) -> str:
        """جملة توصية بالعربي للتنبؤ"""
        st = proto["status"]
        if st == STATUS_IN_RANGE:
            return (f"الجرعة المقترحة {pred:.1f} {self.unit} ضمن النطاق المرجعي "
                    f"لـ {tumor} ({proto['range'][0]}–{proto['range'][1]}).")
        if st == STATUS_ABOVE:
            return (f"تنبيه: الجرعة المقترحة {pred:.1f} {self.unit} أعلى من النطاق "
                    f"المرجعي {proto['range']} — يلزم مراجعة الطبيب.")
        if st == STATUS_BELOW:
            return (f"تنبيه: الجرعة المقترحة {pred:.1f} {self.unit} أقل من النطاق "
                    f"المرجعي {proto['range']} — يلزم مراجعة الطبيب.")
        return (f"تنبيه: نوع الورم '{tumor}' غير موجود بالبروتوكولات المرجعية "
                f"— يلزم مراجعة الطبيب.")

    def recommend(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """إجابة سريرية كاملة لسجل واحد"""
        pred = self.model.predict([record])[0]
        top_factors = self._top_factors(record)
        tumor_raw = record.get(self.tumor_type_key)
        tumor = str(tumor_raw).strip().lower() if tumor_raw not in (None, "") else ""

        if self.model.task_ == "regression":
            unc_list = self.unc.regression_uncertainty(self.model, [record])
            u = unc_list[0] if unc_list else None
            uncertainty = ({"ci_low": u["ci_low"], "ci_high": u["ci_high"], "std": u["std"]}
                           if u else None)
            proto = self._check_protocol(float(pred), tumor)
            requires_review = not proto["in_range"]
            text = self._text_regression(float(pred), tumor, proto)
            unit = self.unit
        else:
            uncertainty = None
            proto = {"range": None, "status": STATUS_NA, "in_range": False}
            requires_review = True
            text = f"التنبؤ تصنيفي ({pred}) وليس جرعة رقمية — يلزم مراجعة الطبيب."
            unit = None

        return {
            "predicted": pred,
            "unit": unit,
            "task": self.model.task_,
            "tumor_type": tumor_raw,
            "uncertainty": uncertainty,
            "top_factors": top_factors,
            "protocol": proto,
            "requires_review": requires_review,
            "recommendation": text,
        }

    def recommend_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """إجابات سريرية لمجموعة"""
        return [self.recommend(r) for r in records]
