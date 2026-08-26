"""
ProtonAI - Test DVH Metrics
"""

import numpy as np
from dose_stats import D, V, plan_metrics


class TestD:
    def test_uniform(self):
        assert D(95, [2.0] * 10) == 2.0

    def test_known(self):
        assert D(95, np.arange(1, 101)) == np.percentile(np.arange(1, 101), 5)


class TestV:
    def test_fraction(self):
        assert V(2, [1, 2, 3]) == 2 / 3

    def test_all(self):
        assert V(1, [1, 2, 3]) == 1.0


class TestPlan:
    def test_perfect(self):
        m = plan_metrics([2.0] * 20, 2.0)
        assert m["D95"] == 1.0 and m["V100"] == 1.0 and m["HI"] == 0.0

    def test_underdose(self):
        m = plan_metrics([1.0] * 20, 2.0)
        assert m["V100"] == 0.0
