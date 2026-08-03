"""
ProtonAI - MC Uncertainty
دمج عدم اليقين بالمدى فيزيائياً: سريري (HU→RSP) + إحصائي MC
الجمع تربيعي (quadrature) لمصدرين مستقلين: total = √(clin² + mc²)
+ أداة اختيار N تاريخ لجعل خطأ MC أصغر من هدفك
"""

import math
import logging
from typing import Dict, Any, Optional

from proton_physics import ProtonPhysics
from range_uncertainty import RangeUncertainty, DEFAULT_UNCERTAINTY
from monte_carlo_physics import MonteCarloPhysics

logger = logging.getLogger("ProtonAI.MCUncertainty")


class MCUncertainty:
    """
    دامج عدم اليقين.
    - combined_uncertainty: سريري + إحصائي + مجموع تربيعي.
    - range_band: نطاق المدى بالـ total (عبر RangeUncertainty).
    - n_histories_for_target: أدنى N يحقق خطأ MC ≤ الهدف.
    """

    def __init__(
        self,
        physics: Optional[ProtonPhysics] = None,
        range_unc: Optional[RangeUncertainty] = None,
        mc: Optional[MonteCarloPhysics] = None,
        clinical_uncertainty: float = DEFAULT_UNCERTAINTY,
    ):
        self.physics = physics if physics is not None else ProtonPhysics()
        self.range_unc = (range_unc if range_unc is not None
                          else RangeUncertainty(self.physics, clinical_uncertainty))
        self.mc = (mc if mc is not None
                   else MonteCarloPhysics(physics=self.physics))

    def combined_uncertainty(
        self, energy_mev: float, n_histories: int
    ) -> Dict[str, float]:
        """الجمع التربيعي لمصدري عدم اليقين المستقلين"""
        clin = self.range_unc.default_uncertainty
        mc_stat = MonteCarloPhysics.relative_statistical_error(n_histories)
        total = math.sqrt(clin ** 2 + mc_stat ** 2)
        return {"clinical": clin, "mc_statistical": mc_stat, "combined": total}

    def range_band(
        self, energy_mev: float, n_histories: int
    ) -> Dict[str, Any]:
        """نطاق المدى بالـ total + المكوّنات"""
        water_range = self.physics.water_range_mm(energy_mev)
        comp = self.combined_uncertainty(energy_mev, n_histories)
        band = self.range_unc.range_band(water_range, uncertainty=comp["combined"])
        return {**band, "components": comp}

    @staticmethod
    def n_histories_for_target(target_mc_error: float) -> int:
        """أدنى N بحيث 1/√N ≤ الهدف (عكس الخطأ الإحصائي)"""
        if target_mc_error <= 0:
            raise ValueError("target_mc_error يجب أن يكون > 0")
        return math.ceil(1.0 / (target_mc_error ** 2))
