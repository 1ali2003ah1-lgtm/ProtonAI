"""
ProtonAI - Test Case Orchestrator
"""

from case_orchestrator import CaseOrchestrator, CaseSpec
from tumor_board import Opinion


class TestRun:
    def test_minimal(self):
        d = CaseOrchestrator().run(CaseSpec("P-300", "prostate"))
        assert d.final in ("PROCEED", "REVIEW", "STOP")
        assert len(d.stages) >= 4
        assert len(d.integrity) == 64

    def test_full_stages(self):
        d = CaseOrchestrator().run(CaseSpec(
            "P-301", "lung_pleura",
            doses=[2.0] * 10, scanners={"CT-A": [0.02]},
            measured=[2, 2], planned=[2, 2],
            achieved_oars={"lung_V20": 20}))
        names = [s.name for s in d.stages]
        assert {"physics_qa", "phantom_qa", "dose"} <= set(names)

    def test_chain_unique(self):
        d = CaseOrchestrator().run(CaseSpec("P-302", "prostate"))
        hashes = [s.hash for s in d.stages]
        assert len(set(hashes)) == len(hashes)


class TestSafety:
    def test_red_stops(self):
        d = CaseOrchestrator().run(CaseSpec("P-303", "prostate",
                                            status="RED"))
        assert d.final == "STOP"

    def test_board_veto(self):
        d = CaseOrchestrator().run(CaseSpec(
            "P-304", "prostate",
            opinions=[Opinion("أ", "oncologist", "PROCEED", 0.9),
                      Opinion("ب", "physicist", "STOP", 0.9)]))
        assert d.final == "STOP"


class TestExport:
    def test_no_phi(self):
        d = CaseOrchestrator().run(CaseSpec(
            "P-305", "prostate", extra={"patient_name": "SYNTH"}))
        j = d.to_json()
        assert "SYNTH" not in j and "P-305" in j
