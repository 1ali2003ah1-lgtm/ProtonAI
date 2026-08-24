"""
ProtonAI - Test Sample Size
"""

import pytest
from sample_size import sample_size, per_site_plan, pilot_reestimate


class TestFormula:
    def test_example_62(self):
        assert sample_size(0.08, 0.02) == 62

    def test_bigger_sd_bigger_n(self):
        assert sample_size(0.10, 0.02) > sample_size(0.08, 0.02)

    def test_tighter_width_bigger_n(self):
        assert sample_size(0.08, 0.01) > sample_size(0.08, 0.02)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            sample_size(0.08, 0)


class TestPlan:
    def test_per_site(self):
        plan = per_site_plan({"brain": 0.08, "lung": 0.10})
        assert plan["brain"] == 62
        assert plan["lung"] > plan["brain"]

    def test_pilot_reestimate(self):
        assert pilot_reestimate(0.12) > pilot_reestimate(0.08)
