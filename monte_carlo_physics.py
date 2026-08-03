"""
ProtonAI - Monte Carlo Physics
محاكاة Monte Carlo حقيقية لمنحنى عمق-جرعة البروتون (numpy صرفة، مبثترة)
كل تاريخ بروتون: مدى مسحوب من Normal(CSDA, straggling) + ترسب Bragg
مدى مُقدّر من الذروة + خطأ إحصائي ~ 1/√N + تحقق مقابل النموذج التحليلي
"""

import logging
import numpy as np
from typing import Any, Dict, Optional

from proton_physics import ProtonPhysics

logger = logging.getLogger("ProtonAI.MonteCarloPhysics")

STRAGGLE_FRACTION = 0.012  # انحراف المدى ~1.2% (straggling فيزيائي واقعي)


class MonteCarloPhysics:
    """
    محاكي Monte Carlo.
    - simulate_depth_dose: منحنى عمق-جرعة من N تاريخ (مبثتر، قابل للتكرار ببذرة).
    - estimate_range: المدى المُقدّر (عمق الذروة).
    - relative_statistical_error: خطأ إحصائي نسبي ~ 1/√N.
    - validate_vs_analytic: مقارنة MC بالنموذج التحليلي (CSDA).
    """

    def __init__(
        self,
        physics: Optional[ProtonPhysics] = None,
        seed: Optional[int] = None,
        bragg_sigma_mm: float = 2.0,
    ):
        if bragg_sigma_mm <= 0:
            raise ValueError("bragg_sigma_mm يجب أن يكون > 0")
        self.physics = physics if physics is not None else ProtonPhysics()
        self.seed = seed
        self.bragg_sigma_mm = bragg_sigma_mm

    def simulate_depth_dose(
        self,
        energy_mev: float,
        n_histories: int = 1000,
        depths: Any = None,
        seed: Optional[int] = None,
    ) -> np.ndarray:
        """منحنى عمق-جرعة من N تاريخ بروتون (مبثتر بالكامل)"""
        if energy_mev <= 0:
            raise ValueError("energy_mev يجب أن يكون > 0")
        if n_histories <= 0:
            raise ValueError("n_histories يجب أن يكون > 0")
        R = self.physics.water_range_mm(energy_mev)
        if depths is None:
            depths = np.arange(0.0, R * 1.3, 1.0)
        z = np.asarray(depths, dtype=float)
        rng = np.random.RandomState(seed if seed is not None else self.seed)
        ranges = rng.normal(R, STRAGGLE_FRACTION * R, n_histories)
        # بثترة: مصفوفة (أعماق × تواريخ) ثم متوسط على التواريخ
        zm = z[:, None]
        rm = ranges[None, :]
        peak = np.exp(-0.5 * ((zm - rm) / self.bragg_sigma_mm) ** 2)
        plateau = np.where(zm <= rm, 0.3 * np.clip(zm / rm, 0.0, 1.0), 0.0)
        return (peak + plateau).mean(axis=1)

    def estimate_range(
        self, energy_mev: float, n_histories: int = 1000, seed: Optional[int] = None
    ) -> float:
        """المدى المُقدّر = عمق ذروة منحنى MC"""
        R = self.physics.water_range_mm(energy_mev)
        depths = np.arange(0.0, R * 1.3, 1.0)
        dose = self.simulate_depth_dose(energy_mev, n_histories, depths, seed)
        return float(depths[int(np.argmax(dose))])

    @staticmethod
    def relative_statistical_error(n_histories: int) -> float:
        """خطأ إحصائي نسبي ~ 1/√N (يتناقص مع عدد التواريخ)"""
        if n_histories <= 0:
            raise ValueError("n_histories يجب أن يكون > 0")
        return 1.0 / np.sqrt(n_histories)

    def validate_vs_analytic(
        self, energy_mev: float, n_histories: int = 2000, seed: Optional[int] = None
    ) -> Dict[str, float]:
        """مقارنة مدى MC بالمدى التحليلي (CSDA)"""
        mc = self.estimate_range(energy_mev, n_histories, seed)
        an = self.physics.water_range_mm(energy_mev)
        return {"mc_range": mc, "analytic_range": an,
                "rel_diff": abs(mc - an) / an}
