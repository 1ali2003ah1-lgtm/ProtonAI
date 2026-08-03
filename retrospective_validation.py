"""
ProtonAI - Retrospective Validation
تحقق استعادي: إعادة تقييم الأداء على نتائج تاريخية (predicted vs actual)
دقة + حساسية/نوعية/PPV/NPV (ثنائي) + معايرة ثقة + قائمة أخطاء
قائمة الأخطاء تغذي حلقة التحسين (القطعة 6) — إغلاق الدورة البحثية
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ProtonAI.RetroValidation")


def _safe_div(a: float, b: float) -> float:
    """قسمة آمنة (0 عند المقام الصفري — لا انهيار)"""
    return (a / b) if b else 0.0


class RetrospectiveValidator:
    """
    متحقّق استعادي.
    - validate: دقة + (ثنائي إن حُددت التسميات) + معايرة ثقة + أخطاء.
    - positive_label/negative_label: لتفعيل مقاييس المصفوفة الثنائية.
    """

    def __init__(
        self,
        positive_label: Optional[str] = None,
        negative_label: Optional[str] = None,
    ):
        self.positive_label = positive_label
        self.negative_label = negative_label

    def _check(self, records: List[Dict[str, Any]]) -> None:
        if not records:
            raise ValueError("records فارغة")
        for i, r in enumerate(records):
            if "predicted" not in r or "actual" not in r:
                raise ValueError(f"السجل {i} ناقص predicted/actual")

    def validate(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """تقييم استعادي شامل"""
        self._check(records)
        n = len(records)
        correct = [r for r in records if r["predicted"] == r["actual"]]
        errors = [r for r in records if r["predicted"] != r["actual"]]

        out: Dict[str, Any] = {
            "n": n, "accuracy": len(correct) / n,
            "n_correct": len(correct), "n_errors": len(errors),
            "errors": errors,
        }

        # مقاييس المصفوفة الثنائية (إن حُددت التسميتان)
        if self.positive_label is not None and self.negative_label is not None:
            p, ng = self.positive_label, self.negative_label
            tp = sum(1 for r in records if r["predicted"] == p and r["actual"] == p)
            fp = sum(1 for r in records if r["predicted"] == p and r["actual"] == ng)
            fn = sum(1 for r in records if r["predicted"] == ng and r["actual"] == p)
            tn = sum(1 for r in records if r["predicted"] == ng and r["actual"] == ng)
            out.update({
                "confusion": {"TP": tp, "FP": fp, "FN": fn, "TN": tn},
                "sensitivity": _safe_div(tp, tp + fn),
                "specificity": _safe_div(tn, tn + fp),
                "ppv": _safe_div(tp, tp + fp),
                "npv": _safe_div(tn, tn + fn),
            })

        # معايرة الثقة: واثقة لما تصيب؟ مترددة لما تخطئ؟
        confs = [r["confidence"] for r in records
                 if r.get("confidence") is not None]
        if confs:
            cc = [r["confidence"] for r in correct if r.get("confidence") is not None]
            ec = [r["confidence"] for r in errors if r.get("confidence") is not None]
            out["calibration"] = {
                "mean_confidence": sum(confs) / len(confs),
                "confidence_correct": (sum(cc) / len(cc)) if cc else None,
                "confidence_incorrect": (sum(ec) / len(ec)) if ec else None,
            }
        return out
