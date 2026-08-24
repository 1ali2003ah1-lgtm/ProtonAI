"""
ProtonAI - Test Tumor Site Registry
"""

import pytest
from tumor_sites import (SITES, site_profile, expansion_order,
                         by_priority, site_readiness)


class TestRegistry:
    def test_valid_fields(self):
        for n, s in SITES.items():
            assert s["priority"] in (1, 2, 3)
            assert s["behavior"] in ("BENIGN", "MALIGNANT", "IN_SITU", "UNCERTAIN")

    def test_profile(self):
        p = site_profile("CNS_brain_spine")
        assert p["priority"] == 1

    def test_unknown_raises(self):
        with pytest.raises(KeyError):
            site_profile("nope")


class TestOrder:
    def test_first_is_high(self):
        assert site_profile(expansion_order()[0])["priority"] == 1

    def test_covers_all(self):
        assert len(expansion_order()) == len(SITES)

    def test_hematologic_not_top(self):
        # الجهازية/الدم مو بأعلى أولوية
        assert site_profile("lymphoma")["priority"] >= 2


class TestReadiness:
    def test_readiness(self):
        r = site_readiness("lung_pleura")
        assert r["n"] >= 1 and r["margin_mm"] >= 0

    def test_motion_increases_margin(self):
        assert site_readiness("lung_pleura")["margin_mm"] >= \
               site_readiness("CNS_brain_spine")["margin_mm"]
