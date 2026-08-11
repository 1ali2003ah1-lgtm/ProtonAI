"""
ProtonAI - Test API Layer
"""

from api_main import quality_response, plan_response, audit_response, CDSS_NOTE
from gov_audit_log import AuditLog


class TestQuality:
    def test_human_ack_mandatory(self):
        r = quality_response({})
        assert r["requires_human_ack"] is True
        assert r["note"] == CDSS_NOTE

    def test_status_passthrough(self):
        r = quality_response({"status": "AMBER"})
        assert r["status"] == "AMBER"


class TestPlan:
    def test_recommendation(self):
        r = plan_response({"recommendation": "proceed", "range_margin_mm": 4})
        assert r["recommendation"] == "proceed"
        assert r["range_margin_mm"] == 4
        assert r["requires_human_ack"] is True


class TestAudit:
    def test_audit_intact(self, tmp_path):
        p = tmp_path / "a.log"
        a = AuditLog(p)
        a.log("dr", "approve", "plan-1")
        r = audit_response(p)
        assert r["intact"] is True
        assert len(r["entries"]) == 1
