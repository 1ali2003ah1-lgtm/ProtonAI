"""
ProtonAI - Batched Monte Carlo (Device Phase)
محاكاة MC على دفعات ثابتة الذاكرة: تشتغل بملايين التواريخ بدون انفجار
المتوسط الموزون acc += mean_chunk * chunk ثم /n = صحيح رياضياً
دفعة واحدة ≥ N تطابق نسخة المرحلة 9 تماماً (نفس البذور)
"""

import logging
import numpy as np
from typing import Any, Optional

from monte_carlo_physics import MonteCarloPhysics, STRAGGLE_FRACTION

logger = logging.getLogger("ProtonAI.BatchedMC")


class BatchedMonteCarlo(MonteCarloPhysics):
    """
    محاكي MC بدفعات.
    - simulate_depth_dose: تجميع على دفعات (ذاكرة محدودة مهما كبر N).
    - يرث estimate_range / validate_vs_analytic / relative_statistical_error.
    """

    def __init__(
        self,
        physics=None,
        seed: Optional[int] = None,
        bragg_sigma_mm: float = 2.0,
        chunk_size: int = 10000,
    ):
        super().__init__(physics=physics, seed=seed, bragg_sigma_mm=bragg_sigma_mm)
        if chunk_size <= 0:
            raise ValueError("chunk_size يجب أن يكون > 0")
        self.chunk_size = chunk_size

    def simulate_depth_dose(
        self,
        energy_mev: float,
        n_histories: int = 1000,
        depths: Any = None,
        seed: Optional[int] = None,
        chunk_size: Optional[int] = None,
    ) -> np.ndarray:
        """منحنى عمق-جرعة بتجميع دفعات (ذاكرة O(أعماق × دفعة))"""
        if energy_mev <= 0:
            raise ValueError("energy_mev يجب أن يكون > 0")
        if n_histories <= 0:
            raise ValueError("n_histories يجب أن يكون > 0")
        R = self.physics.water_range_mm(energy_mev)
        if depths is None:
            depths = np.arange(0.0, R * 1.3, 1.0)
        z = np.asarray(depths, dtype=float)
        chunk = chunk_size or self.chunk_size
        rng = np.random.RandomState(seed if seed is not None else self.seed)
        acc = np.zeros(len(z))
        done = 0
        while done < n_histories:
            c = min(chunk, n_histories - done)
            ranges = rng.normal(R, STRAGGLE_FRACTION * R, c)
            zm = z[:, None]
            rm = ranges[None, :]
            peak = np.exp(-0.5 * ((zm - rm) / self.bragg_sigma_mm) ** 2)
            plateau = np.where(zm <= rm, 0.3 * np.clip(zm / rm, 0.0, 1.0), 0.0)
            acc += (peak + plateau).mean(axis=1) * c
            done += c
        return acc / n_histories
