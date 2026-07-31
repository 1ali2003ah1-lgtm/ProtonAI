"""
ProtonAI - Test Gamma Index
اختبارات معيار Gamma (خصائص مضمونة: تطابق/إزاحة/تحجيم/معيار)
"""

import numpy as np
import pytest
from gamma_index import GammaIndex

DEPTHS = np.arange(0, 100, 1.0)


def _gauss(center=50.0, sigma=8.0, height=1.0):
    """منحنى جرعة شكلي (Gaussian) للاختبار"""
    return height * np.exp(-0.5 * ((DEPTHS - center) / sigma) ** 2)


@pytest.fixture
def gi():
    return GammaIndex()


class TestIdentical:
    def test_pass_rate_one(self, gi):
        r = _gauss()
        assert gi.evaluate(r, r, DEPTHS)["pass_rate"] == pytest.approx(1.0)

    def test_gamma_all_zero(self, gi):
        r = _gauss()
        assert np.allclose(gi.evaluate(r, r, DEPTHS)["gamma"], 0.0)

    def test_all_passed(self, gi):
        r = _gauss()
        res = gi.evaluate(r, r, DEPTHS)
        assert res["n_failed"] == 0
        assert res["n_passed"] == res["n_points"]


class TestShifted:
    def test_large_shift_reduces_pass_rate(self, gi):
        res = gi.evaluate(_gauss(), _gauss(center=80.0), DEPTHS)
        assert res["pass_rate"] < 1.0

    def test_identical_beats_large_shift(self, gi):
        r = _gauss()
        rid = gi.evaluate(r, r, DEPTHS)["pass_rate"]
        rsh = gi.evaluate(r, _gauss(center=80.0), DEPTHS)["pass_rate"]
        assert rid > rsh


class TestScaled:
    def test_large_scale_fails(self, gi):
        r = _gauss()
        assert gi.evaluate(r, r * 3.0, DEPTHS)["pass_rate"] < 1.0


class TestDoseMaxEffect:
    def test_larger_dose_max_easier(self):
        r = _gauss()
        e = r * 1.1  # فرق 10%
        strict = GammaIndex(dose_max=1.0).evaluate(r, e, DEPTHS)
        loose = GammaIndex(dose_max=100.0).evaluate(r, e, DEPTHS)
        assert loose["pass_rate"] > strict["pass_rate"]


class TestProperties:
    def test_gamma_non_negative(self, gi):
        g = gi.evaluate(_gauss(), _gauss(center=55.0), DEPTHS)["gamma"]
        assert np.all(g >= 0)

    def test_mean_le_max(self, gi):
        res = gi.evaluate(_gauss(), _gauss(center=55.0), DEPTHS)
        assert res["mean_gamma"] <= res["max_gamma"] + 1e-9

    def test_passed_plus_failed_equals_n(self, gi):
        res = gi.evaluate(_gauss(), _gauss(center=55.0), DEPTHS)
        assert res["n_passed"] + res["n_failed"] == res["n_points"]

    def test_pass_rate_in_unit_interval(self, gi):
        rate = gi.evaluate(_gauss(), _gauss(center=55.0), DEPTHS)["pass_rate"]
        assert 0.0 <= rate <= 1.0


class TestPassFailMap:
    def test_consistent_with_gamma(self, gi):
        r = _gauss()
        e = _gauss(center=55.0)
        g = gi.evaluate(r, e, DEPTHS)["gamma"]
        assert np.array_equal(gi.pass_fail_map(r, e, DEPTHS), g <= 1.0)

    def test_identical_all_true(self, gi):
        r = _gauss()
        assert gi.pass_fail_map(r, r, DEPTHS).all()


class TestFractionPassing:
    def test_threshold_one_equals_pass_rate(self, gi):
        r = _gauss()
        e = _gauss(center=55.0)
        rate = gi.evaluate(r, e, DEPTHS)["pass_rate"]
        assert gi.fraction_passing(r, e, DEPTHS, 1.0) == pytest.approx(rate)

    def test_huge_threshold_is_one(self, gi):
        r = _gauss()
        e = _gauss(center=55.0)
        assert gi.fraction_passing(r, e, DEPTHS, 1e9) == pytest.approx(1.0)

    def test_zero_threshold_on_identical(self, gi):
        r = _gauss()
        assert gi.fraction_passing(r, r, DEPTHS, 0.0) == pytest.approx(1.0)

    def test_negative_threshold_raises(self, gi):
        with pytest.raises(ValueError):
            gi.fraction_passing(_gauss(), _gauss(), DEPTHS, -1)


class TestResultKeys:
    def test_keys(self, gi):
        res = gi.evaluate(_gauss(), _gauss(), DEPTHS)
        for k in ["gamma", "pass_rate", "n_passed", "n_failed", "n_points",
                  "mean_gamma", "max_gamma", "dd_percent", "dta_mm", "dose_max"]:
            assert k in res

    def test_default_dose_max_is_ref_max(self, gi):
        r = _gauss(height=2.5)
        assert gi.evaluate(r, r, DEPTHS)["dose_max"] == pytest.approx(2.5)


class TestGuards:
    def test_length_mismatch_raises(self, gi):
        with pytest.raises(ValueError):
            gi.evaluate(_gauss(), _gauss()[:10], DEPTHS)

    def test_empty_raises(self, gi):
        with pytest.raises(ValueError):
            gi.evaluate(np.array([]), np.array([]), np.array([]))

    def test_invalid_dd_raises(self):
        with pytest.raises(ValueError):
            GammaIndex(dd_percent=0)

    def test_invalid_dta_raises(self):
        with pytest.raises(ValueError):
            GammaIndex(dta_mm=0)

    def test_invalid_dose_max_raises(self):
        with pytest.raises(ValueError):
            GammaIndex(dose_max=0)
        with pytest.raises(ValueError):
            GammaIndex(dose_max=-1)
