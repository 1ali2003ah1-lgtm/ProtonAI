"""
ProtonAI - Test Physician Review Loop
اختبارات حلقة مراجعة الطبيب
"""

import json
import pytest
from physician_review import (
    PhysicianReviewLoop, ReviewRequest, ReviewStatus, ReviewDecision, _to_decision,
)
from audit import AuditTrail


class TestToDecision:
    def test_from_string(self):
        assert _to_decision("approve") == ReviewDecision.APPROVE
        assert _to_decision("REJECT") == ReviewDecision.REJECT

    def test_from_enum(self):
        assert _to_decision(ReviewDecision.FLAG) == ReviewDecision.FLAG

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _to_decision("maybe")


class TestFlagging:
    def test_no_flag_when_all_ok(self):
        loop = PhysicianReviewLoop()
        assert loop.flag_for_review("s1", 70.0, confidence=0.95,
                                    ci_width=1.0, abs_error=0.5) is None
        assert loop.requests == []

    def test_flag_low_confidence(self):
        loop = PhysicianReviewLoop(low_confidence_threshold=0.7)
        req = loop.flag_for_review("s1", "M", confidence=0.5)
        assert req is not None
        assert any("low_confidence" in r for r in req.reasons)

    def test_flag_high_uncertainty(self):
        loop = PhysicianReviewLoop(high_ci_width=5.0)
        req = loop.flag_for_review("s1", 70.0, ci_width=8.0)
        assert req is not None
        assert any("high_uncertainty" in r for r in req.reasons)

    def test_ci_width_ignored_when_threshold_none(self):
        loop = PhysicianReviewLoop(high_ci_width=None)
        assert loop.flag_for_review("s1", 70.0, ci_width=999.0) is None

    def test_flag_clinical_error(self):
        loop = PhysicianReviewLoop(clinical_tolerance=3.0)
        req = loop.flag_for_review("s1", 70.0, true_value=80.0, abs_error=10.0)
        assert req is not None
        assert any("clinical_error" in r for r in req.reasons)

    def test_flag_out_of_protocol(self):
        loop = PhysicianReviewLoop()
        req = loop.flag_for_review("s1", 70.0, out_of_protocol=True)
        assert req is not None
        assert "out_of_protocol" in req.reasons

    def test_multiple_reasons_collected(self):
        loop = PhysicianReviewLoop(low_confidence_threshold=0.7,
                                   high_ci_width=5.0, clinical_tolerance=3.0)
        req = loop.flag_for_review("s1", 70.0, confidence=0.4,
                                   ci_width=9.0, abs_error=12.0, out_of_protocol=True)
        assert len(req.reasons) == 4

    def test_request_fields_stored(self):
        loop = PhysicianReviewLoop()
        req = loop.flag_for_review("s1", 70.0, true_value=80.0,
                                   abs_error=10.0, record={"age": 50})
        assert req.sample_id == "s1"
        assert req.prediction == 70.0
        assert req.true_value == 80.0
        assert req.record == {"age": 50}
        assert req.status == ReviewStatus.PENDING
        assert len(req.request_id) == 12


class TestDecision:
    def _loop_with_one(self):
        loop = PhysicianReviewLoop()
        req = loop.flag_for_review("s1", 70.0, abs_error=10.0)
        return loop, req

    def test_submit_approve(self):
        loop, req = self._loop_with_one()
        updated = loop.submit_decision(req.request_id, "dr_ahmed", "approve", notes="ok")
        assert updated.status == ReviewStatus.REVIEWED
        assert updated.decision["decision"] == "approve"
        assert updated.decision["reviewer_id"] == "dr_ahmed"
        assert updated.decision["notes"] == "ok"

    def test_submit_reject_and_flag(self):
        loop, req = self._loop_with_one()
        loop.submit_decision(req.request_id, "dr1", ReviewDecision.REJECT)
        assert loop.requests[0].decision["decision"] == "reject"
        loop2, req2 = self._loop_with_one()
        loop2.submit_decision(req2.request_id, "dr1", "flag")
        assert loop2.requests[0].decision["decision"] == "flag"

    def test_double_submit_raises(self):
        loop, req = self._loop_with_one()
        loop.submit_decision(req.request_id, "dr1", "approve")
        with pytest.raises(ValueError):
            loop.submit_decision(req.request_id, "dr1", "reject")

    def test_unknown_request_raises(self):
        loop = PhysicianReviewLoop()
        with pytest.raises(ValueError):
            loop.submit_decision("nope", "dr1", "approve")

    def test_invalid_decision_raises(self):
        loop, req = self._loop_with_one()
        with pytest.raises(ValueError):
            loop.submit_decision(req.request_id, "dr1", "maybe")


class TestQueries:
    def _loop(self):
        loop = PhysicianReviewLoop(low_confidence_threshold=0.7, clinical_tolerance=3.0)
        r1 = loop.flag_for_review("s1", "M", confidence=0.4)
        r2 = loop.flag_for_review("s2", 70.0, abs_error=10.0)
        loop.flag_for_review("s3", 70.0, abs_error=10.0, out_of_protocol=True)
        loop.submit_decision(r1.request_id, "dr1", "approve")
        loop.submit_decision(r2.request_id, "dr1", "reject")
        return loop

    def test_pending_completed(self):
        loop = self._loop()
        assert len(loop.pending()) == 1
        assert len(loop.completed()) == 2

    def test_stats_keys(self):
        loop = self._loop()
        s = loop.stats()
        assert s["total_flagged"] == 3
        assert s["pending_count"] == 1
        assert s["completed_count"] == 2
        assert s["by_decision"]["approve"] == 1
        assert s["by_decision"]["reject"] == 1
        assert s["by_reason"]["low_confidence"] == 1
        assert s["by_reason"]["clinical_error"] == 2
        assert s["by_reason"]["out_of_protocol"] == 1


class TestAudit:
    def test_flag_and_decision_logged(self):
        audit = AuditTrail()
        loop = PhysicianReviewLoop(audit=audit, clinical_tolerance=3.0)
        req = loop.flag_for_review("s1", 70.0, abs_error=10.0)
        loop.submit_decision(req.request_id, "dr1", "approve")
        actions = [e.action for e in audit.events]
        assert "flag" in actions
        assert "decision_approve" in actions
        assert audit.verify_chain() is True

    def test_no_audit_no_crash(self):
        loop = PhysicianReviewLoop(audit=None)
        req = loop.flag_for_review("s1", 70.0, abs_error=10.0)
        loop.submit_decision(req.request_id, "dr1", "approve")
        assert req.status == ReviewStatus.REVIEWED


class TestPersistence:
    def test_save_load(self, tmp_path):
        loop = PhysicianReviewLoop(clinical_tolerance=3.0)
        req = loop.flag_for_review("s1", 70.0, abs_error=10.0, record={"age": 50})
        loop.submit_decision(req.request_id, "dr1", "reject", notes="wrong")
        p = tmp_path / "review.json"
        loop.save(p)

        loop2 = PhysicianReviewLoop()
        loop2.load(p)
        assert len(loop2.requests) == 1
        assert loop2.requests[0].status == ReviewStatus.REVIEWED
        assert loop2.requests[0].decision["decision"] == "reject"
        assert loop2.requests[0].record == {"age": 50}

    def test_saved_is_valid_json(self, tmp_path):
        loop = PhysicianReviewLoop()
        loop.flag_for_review("s1", 70.0, out_of_protocol=True)
        p = tmp_path / "r.json"
        loop.save(p)
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        assert data[0]["status"] == "pending"

    def test_load_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            PhysicianReviewLoop().load(tmp_path / "nope.json")


class TestGuards:
    def test_invalid_low_conf(self):
        with pytest.raises(ValueError):
            PhysicianReviewLoop(low_confidence_threshold=1.5)

    def test_invalid_tolerance(self):
        with pytest.raises(ValueError):
            PhysicianReviewLoop(clinical_tolerance=0)
