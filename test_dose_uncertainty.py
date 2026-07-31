"""
ProtonAI - Test Dose Uncertainty
اختبارات تحليل عدم يقين الجرعة (underdose بالهدف + overshoot ورا الهدف)
"""

import numpy as np
import pytest
from dose_uncertainty import DoseUncertainty, DEFAULT_UNCERTAINTY
from proton_physics import ProtonPhysics

DEPTHS = np.arange(0, 150, 1.0)
T_START = 40.0
T_END = 60.0


@pytest.fixture
def du():
    return DoseUncertainty()


class TestScenarioCurves:
    def test_keys_and_shapes(self, du):
        sc = du.scenario_curves(DEPTHS, T_START, T_END)
        assert set(sc.keys()) >= {"nominal", "range_low", "range_high", "uncertainty"}
        for k in ("nominal", "range_low", "range_high"):
            assert sc[k].shape == DEPTHS.shape

    def test_default_uncertainty_stored(self, du):
        sc = du.scenario_curves(DEPTHS, T_START, T_END)
        assert sc["uncertainty"] == pytest.approx(DEFAULT_UNCERTAINTY)

    def test_high_extends_beyond_nominal(self, du):
        # عند 70mm (ورا الهدف الاسمي): high يمدد فيغطيها، nominal انتهى → high > nominal
        sc = du.scenario_curves(DEPTHS, T_START, T_END, uncertainty=0.2)
        assert sc["range_high"][70] > sc["nominal"][70]

    def test_low_starts_earlier(self, du):
        # عند 35mm (قبل الهدف الاسمي): low يبدأ أبكر فيغطيها، nominal = 0
        sc = du.scenario_curves(DEPTHS, T_START, T_END, uncertainty=0.2)
        assert sc["range_low"][35] > sc["nominal"][35]

    def test_zero_uncertainty_all_equal(self, du):
        sc = du.scenario_curves(DEPTHS, T_START, T_END, uncertainty=0.0)
        assert np.allclose(sc["nominal"], sc["range_low"])
        assert np.allclose(sc["nominal"], sc["range_high"])


class TestTargetRobustness:
    def test_zero_uncertainty_fraction_one(self, du):
        r = du.target_dose_robustness(DEPTHS, T_START, T_END, uncertainty=0.0)
        assert r["worst_case_fraction"] == pytest.approx(1.0)
        assert r["worst_case_mean"] == pytest.approx(r["nominal_mean"])

    def test_positive_uncertainty_reduces_fraction(self, du):
        r = du.target_dose_robustness(DEPTHS, T_START, T_END, uncertainty=0.2)
        assert r["worst_case_fraction"] < 1.0
        assert r["worst_case_mean"] < r["nominal_mean"]

    def test_monotonic_with_uncertainty(self, du):
        r1 = du.target_dose_robustness(DEPTHS, T_START, T_END, uncertainty=0.1)
        r2 = du.target_dose_robustness(DEPTHS, T_START, T_END, uncertainty=0.3)
        assert r2["worst_case_fraction"] < r1["worst_case_fraction"]

    def test_nominal_mean_positive(self, du):
        r = du.target_dose_robustness(DEPTHS, T_START, T_END)
        assert r["nominal_mean"] > 0

    def test_result_keys(self, du):
        r = du.target_dose_robustness(DEPTHS, T_START, T_END)
        for k in ["nominal_mean", "low_mean", "high_mean",
                  "worst_case_mean", "worst_case_fraction"]:
            assert k in r


class TestDistalDose:
    def test_zero_uncertainty_no_increase(self, du):
        r = du.distal_dose_worst(DEPTHS, T_START, T_END, distal_depth=70.0,
                                 uncertainty=0.0)
        assert r["absolute_increase"] == pytest.approx(0.0)
        assert r["worst_case"] == pytest.approx(r["nominal"])

    def test_positive_uncertainty_increases(self, du):
        # 70mm ورا الهدف: high scenario يمدد فيرفع الجرعة هناك
        r = du.distal_dose_worst(DEPTHS, T_START, T_END, distal_depth=70.0,
                                 uncertainty=0.2)
        assert r["absolute_increase"] > 0
        assert r["worst_case"] > r["nominal"]

    def test_high_scenario_dominates_distal(self, du):
        r = du.distal_dose_worst(DEPTHS, T_START, T_END, distal_depth=70.0,
                                 uncertainty=0.2)
        assert r["high"] >= r["nominal"]
        assert r["high"] >= r["low"]
        assert r["worst_case"] == pytest.approx(r["high"])

    def test_larger_uncertainty_larger_increase(self, du):
        r1 = du.distal_dose_worst(DEPTHS, T_START, T_END, distal_depth=70.0,
                                  uncertainty=0.1)
        r2 = du.distal_dose_worst(DEPTHS, T_START, T_END, distal_depth=70.0,
                                  uncertainty=0.3)
        assert r2["absolute_increase"] > r1["absolute_increase"]

    def test_invalid_window_raises(self, du):
        with pytest.raises(ValueError):
            du.distal_dose_worst(DEPTHS, T_START, T_END, 70.0, window_mm=-1)

    def test_result_keys(self, du):
        r = du.distal_dose_worst(DEPTHS, T_START, T_END, 70.0)
        for k in ["nominal", "low", "high", "worst_case", "absolute_increase"]:
            assert k in r


class TestPhysicsInjection:
    def test_uses_injected_physics(self):
        custom = ProtonPhysics(range_a=0.03)
        du = DoseUncertainty(physics=custom)
        assert du.physics is custom

    def test_default_builds_physics(self, du):
        assert isinstance(du.physics, ProtonPhysics)


class TestGuards:
    def test_invalid_default_uncertainty(self):
        with pytest.raises(ValueError):
            DoseUncertainty(default_uncertainty=1.0)
        with pytest.raises(ValueError):
            DoseUncertainty(default_uncertainty=-0.1)

    def test_invalid_n_peaks(self):
        with pytest.raises(ValueError):
            DoseUncertainty(n_peaks=0)

    def test_invalid_sigma(self):
        with pytest.raises(ValueError):
            DoseUncertainty(sigma_mm=0)

    def test_invalid_uncertainty_at_call(self, du):
        with pytest.raises(ValueError):
            du.scenario_curves(DEPTHS, T_START, T_END, uncertainty=1.0)
