"""
ProtonAI - Test Dossier Forensics
"""

from case_orchestrator import CaseOrchestrator, CaseSpec
from dossier_verify import verify_dossier, verify_stages


class TestVerify:
    def test_valid(self):
        d = CaseOrchestrator().run(CaseSpec("P-400", "prostate"))
        assert verify_dossier(d)["valid"] is True

    def test_tamper_summary(self):
        d = CaseOrchestrator().run(CaseSpec("P-401", "prostate"))
        d.stages[1].summary = "tampered"
        r = verify_dossier(d)
        assert r["valid"] is False and r["broken_at"] == 1

    def test_tamper_hash(self):
        d = CaseOrchestrator().run(CaseSpec("P-402", "prostate"))
        d.stages[0].hash = "f" * 64
        assert verify_dossier(d)["valid"] is False

    def test_empty_valid(self):
        assert verify_stages([])["valid"] is True
