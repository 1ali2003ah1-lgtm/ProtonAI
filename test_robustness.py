"""
ProtonAI - Test Robustness
"""

from robustness import (default_scenarios, coverage_under, worst_case, status)


class TestCoverage:
    def test_nominal_unchanged(self):
        sc = default_scenarios()[0]
        assert coverage_under(0.98, sc) == 0.98

    def test_shift_reduces(self):
        sc = {"name": "s", "setup_mm": 3, "density_pct": 0, "motion_mm": 0}
        assert coverage_under(0.98, sc) < 0.98

    def test_bigger_margin_more_robust(self):
        sc = {"name": "s", "setup_mm": 3, "density_pct": 0, "motion_mm": 0}
        assert coverage_under(0.98, sc, setup_margin=6) > \
               coverage_under(0.98, sc, setup_margin=3)


class TestWorstCase:
    def test_worst_below_nominal(self):
        w = worst_case(0.98)
        assert w["worst_coverage"] < 0.98
        assert w["worst_scenario"] == "combined"

    def test_all_scenarios_present(self):
        w = worst_case(0.98)
        assert len(w["all"]) == len(default_scenarios())


class TestStatus:
    def test_green(self):
        assert status(0.98, 0.98) == "GREEN"

    def test_amber(self):
        assert status(0.98, 0.95) == "AMBER"

    def test_red(self):
        assert status(0.98, 0.90) == "RED"
