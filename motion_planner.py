"""
ProtonAI - Motion / Adaptive Planner
معالجة حركة المريض (التنفس) في تخطيط البروتون
ITV (اتحاد أطوار التنفس) + هامش أمان من سعة الحركة + فحص تكيّفي لإعادة التخطيط
كله numpy، بدون بيانات 4D حقيقية (تُمرَّر أقنعة الأطوار يدوياً أو من نموذج)
"""

import math
import logging
import numpy as np
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ProtonAI.MotionPlanner")


def _shift(mask: np.ndarray, dr: int, dc: int) -> np.ndarray:
    """إزاحة قناع بمقدار (dr, dc) مع تصفير الحواف (بدون التفاف)"""
    out = np.zeros_like(mask)
    H, W = mask.shape
    r0_src = max(0, -dr)
    r1_src = H - max(0, dr)
    c0_src = max(0, -dc)
    c1_src = W - max(0, dc)
    length_r = r1_src - r0_src
    length_c = c1_src - c0_src
    if length_r <= 0 or length_c <= 0:
        return out
    r0_dst = max(0, dr)
    c0_dst = max(0, dc)
    out[r0_dst:r0_dst + length_r, c0_dst:c0_dst + length_c] = \
        mask[r0_src:r0_src + length_r, c0_src:c0_src + length_c]
    return out


class MotionPlanner:
    """
    مخطط الحركة.
    - compute_itv: اتحاد أقنعة أطوار التنفس = المنطقة الآمنة (ITV).
    - expand_margin: توسيع قناع بهامش (قرص بنصف قطر r بكسل).
    - motion_margin_from_amplitude: سعة الحركة (mm) → نصف قطر (بكسل).
    - adaptive_check: مقارنة قناع التخطيط بقناع اليوم → هل يلزم إعادة تخطيط.
    """

    def __init__(
        self,
        dice_threshold: float = 0.9,
        volume_change_threshold: float = 0.2,
    ):
        if not (0 <= dice_threshold <= 1):
            raise ValueError("dice_threshold يجب أن يكون بين 0 و 1")
        if volume_change_threshold < 0:
            raise ValueError("volume_change_threshold يجب أن يكون >= 0")
        self.dice_threshold = dice_threshold
        self.volume_change_threshold = volume_change_threshold

    @staticmethod
    def _to_bool(pixels: Any) -> np.ndarray:
        """تحويل آمن إلى قناع bool"""
        arr = np.asarray(pixels)
        if arr.size == 0:
            raise ValueError("القناع فارغ")
        return arr.astype(bool)

    def compute_itv(self, phase_masks: List[Any]) -> np.ndarray:
        """
        اتحاد أقنعة أطوار التنفس = ITV.
        كل طور قناع bool؛ النتيجة بكسل True لو ظهر بأي طور.
        """
        if not phase_masks:
            raise ValueError("phase_masks فارغة (يلزم طور واحد على الأقل)")
        masks = [self._to_bool(m) for m in phase_masks]
        shape = masks[0].shape
        for i, m in enumerate(masks):
            if m.shape != shape:
                raise ValueError(f"الطور {i} بحجم {m.shape} ≠ الطور 0 {shape}")
        itv = np.zeros(shape, dtype=bool)
        for m in masks:
            itv |= m
        return itv

    def expand_margin(self, mask: Any, radius_voxels: int) -> np.ndarray:
        """توسيع قناع بهامش قرصي بنصف قطر r بكسل (r=0 → بدون تغيير)"""
        m = self._to_bool(mask)
        if radius_voxels < 0:
            raise ValueError("radius_voxels يجب أن يكون >= 0")
        if radius_voxels == 0:
            return m.copy()
        out = m.copy()
        r = radius_voxels
        for dr in range(-r, r + 1):
            for dc in range(-r, r + 1):
                if dr * dr + dc * dc <= r * r:  # قرص (هامش متساوي الاتجاه)
                    out |= _shift(m, dr, dc)
        return out

    @staticmethod
    def motion_margin_from_amplitude(
        amplitude_mm: float, voxel_size_mm: float
    ) -> int:
        """سعة الحركة (mm) → نصف قطر هامش (بكسل)، مُقرَّب للأعلى (تحفظاً)"""
        if amplitude_mm < 0:
            raise ValueError("amplitude_mm يجب أن يكون >= 0")
        if voxel_size_mm <= 0:
            raise ValueError("voxel_size_mm يجب أن يكون > 0")
        return math.ceil(amplitude_mm / voxel_size_mm)

    def adaptive_check(
        self,
        plan_mask: Any,
        current_mask: Any,
        dice_threshold: Optional[float] = None,
        volume_change_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        مقارنة قناع التخطيط بقناع اليوم.
        needs_replan = True لو Dice < العتبة أو تغيّر الحجم > العتبة.
        """
        a = self._to_bool(plan_mask)
        b = self._to_bool(current_mask)
        if a.shape != b.shape:
            raise ValueError(f"حجم القناعين مختلف: {a.shape} ≠ {b.shape}")
        dt = self.dice_threshold if dice_threshold is None else dice_threshold
        vt = self.volume_change_threshold if volume_change_threshold is None else volume_change_threshold
        sa = int(a.sum())
        sb = int(b.sum())
        inter = int((a & b).sum())
        if sa + sb == 0:
            dice = 1.0  # كلاهما فارغ → متطابقان
        else:
            dice = 2.0 * inter / (sa + sb)
        if sa > 0:
            vol_change = (sb - sa) / sa
        else:
            vol_change = 1.0 if sb > 0 else 0.0
        needs_replan = bool((dice < dt) or (abs(vol_change) > vt))
        logger.info(f"adaptive_check: dice={dice:.3f}, vol_change={vol_change:+.3f}, "
                    f"replan={needs_replan}")
        return {
            "dice": dice,
            "volume_change_fraction": vol_change,
            "needs_replan": needs_replan,
            "plan_volume": sa,
            "current_volume": sb,
      }
