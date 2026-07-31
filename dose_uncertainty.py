"""
ProtonAI - Dose Uncertainty
تحليل عدم يقين الجرعة الناتج عن عدم يقين المدى
worst-case تغطية الهدف (underdose) + worst-case جرعة ورا الهدف (overshoot)
يعتمد على ProtonPhysics (SOBP) عبر dependency injection
"""

import logging
import numpy as np
from typing import Any, Dict, Optional

from proton_physics import ProtonPhysics

logger = logging.getLogger("ProtonAI.DoseUncertainty")

DEFAULT_UNCERTAINTY = 0.035  # 3.5% — نفس المعيار السريري لعدم يقين المدى


class DoseUncertainty:
    """
    محلّل عدم يقين الجرعة.
    - scenario_curves: ثلاث منحنيات SOBP (nominal / range_low / range_high).
    - target_dose_robustness: أسوأ نقص جرعة بمنطقة الهدف عبر السيناريوهات.
    - distal_dose_worst: أسوأ زيادة جرعة بعمق ورا الهدف عبر السيناريوهات.
    إزاحة المدى بنسبة u = إزاحة نطاق توقف الـ SOBP بنفس النسبة.
    """

    def __init__(
        self,
        physics: Optional[ProtonPhysics] = None,
        default_uncertainty: float = DEFAULT_UNCERTAINTY,
        n_peaks: int = 5,
        sigma_mm: float = 2.0,
    ):
        if not (0 <= default_uncertainty < 1):
            raise ValueError("default_uncertainty يجب أن يكون بين 0 و 1 (حصراً)")
        if n_peaks < 1:
            raise ValueError("n_peaks يجب أن يكون >= 1")
        if sigma_mm <= 0:
            raise ValueError("sigma_mm يجب أن يكون > 0")
        self.physics = physics if physics is not None else ProtonPhysics()
        self.default_uncertainty = default_uncertainty
        self.n_peaks = n_peaks
        self.sigma_mm = sigma_mm

    def _u(self, uncertainty: Optional[float]) -> float:
        """عدم اليقين الفعّال مع التحقق"""
        u = self.default_uncertainty if uncertainty is None else float(uncertainty)
        if not (0 <= u < 1):
            raise ValueError("uncertainty يجب أن يكون بين 0 و 1 (حصراً)")
        return u

    def _shifted_sobp(
        self, depths: np.ndarray, target_start: float, target_end: float, shift_frac: float
    ) -> np.ndarray:
        """SOBP مع إزاحة نطاق التوقف بنسبة shift_frac (موجب = مدى أطول)"""
        f = 1.0 + shift_frac
        return self.physics.sobp(
            depths, target_start * f, target_end * f,
            n_peaks=self.n_peaks, sigma_mm=self.sigma_mm)

    def scenario_curves(
        self, depths: Any, target_start: float, target_end: float,
        uncertainty: Optional[float] = None,
    ) -> Dict[str, Any]:
        """ثلاث منحنيات SOBP: nominal + range_low + range_high"""
        u = self._u(uncertainty)
        z = np.asarray(depths, dtype=float)
        return {
            "nominal": self._shifted_sobp(z, target_start, target_end, 0.0),
            "range_low": self._shifted_sobp(z, target_start, target_end, -u),
            "range_high": self._shifted_sobp(z, target_start, target_end, +u),
            "uncertainty": u,
        }

    def _mean_in_window(self, depths: Any, curve: Any, a: float, b: float) -> float:
        """متوسط الجرعة بنافذة [a, b] (0 لو النافذة فاضية)"""
        d = np.asarray(depths)
        mask = (d >= a) & (d <= b)
        if not mask.any():
            return 0.0
        return float(np.asarray(curve)[mask].mean())

    def target_dose_robustness(
        self, depths: Any, target_start: float, target_end: float,
        uncertainty: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        أسوأ نقص جرعة بمنطقة الهدف عبر السيناريوهات الثلاثة.
        worst_case_fraction = worst_mean / nominal_mean (1 = متين، <1 = نقص).
        """
        sc = self.scenario_curves(depths, target_start, target_end, uncertainty)
        nom = self._mean_in_window(depths, sc["nominal"], target_start, target_end)
        low = self._mean_in_window(depths, sc["range_low"], target_start, target_end)
        high = self._mean_in_window(depths, sc["range_high"], target_start, target_end)
        worst = min(nom, low, high)
        frac = (worst / nom) if nom > 0 else 0.0
        logger.info(f"target robustness: nominal={nom:.3f}, worst_frac={frac:.3f}")
        return {
            "nominal_mean": nom, "low_mean": low, "high_mean": high,
            "worst_case_mean": worst, "worst_case_fraction": frac,
        }

    def distal_dose_worst(
        self, depths: Any, target_start: float, target_end: float,
        distal_depth: float, uncertainty: Optional[float] = None,
        window_mm: float = 2.0,
    ) -> Dict[str, float]:
        """
        أسوأ زيادة جرعة بعمق ورا الهدف (distal edge / OAR) عبر السيناريوهات.
        absolute_increase = worst - nominal (موجب = overshoot).
        """
        if window_mm < 0:
            raise ValueError("window_mm يجب أن يكون >= 0")
        sc = self.scenario_curves(depths, target_start, target_end, uncertainty)
        a, b = distal_depth - window_mm, distal_depth + window_mm
        nom = self._mean_in_window(depths, sc["nominal"], a, b)
        low = self._mean_in_window(depths, sc["range_low"], a, b)
        high = self._mean_in_window(depths, sc["range_high"], a, b)
        worst = max(nom, low, high)
        return {
            "nominal": nom, "low": low, "high": high,
            "worst_case": worst, "absolute_increase": worst - nom,
          }
