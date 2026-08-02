"""
ProtonAI - Test Plan State Machine
اختبارات سير العمل المحروس (مسار سعيد + كل حرس + نهائي + history + context)
"""

import pytest
from plan_state_machine import (
    PlanStateMachine, PlanState, GuardFailedError, TERMINAL_STATES, build_context,
)
from quality_indicators import QualityIndicators
from decision_model import DecisionModel


S = PlanState


def _ctx(**kw):
    """context يدوي سريع"""
    return build_context(**kw)


def _good_decision(signed_phys=True, signed_phy=True):
    """قرار أخضر موقّع (can_deliver=True)"""
    ev = QualityIndicators().evaluate({
        "gamma_pass_rate": 0.98, "range_in_target": True, "coverage_drop": 0.0,
        "benchmark_passed": True, "completeness": 1.0, "reviews_signed": True})
    return DecisionModel().recommend(ev, physician_signed=signed_phys,
                                     physics_signed=signed_phy)


@pytest.fixture
def sm():
    return PlanStateMachine()


class TestInit:
    def test_initial_draft(self, sm):
        assert sm.state == S.DRAFT
        assert sm.is_terminal is False
        assert sm.history == []

    def test_custom_initial(self):
        sm = PlanStateMachine(S.READY)
        assert sm.state == S.READY


class TestHappyPath:
    def test_full_path_to_delivered(self, sm):
        sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))
        sm.transition(S.PHYSICIAN_REVIEW, _ctx(physics_signed=True, overall_status="GREEN"))
        sm.transition(S.READY, _ctx(physician_signed=True, can_deliver=True))
        sm.transition(S.DELIVERED, _ctx(specialist_decision="approve"))
        assert sm.state == S.DELIVERED
        assert sm.is_terminal is True
        assert len(sm.history) == 4


class TestDraftGuards:
    def test_to_physics_needs_physics(self, sm):
        with pytest.raises(GuardFailedError):
            sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=False))

    def test_to_physics_ok(self, sm):
        sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))
        assert sm.state == S.PHYSICS_REVIEW


class TestPhysicsGuards:
    def _at_physics(self, sm):
        sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))

    def test_to_physician_needs_signature(self, sm):
        self._at_physics(sm)
        with pytest.raises(GuardFailedError):
            sm.transition(S.PHYSICIAN_REVIEW,
                          _ctx(physics_signed=False, overall_status="GREEN"))

    def test_to_physician_blocked_by_red(self, sm):
        self._at_physics(sm)
        with pytest.raises(GuardFailedError):
            sm.transition(S.PHYSICIAN_REVIEW,
                          _ctx(physics_signed=True, overall_status="RED"))

    def test_to_physician_blocked_by_unknown(self, sm):
        self._at_physics(sm)
        with pytest.raises(GuardFailedError):
            sm.transition(S.PHYSICIAN_REVIEW,
                          _ctx(physics_signed=True, overall_status="UNKNOWN"))

    def test_to_physician_ok(self, sm):
        self._at_physics(sm)
        sm.transition(S.PHYSICIAN_REVIEW,
                      _ctx(physics_signed=True, overall_status="GREEN"))
        assert sm.state == S.PHYSICIAN_REVIEW

    def test_back_to_draft_always(self, sm):
        self._at_physics(sm)
        sm.transition(S.DRAFT, _ctx())  # بلا شروط
        assert sm.state == S.DRAFT


class TestPhysicianGuards:
    def _at_physician(self, sm):
        sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))
        sm.transition(S.PHYSICIAN_REVIEW,
                      _ctx(physics_signed=True, overall_status="GREEN"))

    def test_to_ready_needs_physician_signature(self, sm):
        self._at_physician(sm)
        with pytest.raises(GuardFailedError):
            sm.transition(S.READY, _ctx(physician_signed=False, can_deliver=True))

    def test_to_ready_needs_can_deliver(self, sm):
        self._at_physician(sm)
        with pytest.raises(GuardFailedError):
            sm.transition(S.READY, _ctx(physician_signed=True, can_deliver=False))

    def test_to_ready_ok(self, sm):
        self._at_physician(sm)
        sm.transition(S.READY, _ctx(physician_signed=True, can_deliver=True))
        assert sm.state == S.READY

    def test_back_to_physics_or_draft(self, sm):
        self._at_physician(sm)
        sm.transition(S.PHYSICS_REVIEW, _ctx())
        assert sm.state == S.PHYSICS_REVIEW


class TestReadyGuards:
    def _at_ready(self, sm):
        sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))
        sm.transition(S.PHYSICIAN_REVIEW,
                      _ctx(physics_signed=True, overall_status="GREEN"))
        sm.transition(S.READY, _ctx(physician_signed=True, can_deliver=True))

    def test_deliver_needs_approve(self, sm):
        self._at_ready(sm)
        with pytest.raises(GuardFailedError):
            sm.transition(S.DELIVERED, _ctx(specialist_decision="defer"))

    def test_deliver_ok(self, sm):
        self._at_ready(sm)
        sm.transition(S.DELIVERED, _ctx(specialist_decision="approve"))
        assert sm.state == S.DELIVERED


class TestReject:
    def test_reject_from_draft(self, sm):
        sm.transition(S.REJECTED, _ctx(specialist_decision="reject"))
        assert sm.state == S.REJECTED

    def test_reject_from_physics(self, sm):
        sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))
        sm.transition(S.REJECTED, _ctx(specialist_decision="reject"))
        assert sm.state == S.REJECTED

    def test_reject_needs_reject_decision(self, sm):
        with pytest.raises(GuardFailedError):
            sm.transition(S.REJECTED, _ctx(specialist_decision="approve"))

    def test_reject_from_ready(self, sm):
        sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))
        sm.transition(S.PHYSICIAN_REVIEW,
                      _ctx(physics_signed=True, overall_status="GREEN"))
        sm.transition(S.READY, _ctx(physician_signed=True, can_deliver=True))
        sm.transition(S.REJECTED, _ctx(specialist_decision="reject"))
        assert sm.state == S.REJECTED


class TestTerminal:
    def test_no_exit_from_delivered(self, sm):
        sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))
        sm.transition(S.PHYSICIAN_REVIEW,
                      _ctx(physics_signed=True, overall_status="GREEN"))
        sm.transition(S.READY, _ctx(physician_signed=True, can_deliver=True))
        sm.transition(S.DELIVERED, _ctx(specialist_decision="approve"))
        with pytest.raises(ValueError):
            sm.transition(S.DRAFT, _ctx())

    def test_no_exit_from_rejected(self, sm):
        sm.transition(S.REJECTED, _ctx(specialist_decision="reject"))
        with pytest.raises(ValueError):
            sm.transition(S.DRAFT, _ctx())

    def test_terminal_set(self):
        assert S.DELIVERED in TERMINAL_STATES
        assert S.REJECTED in TERMINAL_STATES
        assert S.DRAFT not in TERMINAL_STATES


class TestNotAllowed:
    def test_draft_to_ready_illogical(self, sm):
        with pytest.raises(ValueError):
            sm.transition(S.READY, _ctx(physician_signed=True, can_deliver=True))

    def test_draft_to_delivered_illogical(self, sm):
        with pytest.raises(ValueError):
            sm.transition(S.DELIVERED, _ctx(specialist_decision="approve"))

    def test_physics_to_ready_illogical(self, sm):
        sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))
        with pytest.raises(ValueError):
            sm.transition(S.READY, _ctx(physician_signed=True, can_deliver=True))


class TestCanTransition:
    def test_true_when_guard_passes(self, sm):
        assert sm.can_transition(S.PHYSICS_REVIEW, _ctx(physics_available=True)) is True

    def test_false_when_guard_fails(self, sm):
        assert sm.can_transition(S.PHYSICS_REVIEW, _ctx(physics_available=False)) is False

    def test_false_when_illogical(self, sm):
        assert sm.can_transition(S.READY, _ctx()) is False

    def test_false_when_terminal(self, sm):
        sm.transition(S.REJECTED, _ctx(specialist_decision="reject"))
        assert sm.can_transition(S.DRAFT, _ctx()) is False

    def test_does_not_change_state(self, sm):
        sm.can_transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))
        assert sm.state == S.DRAFT  # لم يتغيّر


class TestAllowedTargets:
    def test_draft_targets(self, sm):
        assert sm.allowed_targets() == {S.PHYSICS_REVIEW, S.REJECTED}

    def test_ready_targets(self, sm):
        sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))
        sm.transition(S.PHYSICIAN_REVIEW,
                      _ctx(physics_signed=True, overall_status="GREEN"))
        sm.transition(S.READY, _ctx(physician_signed=True, can_deliver=True))
        assert sm.allowed_targets() == {S.DELIVERED, S.REJECTED}


class TestHistory:
    def test_records_each_transition(self, sm):
        sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=True))
        sm.transition(S.PHYSICIAN_REVIEW,
                      _ctx(physics_signed=True, overall_status="GREEN"))
        assert len(sm.history) == 2
        assert sm.history[0]["from"] == "draft"
        assert sm.history[0]["to"] == "physics_review"
        assert sm.history[1]["to"] == "physician_review"
        assert sm.history[0]["timestamp"]  # غير فارغ

    def test_failed_transition_not_recorded(self, sm):
        with pytest.raises(GuardFailedError):
            sm.transition(S.PHYSICS_REVIEW, _ctx(physics_available=False))
        assert sm.history == []


class TestBuildContext:
    def test_explicit_values(self):
        ctx = build_context(physics_available=True, physician_signed=True,
                            physics_signed=True, specialist_decision="approve")
        assert ctx["physics_available"] is True
        assert ctx["specialist_decision"] == "approve"

    def test_from_decision(self):
        dec = _good_decision()
        ctx = build_context(decision=dec)
        assert ctx["can_deliver"] is True
        assert ctx["physician_signed"] is True
        assert ctx["physics_signed"] is True

    def test_from_evaluation(self):
        ev = QualityIndicators().evaluate({"gamma_pass_rate": 0.98,
                                           "range_in_target": True,
                                           "coverage_drop": 0.0,
                                           "benchmark_passed": True,
                                           "completeness": 1.0,
                                           "reviews_signed": True})
        ctx = build_context(evaluation=ev)
        assert ctx["overall_status"] == "GREEN"

    def test_from_plan(self):
        from treatment_plan import TreatmentPlan
        p = TreatmentPlan("p1", "a")
        p.set_section("physics", {"x": 1})
        ctx = build_context(plan=p)
        assert ctx["physics_available"] is True

    def test_explicit_overrides_object(self):
        dec = _good_decision()  # physician_signed=True
        ctx = build_context(decision=dec, physician_signed=False)  # تجاوز
        assert ctx["physician_signed"] is False

    def test_empty_context(self):
        assert build_context() == {}


class TestIntegrationWithDecision:
    def test_blocked_plan_cannot_reach_ready(self, sm):
        # قرار أحمر → can_deliver=False → PHYSICIAN→READY يفشل
        ev = QualityIndicators().evaluate({
            "gamma_pass_rate": 0.80, "range_in_target": False,
            "coverage_drop": 0.3, "benchmark_passed": False,
            "completeness": 1.0, "reviews_signed": True})
        dec = DecisionModel().recommend(ev, physician_signed=True, physics_signed=True)
        ctx = build_context(decision=dec, physics_signed=True,
                            physician_signed=True, overall_status="RED",
                            physics_available=True)
        sm.transition(S.PHYSICS_REVIEW, ctx)
        # PHYSICS→PHYSICIAN يفشل لأن overall=RED
        with pytest.raises(GuardFailedError):
            sm.transition(S.PHYSICIAN_REVIEW, ctx)
