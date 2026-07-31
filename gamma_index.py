"""
ProtonAI - Gamma Index
معيار Gamma العالمي لمقارنة توزيعي جرعة (reference vs evaluated)
يجمع فرق الجرعة (DD%) والمسافة المكانية (DTA mm) بمقياس واحد
gamma <= 1 = مقبول. مستقل عن المحرك الفيزيائي (مقارنة عامة بين أي توزيعين)
"""

import logging
import numpy as np
from typing import Any, Dict, Optional

logger = logging.getLogger("ProtonAI.GammaIndex")


class GammaIndex:
    """
    حساب Gamma Index (1D، global normalization).
    - evaluate: يحسب gamma لكل نقطة + pass_rate + إحصاءات.
    - pass_fail_map: قناع bool (gamma <= 1).
    - fraction_passing: نسبة النقاط تحت عتبة gamma معيّنة.
    المعيار: dd_percent (%) من dose_max، dta_mm (mm).
    """

    def __init__(
        self,
        dd_percent: float = 3.0,
        dta_mm: float = 3.0,
        dose_max: Optional[float] = None,
    ):
        if dd_percent <= 0:
            raise ValueError("dd_percent يجب أن يكون > 0")
        if dta_mm <= 0:
            raise ValueError("dta_mm يجب أن يكون > 0")
        if dose_max is not None and dose_max <= 0:
            raise ValueError("dose_max يجب أن يكون > 0 إن مُرّر")
        self.dd_percent = dd_percent
        self.dta_mm = dta_mm
        self.dose_max = dose_max

    def _resolve_dose_max(self, reference: np.ndarray) -> float:
        """dose_max الفعّال: المُمرَّر أو max(reference)"""
        if self.dose_max is not None:
            return float(self.dose_max)
        return float(reference.max())

    def _gamma_matrix(
        self, reference: np.ndarray, evaluated: np.ndarray, depths: np.ndarray
    ) -> np.ndarray:
        """مصفوفة gamma (N_eval, N_ref) ثم الحد الأدنى لكل نقطة eval"""
        dmax = self._resolve_dose_max(reference)
        dd = self.dd_percent / 100.0 * dmax
        dose_diff = evaluated[:, None] - reference[None, :]
        # لو dd<=0 (dose_max=0) → لا فرق جرعة ذي معنى → dose_term=0
        dose_term = (dose_diff / dd) ** 2 if dd > 0 else np.zeros_like(dose_diff)
        dist_term = ((depths[:, None] - depths[None, :]) / self.dta_mm) ** 2
        return np.sqrt(dose_term + dist_term)

    def evaluate(
        self, reference: Any, evaluated: Any, depths: Any
    ) -> Dict[str, Any]:
        """حساب Gamma الكامل، يرجع gamma + pass_rate + إحصاءات"""
        ref = np.asarray(reference, dtype=float)
        ev = np.asarray(evaluated, dtype=float)
        d = np.asarray(depths, dtype=float)
        if ref.size == 0 or ev.size == 0 or d.size == 0:
            raise ValueError("reference/evaluated/depths لا يمكن أن تكون فارغة")
        if not (ref.shape == ev.shape == d.shape):
            raise ValueError("reference/evaluated/depths يجب أن تكون بنفس الحجم")
        gamma = self._gamma_matrix(ref, ev, d).min(axis=1)
        passed = gamma <= 1.0
        n = int(gamma.size)
        n_passed = int(passed.sum())
        rate = n_passed / n if n else 0.0
        logger.info(f"gamma: pass_rate={rate:.3f} "
                    f"(DD={self.dd_percent}%/DTA={self.dta_mm}mm)")
        return {
            "gamma": gamma, "pass_rate": rate,
            "n_passed": n_passed, "n_failed": n - n_passed, "n_points": n,
            "mean_gamma": float(gamma.mean()), "max_gamma": float(gamma.max()),
            "dd_percent": self.dd_percent, "dta_mm": self.dta_mm,
            "dose_max": self._resolve_dose_max(ref),
        }

    def pass_fail_map(
        self, reference: Any, evaluated: Any, depths: Any
    ) -> np.ndarray:
        """قناع bool: True حيث gamma <= 1"""
        return self.evaluate(reference, evaluated, depths)["gamma"] <= 1.0

    def fraction_passing(
        self, reference: Any, evaluated: Any, depths: Any, threshold: float = 1.0
    ) -> float:
        """نسبة النقاط التي gamma <= threshold"""
        if threshold < 0:
            raise ValueError("threshold يجب أن يكون >= 0")
        g = self.evaluate(reference, evaluated, depths)["gamma"]
        return float((g <= threshold).sum()) / g.size if g.size else 0.0
