"""
ProtonAI - Test Physics Review Loop
اختبارات حلقة مراجعة الفيزيائي الطبي (القواعد الفيزيائية + لفّ physician_review)
"""

import pytest
from physics_review import (
    PhysicsReviewLoop, DEFAULT_GAMMA_THRESHOLD,
    DEFAULT_COVERAGE_DROP_THRESHOLD, DEFAULT_RBE_RANGE,
)
from physician_review import PhysicianReviewLoop
from audit import AuditTrail


@pytest.fixture
def pr():
    return PhysicsReviewLoop()


class TestNoFlag:
    def test_all_ok_returns_none(self, pr):
        assert pr.flag_physics("s1", 70.0, gamma_pass_rate=0.98,
                               coverage_drop=0.0, range_in_target=True,
                               rbe=1.1) is None
        assert pr.review.requests == []

    def test_no_inputs_returns_none(self, pr):
        # بلا مقاييس → لا قواعد تُفحص → None
        assert pr.flag_physics("s1", 70.0) is None
        assert pr.review.requests == []


class TestGammaFail:
    def test_below_threshold_flags(self, pr):
        req = pr.flag_physics("s1", 70.0, gamma_pass_rate=0.7)
        assert req is not None
        assert req.record["physics_reasons"] == ["gamma_fail"]
        assert req.record["gamma_pass_rate"] == 0.7

    def test_at_threshold_no_flag(self, pr):
        assert pr.flag_physics("s1", 70.0,
                               gamma_pass_rate=DEFAULT_GAMMA_THRESHOLD) is None

    def test_above_threshold_no_flag(self, pr):
        assert pr.flag_physics("s1", 70.0, gamma_pass_rate=0.99) is None


class TestCoverageDrop:
    def test_above_threshold_flags(self, pr):
        req = pr.flag_physics("s1", 70.0, coverage_drop=0.3)
        assert req.record["physics_reasons"] == ["coverage_drop"]

    def test_at_threshold_no_flag(self, pr):
        assert pr.flag_physics("s1", 70.0,
                               coverage_drop=DEFAULT_COVERAGE_DROP_THRESHOLD) is None

    def test_below_threshold_no_flag(self, pr):
        assert pr.flag_physics("s1", 70.0, coverage_drop=0.05) is None


class TestRangeOut:
    def test_false_flags(self, pr):
        req = pr.flag_physics("s1", 70.0, range_in_target=False)
        assert req.record["physics_reasons"] == ["range_out"]

    def test_true_no_flag(self, pr):
        assert pr.flag_physics("s1", 70.0, range_in_target=True) is None


class TestRBEOut:
    def test_above_range_flags(self, pr):
        req = pr.flag_physics("s1", 70.0, rbe=1.5)
        assert req.record["physics_reasons"] == ["rbe_out"]

    def test_below_range_flags(self, pr):
        req = pr.flag_physics("s1", 70.0, rbe=0.8)
        assert req.record["physics_reasons"] == ["rbe_out"]

    def test_in_range_no_flag(self, pr):
        lo, hi = DEFAULT_RBE_RANGE
        assert pr.flag_physics("s1", 70.0, rbe=lo) is None
        assert pr.flag_physics("s1", 70.0, rbe=hi) is None
        assert pr.flag_physics("s1", 70.0, rbe=(lo + hi) / 2) is None


class TestMultipleReasons:
    def test_all_four_collected(self, pr):
        req = pr.flag_physics("s1", 70.0, gamma_pass_rate=0.5,
                              coverage_drop=0.5, range_in_target=False, rbe=2.0)
        assert req.record["physics_reasons"] == [
            "gamma_fail", "coverage_drop", "range_out", "rbe_out"]

    def test_details_stored(self, pr):
        req = pr.flag_physics("s1", 70.0, gamma_pass_rate=0.5,
                              coverage_drop=0.5, range_in_target=False, rbe=2.0,
                              record={"patient": "X"})
        assert req.record["patient"] == "X"  # الأصلي محفوظ
        assert req.record["gamma_pass_rate"] == 0.5
        assert req.record["coverage_drop"] == 0.5
        assert req.record["range_in_target"] is False
        assert req.record["rbe"] == 2.0

    def test_out_of_protocol_in_inner_reasons(self, pr):
        # الحلقة الداخلية تسجّل out_of_protocol كـ trigger
        req = pr.flag_physics("s1", 70.0, gamma_pass_rate=0.5)
        assert "out_of_protocol" in req.reasons


class TestDecision:
    def _flagged(self, pr):
        return pr.flag_physics("s1", 70.0, gamma_pass_rate=0.5)

    def test_submit_approve(self, pr):
        req = self._flagged(pr)
        upd = pr.submit_decision(req.request_id, "phys_ahmed", "approve", notes="ok")
        assert upd.decision["decision"] == "approve"
        assert upd.decision["reviewer_id"] == "phys_ahmed"

    def test_submit_reject_and_flag(self, pr):
        req = self._flagged(pr)
        pr.submit_decision(req.request_id, "p1", "reject")
        assert pr.review.requests[0].decision["decision"] == "reject"
        pr2 = PhysicsReviewLoop()
        req2 = pr2.flag_physics("s2", 70.0, rbe=2.0)
        pr2.submit_decision(req2.request_id, "p1", "flag")
        assert pr2.review.requests[0].decision["decision"] == "flag"

    def test_double_submit_raises(self, pr):
        req = self._flagged(pr)
        pr.submit_decision(req.request_id, "p1", "approve")
        with pytest.raises(ValueError):
            pr.submit_decision(req.request_id, "p1", "reject")


class TestQueries:
    def _setup(self):
        pr = PhysicsReviewLoop()
        r1 = pr.flag_physics("s1", 70.0, gamma_pass_rate=0.5)
        r2 = pr.flag_physics("s2", 70.0, coverage_drop=0.4, rbe=1.5)
        pr.submit_decision(r1.request_id, "p1", "approve")
        return pr

    def test_pending_completed(self):
        pr = self._setup()
        assert len(pr.pending()) == 1
        assert len(pr.completed()) == 1

    def test_physics_stats_counts(self):
        pr = self._setup()
        s = pr.physics_stats()
        assert s["total_flagged"] == 2
        assert s["pending_count"] == 1
        assert s["completed_count"] == 1
        assert s["by_decision"]["approve"] == 1
        assert s["by_physics_reason"]["gamma_fail"] == 1
        assert s["by_physics_reason"]["coverage_drop"] == 1
        assert s["by_physics_reason"]["rbe_out"] == 1
        assert "range_out" not in s["by_physics_reason"]

    def test_physics_stats_empty(self, pr):
        s = pr.physics_stats()
        assert s["total_flagged"] == 0
        assert s["by_physics_reason"] == {}


class TestAudit:
    def test_flag_logged_via_inner(self, tmp_path):
        audit = AuditTrail()
        pr = PhysicsReviewLoop(audit=audit)
        req = pr.flag_physics("s1", 70.0, gamma_pass_rate=0.5)
        pr.submit_decision(req.request_id, "p1", "approve")
        actions = [e.action for e in audit.events]
        assert "flag" in actions
        assert "decision_approve" in actions
        assert audit.verify_chain() is True

    def test_injected_review_keeps_its_audit(self, tmp_path):
        audit = AuditTrail()
        inner = PhysicianReviewLoop(audit=audit)
        pr = PhysicsReviewLoop(review_loop=inner)
        req = pr.flag_physics("s1", 70.0, rbe=2.0)
        assert req is not None
        actions = [e.action for e in audit.events]
        assert "flag" in actions


class TestPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        pr = PhysicsReviewLoop()
        req = pr.flag_physics("s1", 70.0, gamma_pass_rate=0.5,
                              record={"note": "hi"})
        pr.submit_decision(req.request_id, "p1", "reject")
        p = tmp_path / "phys_review.json"
        pr.save(p)

        pr2 = PhysicsReviewLoop()
        pr2.load(p)
        assert len(pr2.review.requests) == 1
        assert pr2.review.requests[0].record["physics_reasons"] == ["gamma_fail"]
        assert pr2.review.requests[0].record["note"] == "hi"
        assert pr2.review.requests[0].decision["decision"] == "reject"


class TestInjection:
    def test_default_builds_review(self, pr):
        assert isinstance(pr.review, PhysicianReviewLoop)

    def test_uses_injected_review(self):
        inner = PhysicianReviewLoop()
        pr = PhysicsReviewLoop(review_loop=inner)
        assert pr.review is inner


class TestGuards:
    def test_invalid_gamma_threshold(self):
        with pytest.raises(ValueError):
            PhysicsReviewLoop(gamma_threshold=1.5)
        with pytest.raises(ValueError):
            PhysicsReviewLoop(gamma_threshold=-0.1)

    def test_invalid_coverage_drop_threshold(self):
        with pytest.raises(ValueError):
            PhysicsReviewLoop(coverage_drop_threshold=-0.1)

    def test_invalid_rbe_range(self):
        with pytest.raises(ValueError):
            PhysicsReviewLoop(rbe_range=(1.2, 1.0))  # low > high
        with pytest.raises(ValueError):
            PhysicsReviewLoop(rbe_range=(0.0, 1.2))  # zero
        with pytest.raises(ValueError):
            PhysicsReviewLoop(rbe_range=(-1.0, 1.2))  # negative
