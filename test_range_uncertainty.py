"""
ProtonAI - Test Range Uncertainty
اختبارات تحليل عدم يقين المدى
"""

import numpy as np
import pytest
from range_uncertainty import RangeUncertainty, DEFAULT_UNCERTAINTY
from proton_physics import ProtonPhysics


@pytest.fixture
def ru():
    return RangeUncertainty()


class TestRangeBand:
    def test_order(self, ru):
        b = ru.range_band(100.0)
        assert b["low"] < b["nominal"] < b["high"]

    def test_default_uncertainty(self, ru):
        b = ru.range_band(100.0)
        assert b["uncertainty"] == pytest.approx(DEFAULT_UNCERTAINTY)
        assert b["low"] == pytest.approx(100.0 * (1 - DEFAULT_UNCERTAINTY))
        assert b["high"] == pytest.approx(100.0 * (1 + DEFAULT_UNCERTAINTY))

    def test_width(self, ru):
        b = ru.range_band(100.0, uncertainty=0.1)
        assert b["width_mm"] == pytest.approx(20.0)

    def test_zero_uncertainty_collapses(self, ru):
        b = ru.range_band(100.0, uncertainty=0.0)
        assert b["low"] == b["high"] == b["nominal"]
        assert b["width_mm"] == 0.0

    def test_custom_uncertainty(self, ru):
        b = ru.range_band(200.0, uncertainty=0.05)
        assert b["low"] == pytest.approx(190.0)
        assert b["high"] == pytest.approx(210.0)

    def test_invalid_range_raises(self, ru):
        with pytest.raises(ValueError):
            ru.range_band(0)

    def test_invalid_uncertainty_raises(self, ru):
        with pytest.raises(ValueError):
            ru.range_band(100.0, uncertainty=1.0)
        with pytest.raises(ValueError):
            ru.range_band(100.0, uncertainty=-0.1)


class TestTargetCoverage:
    def test_fully_inside_covers(self, ru):
        # nominal=50, u=0.035 → [48.25, 51.75] داخل [40,60]
        c = ru.target_coverage(50.0, 40.0, 60.0)
        assert c["covers_target"] is True
        assert c["overshoot_mm"] == 0.0
        assert c["undershoot_mm"] == 0.0
        assert c["nominal_in_target"] is True

    def test_overshoot(self, ru):
        # nominal=50, u=0.1 → high=55 > target_end=50
        c = ru.target_coverage(50.0, 40.0, 50.0, uncertainty=0.1)
        assert c["covers_target"] is False
        assert c["overshoot_mm"] == pytest.approx(5.0)
        assert c["undershoot_mm"] == 0.0

    def test_undershoot(self, ru):
        # nominal=50, u=0.1 → low=45 < target_start=50
        c = ru.target_coverage(50.0, 50.0, 60.0, uncertainty=0.1)
        assert c["covers_target"] is False
        assert c["undershoot_mm"] == pytest.approx(5.0)
        assert c["overshoot_mm"] == 0.0

    def test_nominal_outside_target(self, ru):
        c = ru.target_coverage(80.0, 40.0, 60.0, uncertainty=0.0)
        assert c["nominal_in_target"] is False
        assert c["covers_target"] is False

    def test_invalid_target_raises(self, ru):
        with pytest.raises(ValueError):
            ru.target_coverage(50.0, 60.0, 40.0)

    def test_result_keys(self, ru):
        c = ru.target_coverage(50.0, 40.0, 60.0)
        for k in ["nominal", "low", "high", "covers_target",
                  "overshoot_mm", "undershoot_mm", "nominal_in_target"]:
            assert k in c


class TestHUSensitivity:
    def test_direction_denser_shorter(self, ru):
        # ماء: hu+delta (أكثف) → مدى أقصر، hu-delta (أخف) → مدى أطول
        profile = np.zeros(300)
        s = ru.hu_sensitivity(100.0, profile, voxel_mm=1.0, hu_delta=100.0)
        assert s["hu_plus_range"] < s["nominal"] < s["hu_minus_range"]

    def test_delta_positive(self, ru):
        profile = np.zeros(300)
        s = ru.hu_sensitivity(100.0, profile, voxel_mm=1.0, hu_delta=100.0)
        assert s["delta_range_mm"] > 0

    def test_zero_delta_zero_change(self, ru):
        profile = np.zeros(300)
        s = ru.hu_sensitivity(100.0, profile, voxel_mm=1.0, hu_delta=0.0)
        assert s["delta_range_mm"] == pytest.approx(0.0)
        assert s["hu_plus_range"] == pytest.approx(s["nominal"])

    def test_larger_delta_larger_change(self, ru):
        profile = np.zeros(300)
        s1 = ru.hu_sensitivity(100.0, profile, voxel_mm=1.0, hu_delta=50.0)
        s2 = ru.hu_sensitivity(100.0, profile, voxel_mm=1.0, hu_delta=200.0)
        assert s2["delta_range_mm"] > s1["delta_range_mm"]

    def test_fraction_consistent(self, ru):
        profile = np.zeros(300)
        s = ru.hu_sensitivity(100.0, profile, voxel_mm=1.0, hu_delta=100.0)
        assert s["delta_range_fraction"] == pytest.approx(
            s["delta_range_mm"] / s["nominal"])

    def test_empty_raises(self, ru):
        with pytest.raises(ValueError):
            ru.hu_sensitivity(100.0, np.array([]))

    def test_negative_delta_raises(self, ru):
        with pytest.raises(ValueError):
            ru.hu_sensitivity(100.0, np.zeros(10), hu_delta=-1.0)


class TestPhysicsInjection:
    def test_uses_injected_physics(self):
        custom = ProtonPhysics(range_a=0.03)  # ثوابت مختلفة
        ru = RangeUncertainty(physics=custom)
        assert ru.physics is custom

    def test_default_builds_physics(self, ru):
        assert isinstance(ru.physics, ProtonPhysics)


class TestGuards:
    def test_invalid_default_uncertainty(self):
        with pytest.raises(ValueError):
            RangeUncertainty(default_uncertainty=1.0)
        with pytest.raises(ValueError):
            RangeUncertainty(default_uncertainty=-0.1)
