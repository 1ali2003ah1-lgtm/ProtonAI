"""
ProtonAI - External Test Sets
تقييم التعميم على مجموعات اختبار خارجية مستقلة
دقة داخلية/خارجية + فجوة تعميم + حد أدنى خارجي + فاصل ثقة 95% + حكم نشر
فجوة كبيرة = فرط تخصيص؛ خارجي منخفض = تعميم ضعيف
"""

import math
import logging
from typing import Dict, Any, List, Sequence, Tuple

logger = logging.getLogger("ProtonAI.ExternalTests")

Z95 = 1.96  # معامل ثقة 95% (تقريب طبيعي)


def _check_pairs(y_true: Sequence, y_pred: Sequence) -> None:
    """التحقق من تطابق وطول القوائم"""
    if len(y_true) == 0:
        raise ValueError("القوائم فارغة")
    if len(y_true) != len(y_pred):
        raise ValueError(f"طول y_true ({len(y_true)}) != y_pred ({len(y_pred)})")


def accuracy(y_true: Sequence, y_pred: Sequence) -> float:
    """دقة بسيطة (نسبة التطابق)"""
    _check_pairs(y_true, y_pred)
    return sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)


def _ci(acc: float, n: int) -> Tuple[float, float]:
    """فاصل ثقة 95% (تقريب طبيعي)، مقصوص لـ [0,1]"""
    half = Z95 * math.sqrt(acc * (1 - acc) / n) if n > 0 else 0.0
    return (max(0.0, acc - half), min(1.0, acc + half))


class ExternalTestEvaluator:
    """
    مقيّم التعميم الخارجي.
    - evaluate: دقة داخلية/خارجية + فجوة + حكم + فواصل ثقة + publication_ready.
    - verdict: robust / moderate / poor حسب فجوة التعميم.
    العتبات قابلة للتخصيص (سريرية/بحثية).
    """

    def __init__(
        self,
        gap_threshold: float = 0.05,   # فجوة <= 5% = متين
        poor_threshold: float = 0.15,  # فجوة > 15% = ضعيف
        external_floor: float = 0.70,  # الحد الأدنى المقبول للخارجي
    ):
        if not (0 <= gap_threshold <= poor_threshold <= 1):
            raise ValueError("العتبات: 0 <= gap_threshold <= poor_threshold <= 1")
        if not (0 <= external_floor <= 1):
            raise ValueError("external_floor يجب أن يكون بين 0 و 1")
        self.gap_threshold = gap_threshold
        self.poor_threshold = poor_threshold
        self.external_floor = external_floor

    def verdict(self, gap: float) -> str:
        """حكم فجوة التعميم"""
        if gap <= self.gap_threshold:
            return "robust"
        if gap <= self.poor_threshold:
            return "moderate"
        return "poor"

    def evaluate(
        self,
        y_int_true: Sequence, y_int_pred: Sequence,
        y_ext_true: Sequence, y_ext_pred: Sequence,
    ) -> Dict[str, Any]:
        """تقييم تعميم كامل: داخلي vs خارجي + فجوة + حكم نشر"""
        int_acc = accuracy(y_int_true, y_int_pred)
        ext_acc = accuracy(y_ext_true, y_ext_pred)
        n_int = len(y_int_true)
        n_ext = len(y_ext_true)
        gap = int_acc - ext_acc
        v = self.verdict(gap)
        ext_ok = ext_acc >= self.external_floor
        pub_ready = bool(v != "poor" and ext_ok)
        logger.info(f"external: int={int_acc:.3f}, ext={ext_acc:.3f}, "
                    f"gap={gap:+.3f}, verdict={v}, pub_ready={pub_ready}")
        return {
            "internal_accuracy": int_acc,
            "external_accuracy": ext_acc,
            "internal_ci": _ci(int_acc, n_int),
            "external_ci": _ci(ext_acc, n_ext),
            "n_internal": n_int, "n_external": n_ext,
            "generalization_gap": gap,
            "verdict": v,
            "external_acceptable": ext_ok,
            "publication_ready": pub_ready,
                 }
