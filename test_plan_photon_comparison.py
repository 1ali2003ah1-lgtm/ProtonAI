"""
ProtonAI - Test Proton vs Photon Comparison
"""

import pytest
from plan_photon_comparison import (oar_sparings, integral_reduction,
                                    favors_proton)


class TestSparings:
    def test_positive_savings(self):
        s = oar_sparings("lung_pleura", {"lung_V20": 15, "lung_MLD": 10})
        assert s["lung_V20"] == 20.0 and s["lung_MLD"] == 10.0

    def test_unknown_site(self):
        with pytest.raises(KeyError):
            oar_sparings("nope", {})


class TestIntegral:
    def test_reduction(self):
        assert integral_reduction("lung_pleura", 110) == 50.0


class TestFavors:
    def test_favors_yes(self):
        r = favors_proton("lung_pleura",
                          {"lung_V20": 15, "lung_MLD": 10}, 110)
        assert r["favors_proton"] is True

    def test_favors_no_overdose(self):
        r = favors_proton("lung_pleura",
                          {"lung_V20": 40}, 110)  # تجاوز
        assert r["favors_proton"] is False
