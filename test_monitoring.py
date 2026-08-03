"""
ProtonAI - Test Operational Monitoring
اختبارات المراقبة (تجميع + ملخص + تنبيهات + لوحة)
"""

import pytest
from monitoring import Monitoring
from decision_model import DecisionRecord, Recommendation
from access_control import User, Role


def _rec(audit_rows):
    m = Monitoring()
    m.add_audit(audit_rows)
    return m


def _decision(rec="approve", override=False):
    return DecisionRecord(
        recommendation=Recommendation(rec), recommendation_reason="r",
        can_deliver=True, delivery_blockers=[], overall_status="GREEN",
        physician_signed=True, physics_signed=True, override=override)


AUDIT = [
    {"action": "deliver", "outcome": "SUCCESS", "role": "admin"},
    {"action": "sign", "outcome": "SUCCESS", "role": "physician"},
    {"action": "deliver", "outcome": "DENIED", "role": "viewer"},
]


class TestAddAudit:
    def test_action_counts(self):
        s = _rec(AUDIT).summary()
        assert s["actions"]["deliver"] == 2
        assert s["actions"]["sign"] == 1
        assert s["total_actions"] == 3

    def test_denied_counted(self):
        assert _rec(AUDIT).summary()["denied_access"] == 1

    def test_by_role(self):
        s = _rec(AUDIT).summary()
        assert s["by_role"]["admin"] == 1
        assert s["by_role"]["viewer"] == 1
        assert s["by_role"]["physician"] == 1

    def test_empty_audit(self):
        s = _rec([]).summary()
        assert s["total_actions"] == 0
        assert s["denied_access"] == 0


class TestAddDecisions:
    def test_recommendation_counts(self):
        m = Monitoring()
        m.add_decisions([_decision("approve"), _decision("approve"),
                         _decision("review")])
        s = m.summary()
        assert s["recommendations"]["approve"] == 2
        assert s["recommendations"]["review"] == 1

    def test_overrides_counted(self):
        m = Monitoring()
        m.add_decisions([_decision("approve", override=True), _decision("approve")])
        assert m.summary()["specialist_overrides"] == 1

    def test_no_override(self):
        m = Monitoring()
        m.add_decisions([_decision("approve")])
        assert m.summary()["specialist_overrides"] == 0


class TestStatesOveralls:
    def test_states(self):
        m = Monitoring()
        m.add_states(["delivered", "delivered", "rejected"])
        assert m.summary()["states"]["delivered"] == 2
        assert m.summary()["states"]["rejected"] == 1

    def test_overalls(self):
        m = Monitoring()
        m.add_overalls(["GREEN", "GREEN", "RED", "UNKNOWN"])
        s = m.summary()
        assert s["overall_indicators"]["GREEN"] == 2
        assert s["overall_indicators"]["RED"] == 1
        assert s["overall_indicators"]["UNKNOWN"] == 1


class TestAlerts:
    def test_clean_no_alerts(self):
        m = Monitoring()
        m.add_overalls(["GREEN", "GREEN"])
        assert m.alerts() == []

    def test_denied_warn(self):
        m = _rec(AUDIT)  # فيها DENIED
        alerts = m.alerts()
        assert any(a["level"] == "warn" and "وصول" in a["message"] for a in alerts)

    def test_override_critical(self):
        m = Monitoring()
        m.add_decisions([_decision("approve", override=True)])
        alerts = m.alerts()
        assert any(a["level"] == "critical" and "تجاوز" in a["message"] for a in alerts)

    def test_red_critical(self):
        m = Monitoring()
        m.add_overalls(["RED"])
        alerts = m.alerts()
        assert any(a["level"] == "critical" and "حمراء" in a["message"] for a in alerts)

    def test_unknown_warn(self):
        m = Monitoring()
        m.add_overalls(["UNKNOWN"])
        alerts = m.alerts()
        assert any(a["level"] == "warn" and "ناقصة" in a["message"] for a in alerts)

    def test_alerts_in_summary(self):
        m = Monitoring()
        m.add_overalls(["RED"])
        assert len(m.summary()["alerts"]) >= 1


class TestMarkdown:
    def test_has_sections(self):
        m = Monitoring()
        m.add_audit(AUDIT)
        m.add_overalls(["GREEN", "RED"])
        md = m.to_markdown()
        assert "لوحة المراقبة التشغيلية" in md
        assert "العمليات حسب النوع" in md
        assert "التنبيهات" in md

    def test_clean_shows_green_line(self):
        m = Monitoring()
        md = m.to_markdown()
        assert "لا تنبيهات" in md

    def test_alert_icons(self):
        m = Monitoring()
        m.add_overalls(["RED"])
        md = m.to_markdown()
        assert "🔴" in md


class TestAggregation:
    def test_combined_summary(self):
        m = Monitoring()
        m.add_audit(AUDIT)
        m.add_decisions([_decision("approve", override=True)])
        m.add_states(["delivered"])
        m.add_overalls(["GREEN"])
        s = m.summary()
        assert s["total_actions"] == 3
        assert s["specialist_overrides"] == 1
        assert s["states"]["delivered"] == 1
        assert s["overall_indicators"]["GREEN"] == 1
