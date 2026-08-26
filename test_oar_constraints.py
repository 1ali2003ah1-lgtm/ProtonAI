"""
ProtonAI - Test OAR Constraints
"""

import pytest
from oar_constraints import constraints_for, evaluate


class TestCatalog:
    def test_known(self):
        assert len(constraints_for("lung_pleura")) == 2

    def test_unknown_raises(self):
        with pytest.raises(KeyError):
            constraints_for("nope")


class TestEvaluate:
    def test_green(self):
        r = evaluate("lung_pleura", {"lung_V20": 20, "lung_MLD": 10})
        assert r["status"] == "GREEN"

    def test_red(self):
        r = evaluate("lung_pleura", {"lung_V20": 40})
        assert r["status"] == "RED"

    def test_amber_close(self):
        r = evaluate("prostate", {"rectum_V70": 14.5})  # ≥95% من 15
        assert r["status"] == "AMBER"

    def test_skip_missing(self):
        r = evaluate("prostate", {})
        assert r["status"] == "GREEN" and r["rows"] == []
