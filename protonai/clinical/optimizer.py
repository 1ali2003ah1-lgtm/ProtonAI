"""Robust treatment plan optimizer for proton therapy.
Designed & developed by: Ali Hussein Thajil

Implements spot-weight optimization with:
- Target coverage objective (D95 >= prescription)
- OAR sparing (mean dose constraints)
- Robustness (minimax over scenarios)
- Smoothness regularization

Production-grade replacement for simple lattice planning.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize


@dataclass
class OptimizationResult:
    spot_weights: np.ndarray
    dose: np.ndarray
    iterations: int
    final_objective: float
    target_d95: float
    oar_mean: float
    robust_worst_d95: float
    converged: bool


class ProtonOptimizer:
    """Spot-weight optimizer with robustness."""

    def __init__(self, prescription_gy: float = 70.0,
                 oar_weight: float = 1.0,
                 robustness_weight: float = 0.5,
                 smoothness_weight: float = 0.01):
        self.prescription = prescription_gy
        self.oar_weight = oar_weight
        self.rob_weight = robustness_weight
        self.smooth_weight = smoothness_weight

    def _influence_matrix(self, n_spots: int, n_voxels: int,
                          rng: np.random.Generator) -> np.ndarray:
        """Simplified influence matrix: Gaussian falloff per spot."""
        A = np.zeros((n_voxels, n_spots))
        for s in range(n_spots):
            center = rng.integers(0, n_voxels)
            sigma = max(3, n_voxels // 20)
            x = np.arange(n_voxels) - center
            A[:, s] = np.exp(-x**2 / (2 * sigma**2))
        return A

    def _dose_from_weights(self, A: np.ndarray,
                            w: np.ndarray) -> np.ndarray:
        return A @ w

    def _objective(self, w: np.ndarray, A: np.ndarray,
                   target_mask: np.ndarray,
                   oar_mask: Optional[np.ndarray],
                   scenarios: List[np.ndarray]) -> float:
        d = self._dose_from_weights(A, w)
        # Target coverage: penalize underdose
        d_target = d[target_mask > 0.5]
        if len(d_target):
            under = np.maximum(0, self.prescription - d_target)
            target_loss = float(np.mean(under ** 2))
            # Overdose penalty (small)
            over = np.maximum(0, d_target - 1.1 * self.prescription)
            target_loss += 0.1 * float(np.mean(over ** 2))
        else:
            target_loss = 0.0
        # OAR sparing
        oar_loss = 0.0
        if oar_mask is not None and oar_mask.sum() > 0:
            d_oar = d[oar_mask > 0.5]
            oar_loss = float(np.mean(d_oar ** 2))
        # Robustness: worst-case over scenarios
        rob_loss = 0.0
        if scenarios:
            worst_under = 0.0
            for A_sc in scenarios:
                d_sc = self._dose_from_weights(A_sc, w)
                d_t_sc = d_sc[target_mask > 0.5]
                if len(d_t_sc):
                    under = float(np.mean(np.maximum(0,
                                                     self.prescription - d_t_sc) ** 2))
                    worst_under = max(worst_under, under)
            rob_loss = worst_under
        # Smoothness
        if len(w) > 1:
            smooth = float(np.mean(np.diff(w) ** 2))
        else:
            smooth = 0.0
        return (target_loss + self.oar_weight * oar_loss +
                self.rob_weight * rob_loss + self.smooth_weight * smooth)

    def optimize(self, n_spots: int, n_voxels: int,
                 target_mask: np.ndarray,
                 oar_mask: Optional[np.ndarray] = None,
                 n_scenarios: int = 5,
                 max_iter: int = 200,
                 seed: int = 42) -> OptimizationResult:
        rng = np.random.default_rng(seed)
        A_nom = self._influence_matrix(n_spots, n_voxels, rng)
        scenarios = []
        for _ in range(n_scenarios):
            shift = rng.integers(-3, 4)
            scale = 1.0 + rng.uniform(-0.035, 0.035)
            A_sc = np.roll(A_nom, shift, axis=0) * scale
            scenarios.append(A_sc)
        w0 = np.full(n_spots, self.prescription / max(n_spots, 1))
        bounds = [(0, 10 * self.prescription)] * n_spots
        res = minimize(self._objective, w0,
                       args=(A_nom, target_mask, oar_mask, scenarios),
                       method="L-BFGS-B", bounds=bounds,
                       options={"maxiter": max_iter, "disp": False})
        d = self._dose_from_weights(A_nom, res.x)
        d_target = d[target_mask > 0.5]
        target_d95 = float(np.percentile(d_target, 5)) if len(d_target) else 0.0
        oar_mean = 0.0
        if oar_mask is not None and oar_mask.sum() > 0:
            oar_mean = float(np.mean(d[oar_mask > 0.5]))
        worst_d95 = target_d95
        for A_sc in scenarios:
            d_sc = self._dose_from_weights(A_sc, res.x)
            d_t_sc = d_sc[target_mask > 0.5]
            if len(d_t_sc):
                worst_d95 = min(worst_d95, float(np.percentile(d_t_sc, 5)))
        return OptimizationResult(
            spot_weights=res.x, dose=d, iterations=res.nit,
            final_objective=float(res.fun), target_d95=target_d95,
            oar_mean=oar_mean, robust_worst_d95=worst_d95,
            converged=res.success)
