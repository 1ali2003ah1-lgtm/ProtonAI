"""
ProtonAI - Test MC Uncertainty
اختبارات دمج عدم اليقين (تربيعي + نطاق + اختيار N)
"""

import math
import pytest
from mc_uncertainty import MCUncertainty
from monte_carlo_physics import MonteCarloPhysics


@pytest.fixture
def u():
    return MCUncertainty()


class TestCombined:
    def test_quadrature_formula(self, u):
        c = u.combined_uncertainty(100.0, 10000)
        expected = math.sqrt(c["clinical"] ** 2 + c["mc_statistical"] ** 2)
        assert c["combined"] == pytest.approx(expected)

    def test_mc_term_value(self, u):
        c = u.combined_uncertainty(100.0, 100)
        assert c["mc_statistical"] == pytest.approx(0.1)

    def test_combined_dominates_each(self, u):
        c = u.combined_uncertainty(100.0, 100)
        assert c["combined"] >= c["clinical"]
        assert c["combined"] >= c["mc_statistical"]

    def test_more_histories_approaches_clinical(self, u):
        few = u.combined_uncertainty(100.0, 100)
        many = u.combined_uncertainty(100.0, 10_000_000)
        # كلما زاد N اقترب المجموع من السريري (وما ينزل تحته)
        assert many["combined"] < few["combined"]
        assert many["combined"] >= many["clinical"]


class TestRangeBand:
    def test_band_order(self, u):
        b = u.range_band(100.0, 10000)
        assert b["low"] < b["nominal"] < b["high"]

    def test_components_present(self, u):
        b = u.range_band(100.0, 10000)
        assert "components" in b
        assert b["components"]["combined"] == pytest.approx(b["uncertainty"])

    def test_wider_than_clinical_only(self, u):
        b = u.range_band(100.0, 100)  # خطأ MC كبير → نطاق أوسع
        clin = u.range_unc.default_uncertainty
        assert b["uncertainty"] > clin


class TestNHistories:
    def test_achieves_target(self, u):
        n = MCUncertainty.n_histories_for_target(0.01)
        assert 1.0 / math.sqrt(n) <= 0.01

    def test_value(self):
        assert MCUncertainty.n_histories_for_target(0.1) == 100

    def test_smaller_target_needs_more(self):
        assert (MCUncertainty.n_histories_for_target(0.01)
                > MCUncertainty.n_histories_for_target(0.1))

    def test_invalid_target_raises(self):
        with pytest.raises(ValueError):
            MCUncertainty.n_histories_for_target(0)
        with pytest.raises(ValueError):
            MCUncertainty.n_histories_for_target(-0.1)


class TestInjection:
    def test_defaults_built(self, u):
        from range_uncertainty import RangeUncertainty
        assert isinstance(u.range_unc, RangeUncertainty)
        assert isinstance(u.mc, MonteCarloPhysics)

    def test_uses_injected(self):
        mc = MonteCarloPhysics()
        x = MCUncertainty(mc=mc)
        assert x.mc is mc
