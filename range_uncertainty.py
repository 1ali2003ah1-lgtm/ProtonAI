"""
ProtonAI - Range Uncertainty
تحليل عدم يقين مدى البروتون: نطاق المدى + تغطية الهدف + حساسية HU
أكبر مصدر سريري لعدم اليقين = تحويل HU→RSP (~3.5%، Paganetti 2012)
"""

import logging
import numpy as np
from typing import Any, Dict, Optional

from proton_physics import ProtonPhysics

logger = logging.getLogger("ProtonAI.RangeUncertainty")

DEFAULT_UNCERTAINTY = 0.035  # 3.5% — المعيار السريري الشائع لعدم يقين المدى


class RangeUncertainty:
    """
    محلّل عدم يقين المدى.
    - range_band: نطاق [low, high] حول المدى الاسمي بنسبة عدم يقين.
    - target_coverage: هل النطاق داخل منطقة الهدف؟ + overshoot/undershoot.
    - hu_sensitivity: تغيّر المدى عند ±delta بقيم HU (يربط proton_range_in_medium).
    """

    def __init__(
        self,
        physics: Optional[ProtonPhysics] = None,
        default_uncertainty: float = DEFAULT_UNCERTAINTY,
    ):
        if not (0 <= default_uncertainty < 1):
            raise ValueError("default_uncertainty يجب أن يكون بين 0 و 1 (حصراً)")
        self.physics = physics if physics is not None else ProtonPhysics()
        self.default_uncertainty = default_uncertainty

    def _u(self, uncertainty: Optional[float]) -> float:
        """عدم اليقين الفعّال مع التحقق"""
        u = self.default_uncertainty if uncertainty is None else float(uncertainty)
        if not (0 <= u < 1):
            raise ValueError("uncertainty يجب أن يكون بين 0 و 1 (حصراً)")
        return u

    def range_band(
        self, range_mm: float, uncertainty: Optional[float] = None
    ) -> Dict[str, float]:
        """نطاق المدى الاسمي ± نسبة عدم يقين"""
        if range_mm <= 0:
            raise ValueError("range_mm يجب أن يكون > 0")
        u = self._u(uncertainty)
        low = range_mm * (1.0 - u)
        high = range_mm * (1.0 + u)
        return {
            "nominal": range_mm, "low": low, "high": high,
            "uncertainty": u, "width_mm": high - low,
        }

    def target_coverage(
        self,
        range_mm: float,
        target_start_mm: float,
        target_end_mm: float,
        uncertainty: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        هل نطاق عدم اليقين يقع كامل داخل منطقة الهدف؟
        overshoot = تجاوز النهاية، undershoot = عدم بلوغ البداية.
        covers_target = True فقط لو [low,high] ⊂ [start,end].
        """
        if target_end_mm <= target_start_mm:
            raise ValueError("target_end_mm يجب أن يكون > target_start_mm")
        band = self.range_band(range_mm, uncertainty)
        low, high = band["low"], band["high"]
        overshoot = max(0.0, high - target_end_mm)
        undershoot = max(0.0, target_start_mm - low)
        covers = bool(low >= target_start_mm and high <= target_end_mm)
        nominal_in = bool(target_start_mm <= range_mm <= target_end_mm)
        logger.info(f"coverage: nominal_in={nominal_in}, covers={covers}, "
                    f"overshoot={overshoot:.2f}, undershoot={undershoot:.2f}")
        return {
            "nominal": range_mm, "low": low, "high": high,
            "target_start": target_start_mm, "target_end": target_end_mm,
            "nominal_in_target": nominal_in, "covers_target": covers,
            "overshoot_mm": overshoot, "undershoot_mm": undershoot,
        }

    def hu_sensitivity(
        self,
        energy_mev: float,
        hu_profile_1d: Any,
        voxel_mm: float = 1.0,
        hu_delta: float = 50.0,
    ) -> Dict[str, float]:
        """
        تغيّر المدى عند ±delta بقيم HU (مادة أكثف → مدى أقصر).
        يرجع المدى الاسمي/المزاد/المنقوص + مقدار التغيّر (mm و نسبة).
        """
        arr = np.asarray(hu_profile_1d, dtype=float)
        if arr.size == 0:
            raise ValueError("hu_profile_1d فارغ")
        if hu_delta < 0:
            raise ValueError("hu_delta يجب أن يكون >= 0")
        nominal = self.physics.proton_range_in_medium(energy_mev, arr, voxel_mm)
        plus = self.physics.proton_range_in_medium(energy_mev, arr + hu_delta, voxel_mm)
        minus = self.physics.proton_range_in_medium(energy_mev, arr - hu_delta, voxel_mm)
        # التغيّر = نصف المسافة بين الحالتين المتطرفتين (متماثل تقريباً)
        delta_range = (minus - plus) / 2.0
        frac = (delta_range / nominal) if nominal > 0 else 0.0
        return {
            "nominal": nominal, "hu_plus_range": plus, "hu_minus_range": minus,
            "hu_delta": hu_delta, "delta_range_mm": delta_range,
            "delta_range_fraction": frac,
          }
