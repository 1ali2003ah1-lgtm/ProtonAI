"""
ProtonAI - Test Gov Audit Log
"""

import json
from gov_audit_log import AuditLog, GENESIS


class TestLog:
    def test_append_and_seq(self, tmp_path):
        a = AuditLog(tmp_path / "a.log")
        e1 = a.log("dr", "approve", "plan-1")
        e2 = a.log("phys", "review", "plan-1")
        assert e1["seq"] == 1 and e2["seq"] == 2
        assert len(a.entries()) == 2

    def test_chain_linkage(self, tmp_path):
        a = AuditLog(tmp_path / "a.log")
        e1 = a.log("x", "y", "z")
        e2 = a.log("x", "y", "z")
        assert e1["prev_hash"] == GENESIS
        assert e2["prev_hash"] == e1["hash"]

    def test_verify_intact(self, tmp_path):
        a = AuditLog(tmp_path / "a.log")
        a.log("a", "approve", "x")
        a.log("b", "reject", "y")
        assert a.verify() is True

    def test_verify_detects_tamper(self, tmp_path):
        p = tmp_path / "a.log"
        a = AuditLog(p)
        a.log("a", "approve", "x")
        a.log("b", "reject", "y")
        lines = p.read_text(encoding="utf-8").splitlines()
        e = json.loads(lines[0])
        e["action"] = "HACKED"  # تلاعب
        lines[0] = json.dumps(e)
        p.write_text("\n".join(lines), encoding="utf-8")
        assert a.verify() is False

    def test_empty_verify(self, tmp_path):
        assert AuditLog(tmp_path / "e.log").verify() is True
