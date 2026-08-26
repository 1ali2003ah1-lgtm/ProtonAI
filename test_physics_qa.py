"""
ProtonAI - Test Physics QA
"""

from physics_qa import scanner_status, fleet_qa


class TestStatus:
    def test_green(self):
        assert scanner_status(0.02) == "GREEN"

    def test_amber(self):
        assert scanner_status(0.04) == "AMBER"

    def test_red(self):
        assert scanner_status(0.07) == "RED"


class TestFleet:
    def test_all_green(self):
        r = fleet_qa({"CT-A": [0.01, 0.02], "CT-B": [0.02]})
        assert r["overall"] == "GREEN" and r["flagged"] == []

    def test_worst_wins(self):
        r = fleet_qa({"CT-A": [0.01], "CT-B": [0.08]})
        assert r["overall"] == "RED" and r["flagged"] == ["CT-B"]

    def test_amber_overall(self):
        r = fleet_qa({"CT-A": [0.01], "CT-B": [0.045]})
        assert r["overall"] == "AMBER"
