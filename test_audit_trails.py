"""
ProtonAI - Test Enterprise Audit Trails
اختبارات التدقيق المؤسسي (ربط الأدوار + فصل مهام القراءة + تصدير + سلامة)
"""

import json
import csv
import pytest
from audit_trails import EnterpriseAuditTrail, _CSV_FIELDS
from access_control import User, Role, Permission, PermissionDeniedError
from audit import AuditTrail
from access_control import AccessControl


def _u(role, uid=None):
    return User(uid or f"id_{role}", role)


@pytest.fixture
def ea():
    return EnterpriseAuditTrail()


class TestLogAction:
    def test_links_user_and_role(self, ea):
        rec = ea.log_action(_u(Role.PHYSICIAN), "sign", "plan_1")
        assert rec["user_id"] == "id_physician"
        assert rec["role"] == "physician"
        assert rec["action"] == "sign"
        assert rec["outcome"] == "SUCCESS"

    def test_seq_increments(self, ea):
        ea.log_action(_u(Role.ADMIN), "a")
        ea.log_action(_u(Role.ADMIN), "b")
        assert ea.records[0]["seq"] == 0
        assert ea.records[1]["seq"] == 1
        assert ea.count == 2

    def test_details_merged_with_user(self, ea):
        rec = ea.log_action(_u(Role.ADMIN), "deliver", details={"plan": "p1"})
        assert rec["details"]["plan"] == "p1"
        assert rec["details"]["user_id"] == "id_admin"
        assert rec["details"]["role"] == "admin"

    def test_timestamp_present(self, ea):
        rec = ea.log_action(_u(Role.ADMIN), "a")
        assert rec["timestamp"]

    def test_log_denied_outcome(self, ea):
        rec = ea.log_denied(_u(Role.VIEWER), "deliver")
        assert rec["outcome"] == "DENIED"


class TestSeparationOnRead:
    def _seed(self, ea):
        ea.log_action(_u(Role.ADMIN), "deliver", "p1")
        ea.log_action(_u(Role.PHYSICIAN), "sign", "p1")
        return ea

    def test_auditor_can_view(self, ea):
        self._seed(ea)
        events = ea.view_events(_u(Role.AUDITOR))
        assert len(events) == 2

    def test_admin_cannot_view(self, ea):
        self._seed(ea)
        with pytest.raises(PermissionDeniedError):
            ea.view_events(_u(Role.ADMIN))

    def test_viewer_cannot_view(self, ea):
        self._seed(ea)
        with pytest.raises(PermissionDeniedError):
            ea.view_events(_u(Role.VIEWER))

    def test_physician_cannot_view(self, ea):
        self._seed(ea)
        with pytest.raises(PermissionDeniedError):
            ea.view_events(_u(Role.PHYSICIAN))

    def test_view_returns_copies(self, ea):
        self._seed(ea)
        events = ea.view_events(_u(Role.AUDITOR))
        events[0]["action"] = "tampered"
        assert ea.records[0]["action"] == "deliver"  # الأصل سليم


class TestExport:
    def _seed(self, ea):
        ea.log_action(_u(Role.ADMIN), "deliver", "p1", details={"x": 1})
        ea.log_action(_u(Role.PHYSICIAN), "sign", "p1")
        return ea

    def test_jsonl_denied_for_admin(self, ea, tmp_path):
        self._seed(ea)
        with pytest.raises(PermissionDeniedError):
            ea.export_jsonl(_u(Role.ADMIN), tmp_path / "a.jsonl")

    def test_jsonl_allowed_for_auditor(self, ea, tmp_path):
        self._seed(ea)
        p = ea.export_jsonl(_u(Role.AUDITOR), tmp_path / "a.jsonl")
        assert p.exists()
        lines = p.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["action"] == "deliver"
        assert first["role"] == "admin"

    def test_csv_denied_for_physician(self, ea, tmp_path):
        self._seed(ea)
        with pytest.raises(PermissionDeniedError):
            ea.export_csv(_u(Role.PHYSICIAN), tmp_path / "a.csv")

    def test_csv_allowed_for_auditor(self, ea, tmp_path):
        self._seed(ea)
        p = ea.export_csv(_u(Role.AUDITOR), tmp_path / "a.csv")
        assert p.exists()
        with open(p, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert list(rows[0].keys()) == _CSV_FIELDS
        assert rows[0]["action"] == "deliver"
        # details مسلسل كـ JSON string
        assert json.loads(rows[0]["details"])["x"] == 1

    def test_export_creates_parent_dir(self, ea, tmp_path):
        self._seed(ea)
        p = ea.export_jsonl(_u(Role.AUDITOR), tmp_path / "sub" / "deep" / "a.jsonl")
        assert p.exists()


class TestVerify:
    def test_verify_true_after_logs(self, ea):
        ea.log_action(_u(Role.ADMIN), "a")
        ea.log_action(_u(Role.ADMIN), "b")
        assert ea.verify() is True

    def test_verify_empty_true(self, ea):
        assert ea.verify() is True


class TestInjection:
    def test_defaults_built(self, ea):
        assert isinstance(ea.audit, AuditTrail)
        assert isinstance(ea.access, AccessControl)

    def test_uses_injected(self):
        a, c = AuditTrail(), AccessControl()
        ea = EnterpriseAuditTrail(audit=a, access=c)
        assert ea.audit is a
        assert ea.access is c


class TestCount:
    def test_zero_initial(self, ea):
        assert ea.count == 0

    def test_increments(self, ea):
        ea.log_action(_u(Role.ADMIN), "a")
        assert ea.count == 1
