"""B1 v2: calibrated proton dose bridge guard (7 tests)."""
from __future__ import annotations

import numpy as np
import pytest

from dose_bridge import (compute_dose, dvh, dvh_metrics, hu_to_rsp,
                         oar_v20, robust_d95, water_equivalent_depth)


@pytest.fixture()
def phantom():
    ct = np.zeros((60, 40))
    mask = np.zeros((60, 40)); mask[25:35, 10:30] = 1
    oar = np.zeros((60, 40)); oar[45:55, :] = 1
    return ct, mask, oar


def test_schneider_calibration():
    assert hu_to_rsp(np.array([0.0]))[0] == pytest.approx(1.0)
    assert hu_to_rsp(np.array([-1000.0]))[0] == pytest.approx(0.001)
    assert hu_to_rsp(np.array([1000.0]))[0] == pytest.approx(1.40)


def test_wed_monotonic():
    assert np.all(np.diff(water_equivalent_depth(np.ones((10, 5)))[:, 0]) > 0)


def test_bragg_sobp_shape(phantom):
    ct, mask, _ = phantom
    dose = compute_dose(ct, mask)
    assert dose[mask > 0].mean() == pytest.approx(1.0, abs=0.15)
    assert dose[0, :].mean() < 0.6          # entrance lower than plateau
    assert dose[-1, :].max() < 0.25         # distal falloff


def test_dvh_monotonic_and_metrics(phantom):
    ct, mask, _ = phantom
    bins, cum = dvh(compute_dose(ct, mask), mask)
    assert np.all(np.diff(cum) <= 1e-9)
    m = dvh_metrics(compute_dose(ct, mask), mask)
    assert m["D95"] <= m["D2"] <= m["Dmax"] and 0 <= m["HI"] <= 1


def test_oar_sparing(phantom):
    ct, mask, oar = phantom
    assert oar_v20(compute_dose(ct, mask), oar) < 0.5


def test_range_uncertainty_worst_case(phantom):
    ct, mask, _ = phantom
    nom = dvh_metrics(compute_dose(ct, mask), mask)["D95"]
    assert robust_d95(ct, mask) <= nom + 1e-9


def test_sensitivity_to_contour_error(phantom):
    ct, mask, _ = phantom
    dose = compute_dose(ct, mask)      # plan on AI/good contour
    shifted = np.roll(mask, 6, axis=0)  # ground-truth mismatch
    good = dvh_metrics(dose, mask)["D95"]
    bad = dvh_metrics(dose, shifted)["D95"]
    assert good > 0.9 and good - bad > 0.2
