"""
ProtonAI - Test MC Tissue Compare
"""

import pytest
from mc_tissue_compare import (analytic_range, mc_range, compare,
                               wepl, residual_range, csda_range_cm)


class TestRanges:
    def test_water_150MeV(self):
        assert csda_range_cm(150) == pytest.approx(15.6, abs=1.0)

    def test_ordering_by_rsp(self):
        e = 150
        assert analytic_range(e, "bone") < analytic_range(e, "water")
        assert analytic_range(e, "water") < analytic_range(e, "lung")

    def test_mc_close_to_analytic(self):
        for t in ["water", "bone", "lung", "muscle"]:
            c = compare(150, t, seed=1)
            assert c["rel_diff"] < 0.05


class TestReproducibility:
    def test_seeded_same(self):
        assert mc_range(150, "water", seed=7) == mc_range(150, "water", seed=7)

    def test_different_seed_differs(self):
        assert mc_range(150, "water", seed=1) != mc_range(150, "water", seed=2)


class TestHeterogeneous:
    def test_wepl_water(self):
        assert wepl([(10, "water")]) == pytest.approx(10.0)

    def test_wepl_bone_higher(self):
        assert wepl([(5, "bone")]) > wepl([(5, "water")])

    def test_residual_reaches(self):
        assert residual_range(150, [(5, "water")]) > 0

    def test_residual_stops(self):
        assert residual_range(100, [(30, "bone")]) < 0
