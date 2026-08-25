"""
ProtonAI - Test Inter-observer Agreement
"""

import numpy as np
import pytest
from agreement import cohens_kappa, interpret_kappa, dice_between


class TestKappa:
    def test_perfect(self):
        assert cohens_kappa([1, 0, 1], [1, 0, 1]) == 1.0

    def test_known_value(self):
        a = [1, 1, 0, 0, 1]
        b = [1, 0, 0, 0, 1]
        assert cohens_kappa(a, b) == pytest.approx(0.615, abs=0.01)

    def test_mismatch_raises(self):
        with pytest.raises(ValueError):
            cohens_kappa([1], [1, 0])


class TestInterpret:
    def test_bands(self):
        assert interpret_kappa(0.9) == "almost perfect"
        assert interpret_kappa(0.5) == "moderate"
        assert interpret_kappa(-0.1) == "poor"


class TestDiceBetween:
    def test_identical(self):
        m = np.ones((4, 4), bool)
        assert dice_between(m, m) == 1.0
