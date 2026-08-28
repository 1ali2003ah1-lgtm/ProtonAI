"""
ProtonAI - Test Control Tower
"""

from case_orchestrator import CaseOrchestrator, CaseSpec
from control_tower import ControlTower


def dossiers(n=2, tamper=False):
    ds = [CaseOrchestrator().run(CaseSpec(f"P-{i}", "prostate"))
          for i in range(n)]
    if tamper:
        ds[0].stages[0].summary = "x"
    return ds


class TestPosture:
    def test_green(self):
        r = ControlTower().run_cycle({"CT-A": [0.02]}, "GREEN", dossiers())
        assert r.posture == "GREEN"

    def test_fleet_red(self):
        r = ControlTower().run_cycle({"CT-A": [0.08]}, "GREEN", dossiers())
        assert r.posture == "RED"

    def test_drift_amber(self):
        r = ControlTower().run_cycle({"CT-A": [0.02]}, "AMBER", dossiers())
        assert r.posture == "AMBER"

    def test_integrity_high(self):
        r = ControlTower().run_cycle({"CT-A": [0.02]}, "GREEN",
                                     dossiers(tamper=True))
        assert r.posture == "RED"


class TestSummary:
    def test_narrative(self):
        r = ControlTower().run_cycle({"CT-A": [0.02]}, "GREEN", dossiers())
        assert "الوضعية العامة" in r.summary
