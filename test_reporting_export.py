"""
ProtonAI - Test Reporting Export
"""

from clinical_report import build_report
from reporting_export import scrub, to_json, to_text


class TestScrub:
    def test_removes_phi(self):
        r = {"case_id": "P-1", "patient_name": "X", "mrn": "123"}
        s = scrub(r)
        assert "patient_name" not in s and "mrn" not in s
        assert s["case_id"] == "P-1"


class TestExport:
    def test_json_no_phi(self):
        rep = build_report("P-9", "prostate", 0.9, 0.02)
        rep["patient_name"] = "SYNTH"
        j = to_json(rep)
        assert "SYNTH" not in j and "P-9" in j

    def test_text(self):
        rep = build_report("P-9", "prostate", 0.9, 0.02)
        assert "القرار" in to_text(rep)
