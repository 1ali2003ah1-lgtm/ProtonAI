"""
ProtonAI - Test Monte Carlo Physics
اختبارات محاكاة MC (تكرار ببذرة + مدى + خطأ إحصائي + تحقق)
"""

import numpy as np
import pytest
from monte_carlo_physics import MonteCarloPhysics, STRAGGLE_FRACTION
from proton_physics import ProtonPhysics


@pytest.fixture
def mc():
    return MonteCarloPhysics(seed=42)


class TestDepthDose:
    def test_non_negative_and_positive(self, mc):
        dose = mc.simulate_depth_dose(100.0, n_histories=200)
        assert np.all(dose >= 0)
        assert dose.sum() > 0

    def test_shape_matches_depths(self, mc):
        depths = np.arange(0, 100, 1.0)
        dose = mc.simulate_depth_dose(100.0, 200, depths)
        assert dose.shape == depths.shape

    def test_seed_reproducible(self, mc):
        d1 = mc.simulate_depth_dose(100.0, 300, seed=7)
        d2 = mc.simulate_depth_dose(100.0, 300, seed=7)
        assert np.allclose(d1, d2)

    def test_different_seed_differs(self, mc):
        d1 = mc.simulate_depth_dose(100.0, 300, seed=1)
        d2 = mc.simulate_depth_dose(100.0, 300, seed=2)
        assert not np.allclose(d1, d2)

    def test_peak_near_range(self, mc):
        R = mc.physics.water_range_mm(100.0)
        depths = np.arange(0, R * 1.3, 1.0)
        dose = mc.simulate_depth_dose(100.0, 2000, depths, seed=42)
        peak_depth = depths[int(np.argmax(dose))]
        assert abs(peak_depth - R) / R < 0.06

    def test_falls_off_after_range(self, mc):
        R = mc.physics.water_range_mm(100.0)
        depths = np.arange(0, R * 1.3, 1.0)
        dose = mc.simulate_depth_dose(100.0, 2000, depths, seed=42)
        far = dose[depths > R * 1.15]
        assert far.max() < dose.max() * 0.2


class TestEstimateRange:
    def test_close_to_analytic(self, mc):
        R = mc.physics.water_range_mm(100.0)
        est = mc.estimate_range(100.0, 2000, seed=42)
        assert abs(est - R) / R < 0.06

    def test_monotonic_with_energy(self, mc):
        e1 = mc.estimate_range(80.0, 1500, seed=42)
        e2 = mc.estimate_range(150.0, 1500, seed=42)
        assert e1 < e2


class TestStatisticalError:
    def test_decreases_with_n(self):
        assert (MonteCarloPhysics.relative_statistical_error(100)
                > MonteCarloPhysics.relative_statistical_error(10000))

    def test_value(self):
        assert MonteCarloPhysics.relative_statistical_error(100) == pytest.approx(0.1)

    def test_invalid_n_raises(self):
        with pytest.raises(ValueError):
            MonteCarloPhysics.relative_statistical_error(0)


class TestValidate:
    def test_rel_diff_small(self, mc):
        v = mc.validate_vs_analytic(100.0, 2000, seed=42)
        assert v["rel_diff"] < 0.06
        assert v["analytic_range"] == pytest.approx(
            mc.physics.water_range_mm(100.0))

    def test_keys(self, mc):
        v = mc.validate_vs_analytic(100.0, 500, seed=1)
        for k in ["mc_range", "analytic_range", "rel_diff"]:
            assert k in v


class TestGuards:
    def test_invalid_energy_raises(self, mc):
        with pytest.raises(ValueError):
            mc.simulate_depth_dose(-10.0)

    def test_invalid_histories_raises(self, mc):
        with pytest.raises(ValueError):
            mc.simulate_depth_dose(100.0, n_histories=0)

    def test_invalid_bragg_sigma_raises(self):
        with pytest.raises(ValueError):
            MonteCarloPhysics(bragg_sigma_mm=0)


class TestInjection:
    def test_default_builds_physics(self, mc):
        assert isinstance(mc.physics, ProtonPhysics)

    def test_uses_injected(self):
        p = ProtonPhysics(range_a=0.03)
        m = MonteCarloPhysics(physics=p)
        assert m.physics is p
