"""
ProtonAI - Test Uncertainty-aware AI
"""

import numpy as np
from uncertainty_aware import (ensemble_mean_std, expected_calibration_error,
                               conformal_threshold, conformal_covered)


class TestEnsemble:
    def test_mean_std(self):
        m, s = ensemble_mean_std([[0.2, 0.4], [0.4, 0.6]])
        assert np.allclose(m, [0.3, 0.5])
        assert s[0] > 0

    def test_identical_zero_std(self):
        m, s = ensemble_mean_std([[0.5, 0.5], [0.5, 0.5]])
        assert np.allclose(s, 0.0)


class TestECE:
    def test_calibrated_low(self):
        conf = [0.5] * 10
        corr = [1] * 5 + [0] * 5
        assert expected_calibration_error(conf, corr) < 0.05

    def test_miscalibrated_high(self):
        conf = [0.9] * 10
        corr = [1] * 5 + [0] * 5
        assert expected_calibration_error(conf, corr) > 0.3

    def test_ordering(self):
        c_cal = expected_calibration_error([0.5] * 10, [1] * 5 + [0] * 5)
        c_mis = expected_calibration_error([0.9] * 10, [1] * 5 + [0] * 5)
        assert c_cal < c_mis


class TestConformal:
    def test_coverage_on_calib(self):
        rng = np.random.default_rng(0)
        scores = rng.uniform(0, 1, 200)
        th = conformal_threshold(scores, alpha=0.1)
        cov = np.mean([conformal_covered(s, th) for s in scores])
        assert cov >= 0.88

    def test_low_score_covered(self):
        th = conformal_threshold([0.1, 0.5, 0.9], alpha=0.1)
        assert conformal_covered(0.05, th) is True
