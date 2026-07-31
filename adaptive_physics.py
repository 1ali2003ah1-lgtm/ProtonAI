"""
ProtonAI - Adaptive Physics Evaluation
التقييم التكيّفي الفيزيائي: يربط حركة الورم (motion_planner) بتوزيع الجرعة
يقرر إعادة التخطيط = اتحاد سببين: انهيار تغطية الجرعة + تغيّر الشكل/الحجم
الجسر بين قمة التصوير (motion) والفيزياء (dose_curve)
"""

import logging
import numpy as np
from typing import Any, Dict, List, Optional

from motion_planner import MotionPlanner

logger = logging.getLogger("ProtonAI.AdaptivePhysics")

DEFAULT_DOSE_THRESHOLD_FRAC = 0.95   # الجرعة "الفعّالة" = 95% من الذروة
DEFAULT_COVERAGE_DROP_THRESHOLD = 0.1  # انهيار تغطية > 10% → إعادة تخطيط


class AdaptivePhysics:
    """
    مقيّم التكيّف الفيزيائي.
    - coverage: نسبة بكسلات الورم المغطاة بجرعة فعّالة (dose >= frac*max).
    - evaluate: يقارن خطة التخطيط بالوضع الحالي → تقرير + needs_replan + أسباب.
    needs_replan = (coverage_drop > عتبة) OR (motion_planner يقول replan).
    """

    def __init__(
        self,
        motion_planner: Optional[MotionPlanner] = None,
        dice_threshold: float = 0.9,
        volume_change_threshold: float = 0.2,
    ):
        self.motion = (motion_planner if motion_planner is not None
                       else MotionPlanner(dice_threshold=dice_threshold,
                                          volume_change_threshold=volume_change_threshold))

    def _check_1d(self, *arrays: Any) -> List[np.ndarray]:
        """تحويل لـ 1D float/bool مع التحقق من تطابق الأحجام"""
        out = [np.asarray(a) for a in arrays]
        shapes = {a.shape for a in out}
        if len(shapes) != 1:
            raise ValueError(f"الأحجام مختلفة: {[a.shape for a in out]}")
        if out[0].size == 0:
            raise ValueError("المدخلات فارغة")
        return out

    def coverage(
        self, profile: Any, dose_curve: Any,
        dose_threshold_frac: float = DEFAULT_DOSE_THRESHOLD_FRAC,
    ) -> float:
        """
        نسبة بكسلات الورم (profile=True) المغطاة بجرعة فعّالة.
        جرعة فعّالة = dose >= frac * max(dose). ورم فاضي → 1.0 (vacuously).
        """
        if not (0 <= dose_threshold_frac <= 1):
            raise ValueError("dose_threshold_frac يجب أن يكون بين 0 و 1")
        prof, dose = self._check_1d(profile, dose_curve)
        prof = prof.astype(bool)
        dose = dose.astype(float)
        dmax = float(dose.max())
        if dmax <= 0:
            raise ValueError("dose_curve يجب أن يحتوي قيماً موجبة (توزيع جرعة صالح)")
        n_tumor = int(prof.sum())
        if n_tumor == 0:
            return 1.0
        effective = dose >= (dose_threshold_frac * dmax)
        return float((prof & effective).sum()) / n_tumor

    def evaluate(
        self,
        plan_profile: Any,
        current_profile: Any,
        dose_curve: Any,
        dose_threshold_frac: float = DEFAULT_DOSE_THRESHOLD_FRAC,
        coverage_drop_threshold: float = DEFAULT_COVERAGE_DROP_THRESHOLD,
    ) -> Dict[str, Any]:
        """
        تقييم تكيّفي: خطة التخطيط vs الوضع الحالي.
        يرجع تغطيتين + الانهيار + فحص الحركة + needs_replan + أسباب.
        """
        if coverage_drop_threshold < 0:
            raise ValueError("coverage_drop_threshold يجب أن يكون >= 0")
        plan_b, cur_b, dose = self._check_1d(plan_profile, current_profile, dose_curve)
        plan_b = plan_b.astype(bool)
        cur_b = cur_b.astype(bool)

        nom_cov = self.coverage(plan_b, dose, dose_threshold_frac)
        cur_cov = self.coverage(cur_b, dose, dose_threshold_frac)
        drop = nom_cov - cur_cov  # موجب = انهيار؛ سالب = تحسّن (لا يفعّل)

        motion = self.motion.adaptive_check(plan_b, cur_b)

        reasons: List[str] = []
        if drop > coverage_drop_threshold:
            reasons.append("coverage_drop")
        if motion["needs_replan"]:
            if motion["dice"] < self.motion.dice_threshold:
                reasons.append("motion_dice")
            if abs(motion["volume_change_fraction"]) > self.motion.volume_change_threshold:
                reasons.append("motion_volume")

        needs_replan = bool(reasons)
        logger.info(f"adaptive_physics: nom_cov={nom_cov:.3f}, cur_cov={cur_cov:.3f}, "
                    f"drop={drop:+.3f}, replan={needs_replan}, reasons={reasons}")
        return {
            "nominal_coverage": nom_cov,
            "current_coverage": cur_cov,
            "coverage_drop": drop,
            "coverage_drop_threshold": coverage_drop_threshold,
            "motion": motion,
            "needs_replan": needs_replan,
            "reasons": reasons,
}
