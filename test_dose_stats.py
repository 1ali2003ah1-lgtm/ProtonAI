"""B2 v2: paired dose-impact statistics guard (6 tests)."""
from __future__ import annotations

import numpy as np

from dose_stats import (bootstrap_ci, dose_impact, paired_deltas,
                        verdict_for, wilcoxon_p)


def _cases(ai_shift, base_shift, n=8):
    ct, truth, ai, base = [], [], [], []
    for i in range(n):
        c = np.zeros((60, 40)); t = np.zeros((60, 40))
        r0 = 20 + i
        t[r0:r0 + 10, 10:30] = 1
        ct.append(c); truth.append(t)
        ai.append(np.roll(t, ai_shift, axis=0))
        base.append(np.roll(t, base_shift, axis=0))
    return ct, truth, ai, base


def test_zero_delta_when_identical():
    ct, truth, ai, _ = _cases(2, 2)
    d = paired_deltas(ct, truth, ai, ai)
    assert np.allclose(d, 0)
    lo, hi = bootstrap_ci(d)
    assert lo <= 0 <= hi


def test_ai_superior_signal():
    ct, truth, ai, base = _cases(1, 4)
    d = paired_deltas(ct, truth, ai, base)
    assert d.mean() > 0 and wilcoxon_p(d) < 0.05


def test_ci_ordering():
    ct, truth, ai, base = _cases(1, 4)
    d = paired_deltas(ct, truth, ai, base)
    lo, hi = bootstrap_ci(d)
    assert lo <= d.mean() <= hi


def test_bootstrap_seed_determinism():
    x = np.array([0.1, 0.2, 0.3, 0.4])
    assert bootstrap_ci(x, seed=1) == bootstrap_ci(x, seed=1)


def test_verdict_rules():
    assert verdict_for(0.05, 0.1, 0.01) == "SUPERIOR"
    assert verdict_for(-0.01, 0.01, 0.2) == "NON_INFERIOR"
    assert verdict_for(-0.1, -0.05, 0.5) == "NOT_ESTABLISHED"


def test_full_impact_two_endpoints():
    ct, truth, ai, base = _cases(1, 4)
    res = dose_impact(ct, truth, ai, base)
    assert set(res) == {"d95", "oar_v20"}
    assert res["d95"]["verdict"] in ("SUPERIOR", "NON_INFERIOR")
