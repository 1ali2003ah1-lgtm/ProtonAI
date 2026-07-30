"""
ProtonAI - Test Audit Trail
اختبارات سجل التدقيق
"""

import json
import pytest
from audit import AuditTrail, AuditEvent, AuditOutcome, GENESIS_HASH, _compute_hash


class TestLogging:
    def test_log_adds_event(self):
        t = AuditTrail()
        e = t.log("system", "train", "model_v1", AuditOutcome.SUCCESS)
        assert len(t.events) == 1
        assert e.action == "train"
        assert e.outcome == AuditOutcome.SUCCESS

    def test_event_has_id_and_hash(self):
        t = AuditTrail()
        e = t.log("system", "ingest", "file.csv")
        assert e.event_id  # غير فارغ
        assert len(e.hash) == 64

    def test_details_stored(self):
        t = AuditTrail()
        e = t.log("system", "split", "data", details={"train": 70})
        assert e.details["train"] == 70


class TestChainIntegrity:
    def test_genesis_first_event(self):
        t = AuditTrail()
        e = t.log("system", "init", "platform")
        assert e.previous_hash == GENESIS_HASH

    def test_chain_links_correctly(self):
        t = AuditTrail()
        e1 = t.log("system", "a", "x")
        e2 = t.log("system", "b", "y")
        assert e2.previous_hash == e1.hash

    def test_verify_chain_valid(self):
        t = AuditTrail()
        t.log("system", "a", "x")
        t.log("system", "b", "y")
        t.log("system", "c", "z")
        assert t.verify_chain() is True

    def test_verify_empty_chain_valid(self):
        assert AuditTrail().verify_chain() is True

    def test_tampered_content_detected(self):
        t = AuditTrail()
        t.log("system", "a", "x")
        t.log("system", "b", "y")
        # تلاعب بمحتوى الحدث الأول
        t.events[0].action = "TAMPERED"
        assert t.verify_chain() is False

    def test_broken_link_detected(self):
        t = AuditTrail()
        t.log("system", "a", "x")
        t.log("system", "b", "y")
        # كسر الربط بالحدث الثاني
        t.events[1].previous_hash = "wrong_hash_value"
        assert t.verify_chain() is False


class TestFilter:
    def _trail(self):
        t = AuditTrail()
        t.log("alice", "train", "m1", AuditOutcome.SUCCESS)
        t.log("alice", "validate", "d1", AuditOutcome.FAILURE)
        t.log("bob", "train", "m2", AuditOutcome.SUCCESS)
        return t

    def test_filter_by_action(self):
        res = self._trail().filter_by(action="train")
        assert len(res) == 2

    def test_filter_by_outcome(self):
        res = self._trail().filter_by(outcome=AuditOutcome.FAILURE)
        assert len(res) == 1
        assert res[0].action == "validate"

    def test_filter_by_actor(self):
        res = self._trail().filter_by(actor="bob")
        assert len(res) == 1

    def test_filter_combined(self):
        res = self._trail().filter_by(actor="alice", action="train")
        assert len(res) == 1

    def test_filter_no_match(self):
        assert self._trail().filter_by(actor="nobody") == []


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        t = AuditTrail()
        t.log("system", "train", "m1", AuditOutcome.SUCCESS, {"lr": 0.01})
        t.log("system", "eval", "m1", AuditOutcome.INFO)
        path = tmp_path / "audit.json"
        t.save(path)

        t2 = AuditTrail()
        t2.load(path)
        assert len(t2.events) == 2
        assert t2.events[0].action == "train"
        assert t2.events[0].details["lr"] == 0.01
        assert t2.verify_chain() is True  # السلسلة سليمة بعد الحفظ

    def test_load_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            AuditTrail().load(tmp_path / "nope.json")

    def test_saved_file_is_valid_json(self, tmp_path):
        t = AuditTrail()
        t.log("system", "a", "x")
        path = tmp_path / "a.json"
        t.save(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert data[0]["outcome"] == "info"


class TestSummary:
    def test_summary_keys(self):
        t = AuditTrail()
        t.log("system", "a", "x", AuditOutcome.SUCCESS)
        t.log("system", "b", "y", AuditOutcome.SUCCESS)
        t.log("system", "c", "z", AuditOutcome.FAILURE)
        s = t.summary()
        assert s["total_events"] == 3
        assert s["chain_valid"] is True
        assert s["by_outcome"]["success"] == 2
        assert s["by_outcome"]["failure"] == 1
