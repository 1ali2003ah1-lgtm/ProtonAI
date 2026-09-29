"""P5-S1: unified clinical confidence score (ADR-007).

Fuses two independent uncertainty sources into one conservative per-plan
score in [0,1]:
- model epistemic: seed-ensemble vote entropy (Phase 3, ADR-006)
- physics/dose: clinical range + MC statistical (mc_uncertainty)

Combination: multiplicative conjunction (conservative AND) - if either
layer is uncertain, confidence drops. Additive module: wraps
mc_uncertainty without modifying it.
"""
from __future__ import annotations

import math

from mc_uncertainty import MCUncertainty

LN2 = math.log(2.0)
DEFAULT_ENERGY_MEV = 150.0
DEFAULT_TARGET_MC_ERROR = 0.01


def model_confidence(vote_entropy: float) -> float:
    """1 - normalized vote entropy (entropy naturally in [0, ln 2])."""
    return 1.0 - min(1.0, max(0.0, vote_entropy / LN2))


def physics_confidence(energy_mev: float = DEFAULT_ENERGY_MEV,
                       n_histories: int | None = None) -> float:
    u = MCUncertainty()
    n = n_histories or MCUncertainty.n_histories_for_target(
        DEFAULT_TARGET_MC_ERROR)
    comp = u.combined_uncertainty(energy_mev, n)
    return 1.0 - min(1.0, comp["combined"])


def unified_confidence(vote_entropy: float,
                       energy_mev: float = DEFAULT_ENERGY_MEV,
                       n_histories: int | None = None) -> float:
    return model_confidence(vote_entropy) * physics_confidence(
        energy_mev, n_histories)


def review_required(confidence: float, threshold: float) -> bool:
    return confidence < threshold
