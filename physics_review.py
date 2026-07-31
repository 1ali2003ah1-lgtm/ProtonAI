"""
ProtonAI - Physics Review Loop
حلقة مراجعة الفيزيائي الطبي: إحالة تلقائية للحالات الفيزيائية المشبوهة
تلّف physician_review (composition) وتضيف قواعد فيزيائية فوقه
gamma_fail / coverage_drop / range_out / rbe_out
الأسباب الفيزيائية تُخزّن بـ record["physics_reasons"] (مصدر حقيقة واحد)
"""

import logging
from typing import List, Dict, Any, Optional

from physician_review import PhysicianReviewLoop, ReviewRequest

logger = logging.getLogger("ProtonAI.PhysicsReview")

DEFAULT_GAMMA_THRESHOLD = 0.9          # pass_rate < 90% → إحالة
DEFAULT_COVERAGE_DROP_THRESHOLD = 0.1  # انهيار تغطية > 10% → إحالة
DEFAULT_RBE_RANGE = (1.0, 1.2)         # النطاق السريري المقبول للـ RBE


class PhysicsReviewLoop:
    """
    حلقة مراجعة الفيزيائي الطبي.
    - flag_physics: يبني الأسباب الفيزيائية، ويحيل عبر physician_review إن وُجدت.
    - submit_decision / pending / completed: تمرير للحلقة الداخلية.
    - physics_stats: إحصاءات بالأسباب الفيزيائية (تُمسح من record، لا حالة مكررة).
    - save / load: تمرير للحلقة الداخلية.
    """

    def __init__(
        self,
        review_loop: Optional[PhysicianReviewLoop] = None,
        audit: Any = None,
        gamma_threshold: float = DEFAULT_GAMMA_THRESHOLD,
        coverage_drop_threshold: float = DEFAULT_COVERAGE_DROP_THRESHOLD,
        rbe_range: tuple = DEFAULT_RBE_RANGE,
    ):
        if not (0 <= gamma_threshold <= 1):
            raise ValueError("gamma_threshold يجب أن يكون بين 0 و 1")
        if coverage_drop_threshold < 0:
            raise ValueError("coverage_drop_threshold يجب أن يكون >= 0")
        rlo, rhi = float(rbe_range[0]), float(rbe_range[1])
        if rlo <= 0 or rhi <= 0 or rlo >= rhi:
            raise ValueError("rbe_range يجب أن يكون (low, high) بقيم موجبة و low < high")
        self.gamma_threshold = gamma_threshold
        self.coverage_drop_threshold = coverage_drop_threshold
        self.rbe_range = (rlo, rhi)
        # الحلقة الداخلية: محقونة أو مبنية (مع audit اختياري)
        self.review = (review_loop if review_loop is not None
                       else PhysicianReviewLoop(audit=audit))

    def flag_physics(
        self,
        sample_id: str,
        prediction: Any,
        true_value: Any = None,
        gamma_pass_rate: Optional[float] = None,
        coverage_drop: Optional[float] = None,
        range_in_target: Optional[bool] = None,
        rbe: Optional[float] = None,
        record: Optional[Dict[str, Any]] = None,
    ) -> Optional[ReviewRequest]:
        """
        إحالة فيزيائية إن خالفت قاعدة واحدة على الأقل، وإلا None.
        الأسباب الفيزيائية تُحفظ بـ record["physics_reasons"] + التفاصيل.
        """
        reasons: List[str] = []
        if gamma_pass_rate is not None and gamma_pass_rate < self.gamma_threshold:
            reasons.append("gamma_fail")
        if coverage_drop is not None and coverage_drop > self.coverage_drop_threshold:
            reasons.append("coverage_drop")
        if range_in_target is not None and not range_in_target:
            reasons.append("range_out")
        if rbe is not None and (rbe < self.rbe_range[0] or rbe > self.rbe_range[1]):
            reasons.append("rbe_out")

        if not reasons:
            return None

        merged: Dict[str, Any] = dict(record or {})
        merged["physics_reasons"] = reasons
        merged["gamma_pass_rate"] = gamma_pass_rate
        merged["coverage_drop"] = coverage_drop
        merged["range_in_target"] = range_in_target
        merged["rbe"] = rbe

        # out_of_protocol=True = trigger الإحالة بالحلقة الداخلية
        # (التفسير: الحالة خارج البروتوكول الفيزيائي المقبول)
        req = self.review.flag_for_review(
            sample_id, prediction, true_value=true_value,
            out_of_protocol=True, record=merged)
        logger.info(f"إحالة فيزيائية {req.request_id} ({sample_id}): {reasons}")
        return req

    def submit_decision(
        self, request_id: str, reviewer_id: str,
        decision: Any, notes: str = "",
    ) -> ReviewRequest:
        """تسجيل قرار الفيزيائي (تمرير للحلقة الداخلية)"""
        return self.review.submit_decision(request_id, reviewer_id, decision, notes)

    def pending(self) -> List[ReviewRequest]:
        """الطلبات الفيزيائية المنتظرة"""
        return self.review.pending()

    def completed(self) -> List[ReviewRequest]:
        """الطلبات الفيزيائية المُراجعة"""
        return self.review.completed()

    def physics_stats(self) -> Dict[str, Any]:
        """
        إحصاءات بالأسباب الفيزيائية (تُمسح من record، لا حالة مكررة).
        by_physics_reason: عدّاد لكل سبب فيزيائي عبر كل الطلبات.
        """
        by_reason: Dict[str, int] = {}
        for r in self.review.requests:
            for reason in (r.record or {}).get("physics_reasons", []):
                by_reason[reason] = by_reason.get(reason, 0) + 1
        base = self.review.stats()
        return {
            "total_flagged": base["total_flagged"],
            "pending_count": base["pending_count"],
            "completed_count": base["completed_count"],
            "by_decision": base["by_decision"],
            "by_physics_reason": by_reason,
        }

    def save(self, path) -> None:
        """حفظ سجل المراجعات (تمرير)"""
        self.review.save(path)

    def load(self, path) -> None:
        """تحميل سجل المراجعات (تمرير)"""
        self.review.load(path)
