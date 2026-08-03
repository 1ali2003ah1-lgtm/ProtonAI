"""
ProtonAI - Test Stage-7 Enterprise Demo
اختبارات المايسترو المؤسسي (RBAC + gates + audit + monitoring + FHIR)
"""

import json
import pytest
from run_enterprise_demo import run_enterprise_demo


@pytest.fixture
def res():
    return run_enterprise_demo()


class TestCoreKeys:
    def test_all_keys(self, res):
        for k in ["users", "audit_count", "denied_count", "gate", "fhir",
                  "monitoring", "monitoring_markdown"]:
            assert k in res

    def test_users_roles(self, res):
        assert res["users"]["admin1"] == "admin"
        assert res["users"]["aud1"] == "auditor"
        assert res["users"]["view1"] == "viewer"


class TestDeniedLogged:
    def test_denied_at_least_two(self, res):
        # viewer deliver + admin view_audit
        assert res["denied_count"] >= 2

    def test_monitoring_sees_denied(self, res):
        assert res["monitoring"]["denied_access"] >= 2

    def test_denied_alert_present(self, res):
        assert any("وصول" in a["message"] for a in res["monitoring"]["alerts"])


class TestGate:
    def test_approved_by_second_admin(self, res):
        assert res["gate"]["status"] == "approved"
        assert res["gate"]["decided_by"] == "admin2"

    def test_separation_blocked(self, res):
        assert res["gate"]["separation_blocked"] is True


class TestFHIR:
    def test_two_acks(self, res):
        assert set(res["fhir"]["acks"].keys()) == {"pacs", "his"}

    def test_bundle_has_entries(self, res):
        assert res["fhir"]["entries"] >= 4  # Patient+Imaging+Request+Observations


class TestMonitoring:
    def test_override_alert(self, res):
        assert any(a["level"] == "critical" and "تجاوز" in a["message"]
                   for a in res["monitoring"]["alerts"])

    def test_red_alert(self, res):
        assert any(a["level"] == "critical" and "حمراء" in a["message"]
                   for a in res["monitoring"]["alerts"])

    def test_overrides_counted(self, res):
        assert res["monitoring"]["specialist_overrides"] == 1

    def test_markdown_has_sections(self, res):
        md = res["monitoring_markdown"]
        assert "لوحة المراقبة التشغيلية" in md
        assert "التنبيهات" in md
        assert "🔴" in md


class TestSave:
    def test_saves_files(self, tmp_path):
        out = tmp_path / "ent"
        run_enterprise_demo(output_dir=out)
        assert (out / "enterprise_monitoring.md").exists()
        assert (out / "enterprise_audit.jsonl").exists()
        assert (out / "fhir_bundle.json").exists()

    def test_fhir_bundle_valid_json(self, tmp_path):
        out = tmp_path / "ent"
        run_enterprise_demo(output_dir=out)
        b = json.loads((out / "fhir_bundle.json").read_text(encoding="utf-8"))
        assert b["resourceType"] == "Bundle"

    def test_audit_jsonl_has_denied(self, tmp_path):
        out = tmp_path / "ent"
        run_enterprise_demo(output_dir=out)
        txt = (out / "enterprise_audit.jsonl").read_text(encoding="utf-8")
        assert "DENIED" in txt
