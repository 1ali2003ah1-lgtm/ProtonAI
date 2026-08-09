"""
ProtonAI - Test Segmentation Metrics
"""

import numpy as np
import pytest
from seg_metrics import dice, hd95, assd, report


def _square(shift=0):
    m = np.zeros((12, 12), bool)
    m[2 + shift:6 + shift, 2:6] = True
    return m


class TestDice:
    def test_identical(self):
        assert dice(_square(), _square()) == 1.0

    def test_disjoint(self):
        a = _square()
        b = np.zeros((12, 12), bool)
        b[8:, 8:] = True
        assert dice(a, b) == 0.0

    def test_both_empty(self):
        assert dice(np.zeros((5, 5), bool), np.zeros((5, 5), bool)) == 1.0

    def test_one_empty(self):
        assert dice(_square(), np.zeros((12, 12), bool)) == 0.0


class TestDistances:
    def test_identical_zero(self):
        assert hd95(_square(), _square()) == 0.0
        assert assd(_square(), _square()) == 0.0

    def test_shifted_small(self):
        assert hd95(_square(), _square(1)) == pytest.approx(1.0, abs=0.5)
        assert 0 < assd(_square(), _square(1)) < 1.5

    def test_empty_inf(self):
        assert hd95(_square(), np.zeros((12, 12), bool)) == float("inf")


class TestReport:
    def test_keys(self):
        r = report(_square(), _square())
        assert set(r) == {"dice", "hd95", "assd"}
        assert r["dice"] == 1.0
