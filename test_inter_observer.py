"""P5-S2: agreement suite sensitivity + dual-criteria guard (8 tests)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tools.inter_observer_study import (HD95_TOL_MM, THRESHOLD, dilate,
                                        erode, hd95, jitter, shift, study)

CONF = Path("inter_observer_study.json")


def _block(lo, hi, n=40):
    m = np.zeros((n, n))
    m[lo:hi, lo:hi] = 1.0
    return m


def _bar():
    m = np.zeros((40, 40))
    m[20, :] = 1.0
    return m


def test_identity_pass():
    m = _block(10, 30)
    res = study([(m, m)])
    assert res["mean_dice"] == 1.0 and res["mean_hd95"] == 0.0
    assert res["verdict"] == "PASS"


def test_disjoint_fails():
    res = study([(_block(0, 10), _block(20, 30))])
    assert res["mean_dice"] == 0.0
    assert res["mean_hd95"] > HD95_TOL_MM
    assert res["verdict"] == "FAIL"


def test_hd95_exact_on_pure_shift():
    assert hd95(_bar(), shift(_bar(), 2)) == pytest.approx(2.0)


def test_symmetry():
    a, b = _block(10, 30), _block(12, 30)
    assert hd95(a, b) == hd95(b, a)
    assert study([(a, b)])["mean_dice"] == study([(b, a)])["mean_dice"]


def test_degradation_monotonic():
    m = _block(5, 35)
    d1 = study([(m, erode(m, 1))])
    d3 = study([(m, erode(m, 3))])
    assert d3["mean_dice"] <= d1["mean_dice"]
    assert d3["mean_hd95"] >= d1["mean_hd95"]


def test_operators_matrix_in_artifact():
    a = json.loads(CONF.read_text(encoding="utf-8"))
    for k in ("erode1", "dilate1", "shift2", "jitter"):
        assert k in a["operators_mean_dice"]


def test_ci_contains_mean():
    a = json.loads(CONF.read_text(encoding="utf-8"))
    lo, hi = a["ci95_dice"]
    assert lo <= a["mean_dice"] <= hi


def test_dual_verdict_consistency():
    a = json.loads(CONF.read_text(encoding="utf-8"))
    expect = ("PASS" if (a["mean_dice"] >= THRESHOLD
                         and a["mean_hd95"] <= HD95_TOL_MM) else "FAIL")
    assert a["verdict"] == expect
