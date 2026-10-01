"""B3 v2: radiobiology guard (6 tests)."""
from __future__ import annotations

import numpy as np

from tcp_ntcp import (LUNG_N, LUNG_TD50, TCP_D50_GY, geud, ntcp_lkb,
                        tcp_logistic)


def test_tcp_midpoint_and_monotonic():
    assert tcp_logistic(TCP_D50_GY) == 0.5
    x = tcp_logistic(np.array([10, 30, 60, 90]))
    assert np.all(np.diff(x) > 0)


def test_ntcp_midpoint():
    dose = np.full((10, 10), LUNG_TD50); m = np.ones((10, 10))
    assert abs(ntcp_lkb(dose, m) - 0.5) < 1e-9


def test_geud_volume_effect():
    dose = np.array([[30.0, 5.0]])
    m = np.ones((1, 2))
    g = geud(dose, m, n=LUNG_N)
    assert dose.mean() - 1e-9 <= g <= dose.max() + 1e-9


def test_ntcp_monotonic():
    m = np.ones((10, 10))
    lo = ntcp_lkb(np.full((10, 10), 10.0), m)
    hi = ntcp_lkb(np.full((10, 10), 50.0), m)
    assert lo < hi


def test_ai_clinical_benefit():
    from tcp_ntcp import clinical_impact
    ct, truth, oar, ai, base = [], [], [], [], []
    for i in range(8):
        c = np.zeros((60, 40)); t = np.zeros((60, 40)); o = np.zeros((60, 40))
        r0 = 20 + i
        t[r0:r0 + 10, 10:30] = 1; o[r0 + 11:r0 + 18, :] = 1
        ct.append(c); truth.append(t); oar.append(o)
        ai.append(np.roll(t, 1, axis=0)); base.append(np.roll(t, 4, axis=0))
    res = clinical_impact(ct, truth, oar, ai, base)
    assert res["tcp_delta"].mean() > 0.05
    assert res["ntcp_delta"].mean() >= -1e-9


def test_params_documented():
    import tcp_ntcp
    assert tcp_ntcp.RX_GY == 60.0 and tcp_ntcp.LUNG_M == 0.45
