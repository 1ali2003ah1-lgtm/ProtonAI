"""
ProtonAI - Test Decision Model
اختبارات نموذج القرار (توصية + بوابة + قرار متخصص + override)
"""

import pytest
from decision_model import (
    DecisionModel, DecisionRecord, Recommendation, SpecialistDecision, _to_decision,
)
from quality_indicators import QualityIndicators, Status
from treatment_plan import TreatmentPlan


def _eval(**overrides):
    """تقييم جودة من مقاييس، مع افتراضات آمنة"""
    base = {"gamma_pass_rate": 0.98, "range_in_target": True, "coverage_drop": 0.0,
            "benchmark_passed": True, "completeness": 1.0, "reviews_signed": True}
    base.update(overrides)
    return QualityIndicators().evaluate(base)


@pytest.fixture
def dm():
    return DecisionModel()


class TestToDecision:
    def test_from_string(self):
        assert _to_decision("approve") == SpecialistDecision.APPROVE
        assert _to_decision("DEFER") == SpecialistDecision.DEFER

    def test_from_enum(self):
        assert _to_decision(SpecialistDecision.REJECT) == SpecialistDecision.REJECT

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _to_decision("maybe")


class TestRecommendApprove:
    def test_green_and_signed(self, dm):
        rec = dm.recommend(_eval(), physician_signed=True, physics_signed=True)
        assert rec.recommendation == Recommendation.APPROVE
        assert rec.can_deliver is True
        assert rec.delivery_blockers == []
        assert rec.overall_status == "GREEN"

    def test_reason_mentions_recommend(self, dm):
        rec = dm.recommend(_eval(), physician_signed=True, physics_signed=True)
        assert "موصى" in rec.recommendation_reason


class TestRecommendReview:
    def test_amber_signed(self, dm):
        rec = dm.recommend(_eval(gamma_pass_rate=0.92),
                           physician_signed=True, physics_signed=True)
        assert rec.recommendation == Recommendation.REVIEW_REQUIRED
        assert rec.can_deliver is True  # AMBER ليس مانع تسليم
        assert rec.delivery_blockers == []

    def test_green_unsigned_physician(self, dm):
        rec = dm.recommend(_eval(), physician_signed=False, physics_signed=True)
        assert rec.recommendation == Recommendation.REVIEW_REQUIRED
        assert rec.can_deliver is False
        assert "physician_unsigned" in rec.delivery_blockers

    def test_green_unsigned_physics(self, dm):
        rec = dm.recommend(_eval(), physician_signed=True, physics_signed=False)
        assert rec.recommendation == Recommendation.REVIEW_REQUIRED
        assert "physics_unsigned" in rec.delivery_blockers

    def test_green_both_unsigned(self, dm):
        rec = dm.recommend(_eval(), physician_signed=False, physics_signed=False)
        assert rec.recommendation == Recommendation.REVIEW_REQUIRED
        assert set(rec.delivery_blockers) == {"physician_unsigned", "physics_unsigned"}


class TestRecommendReject:
    def test_red(self, dm):
        rec = dm.recommend(_eval(gamma_pass_rate=0.80, range_in_target=False,
                                 coverage_drop=0.3, benchmark_passed=False),
                           physician_signed=True, physics_signed=True)
        assert rec.recommendation == Recommendation.REJECT
        assert rec.can_deliver is False
        assert "quality_red" in rec.delivery_blockers
        assert rec.overall_status == "RED"

    def test_red_unsigned_still_reject(self, dm):
        # أحمر + تواقيع ناقصة → REJECT (الأحمر يحكم التوصية) + مانعان
        rec = dm.recommend(_eval(gamma_pass_rate=0.80, range_in_target=False,
                                 coverage_drop=0.3, benchmark_passed=False),
                           physician_signed=False, physics_signed=False)
        assert rec.recommendation == Recommendation.REJECT
        assert "quality_red" in rec.delivery_blockers
        assert "physician_unsigned" in rec.delivery_blockers


class TestRecommendIncomplete:
    def test_unknown(self, dm):
        rec = dm.recommend(_eval(completeness=None),  # يجعل الكل unknown
                           physician_signed=True, physics_signed=True)
        # completeness=None → evaluate يعطي unknown له، بس الباقي مقيّم → overall مو unknown
        # نحتاج تقييم فارغ فعلياً:
        rec = dm.recommend(QualityIndicators().evaluate({}),
                           physician_signed=True, physics_signed=True)
        assert rec.recommendation == Recommendation.INCOMPLETE
        assert rec.can_deliver is False
        assert "quality_unknown" in rec.delivery_blockers


class TestDeliveryGate:
    def test_only_green_signed_delivers(self, dm):
        rec = dm.recommend(_eval(), physician_signed=True, physics_signed=True)
        assert rec.can_deliver is True

    def test_amber_signed_delivers(self, dm):
        rec = dm.recommend(_eval(gamma_pass_rate=0.92),
                           physician_signed=True, physics_signed=True)
        assert rec.can_deliver is True

    def test_red_never_delivers(self, dm):
        rec = dm.recommend(_eval(gamma_pass_rate=0.80, range_in_target=False,
                                 coverage_drop=0.3, benchmark_passed=False),
                           physician_signed=True, physics_signed=True)
        assert rec.can_deliver is False

    def test_unknown_never_delivers(self, dm):
        rec = dm.recommend(QualityIndicators().evaluate({}),
                           physician_signed=True, physics_signed=True)
        assert rec.can_deliver is False

    def test_unsigned_never_delivers(self, dm):
        rec = dm.recommend(_eval(), physician_signed=True, physics_signed=False)
        assert rec.can_deliver is False


class TestRecommendPlan:
    def _full_plan(self, signed=True):
        p = TreatmentPlan("p1", "anon")
        p.set_section("imaging", {"x": 1})
        p.set_section("ai", {"y": 2})
        p.set_section("physics", {"gamma_pass_rate": 0.98, "range_in_target": True,
                                  "coverage_drop": 0.0, "benchmark_passed": True})
        p.set_section("reviews", {"signed": signed})
        return p

    def test_plan_approve(self, dm):
        rec = dm.recommend_plan(self._full_plan(),
                                physician_signed=True, physics_signed=True)
        assert rec.recommendation == Recommendation.APPROVE

    def test_plan_unsigned_reviews_blocks(self, dm):
        # reviews غير موقّعة بالـ plan، بس التواقيع بالـ recommend_plan منفصلة
        rec = dm.recommend_plan(self._full_plan(signed=False),
                                physician_signed=False, physics_signed=False)
        assert rec.can_deliver is False


class TestSpecialistDecision:
    def _rec(self, dm, **kw):
        return dm.recommend(_eval(**kw), physician_signed=True, physics_signed=True)

    def test_record_approve_no_override(self, dm):
        rec = self._rec(dm)  # green → can_deliver True
        dm.record_specialist_decision(rec, "approve", "dr_ahmed", notes="ok")
        assert rec.specialist_decision == "approve"
        assert rec.specialist_id == "dr_ahmed"
        assert rec.specialist_notes == "ok"
        assert rec.specialist_timestamp
        assert rec.override is False

    def test_record_reject(self, dm):
        rec = self._rec(dm, gamma_pass_rate=0.80, range_in_target=False,
                        coverage_drop=0.3, benchmark_passed=False)
        dm.record_specialist_decision(rec, "reject", "dr1")
        assert rec.specialist_decision == "reject"
        assert rec.override is False

    def test_record_defer(self, dm):
        rec = self._rec(dm)
        dm.record_specialist_decision(rec, SpecialistDecision.DEFER, "dr1")
        assert rec.specialist_decision == "defer"

    def test_approve_when_blocked_is_override(self, dm):
        rec = self._rec(dm, gamma_pass_rate=0.80, range_in_target=False,
                        coverage_drop=0.3, benchmark_passed=False)  # red → blocked
        assert rec.can_deliver is False
        dm.record_specialist_decision(rec, "approve", "dr_senior", notes="استثناء سريري")
        assert rec.override is True  # تجاوز موثّق
        assert rec.specialist_decision == "approve"

    def test_double_record_raises(self, dm):
        rec = self._rec(dm)
        dm.record_specialist_decision(rec, "approve", "dr1")
        with pytest.raises(ValueError):
            dm.record_specialist_decision(rec, "reject", "dr1")

    def test_empty_specialist_id_raises(self, dm):
        rec = self._rec(dm)
        with pytest.raises(ValueError):
            dm.record_specialist_decision(rec, "approve", "")

    def test_invalid_decision_raises(self, dm):
        rec = self._rec(dm)
        with pytest.raises(ValueError):
            dm.record_specialist_decision(rec, "maybe", "dr1")


class TestRecordObject:
    def test_to_dict(self, dm):
        rec = dm.recommend(_eval(), physician_signed=True, physics_signed=True)
        d = rec.to_dict()
        assert d["recommendation"] == "approve"
        assert d["can_deliver"] is True
        assert isinstance(rec, DecisionRecord)

    def test_default_no_specialist(self, dm):
        rec = dm.recommend(_eval())
        assert rec.specialist_decision is None
        assert rec.specialist_id is None
        assert rec.override is False


class TestInjection:
    def test_default_builds_quality(self, dm):
        assert isinstance(dm.qi, QualityIndicators)

    def test_uses_injected_quality(self):
        qi = QualityIndicators(gamma_green=0.99)
        m = DecisionModel(quality=qi)
        assert m.qi is qi
