"""
ProtonAI - Test Plan Orchestrator
اختبارات المنسّق (ملء + تقييم + قرار + حركة + لوحة + أمان التسليم)
"""

import pytest
from plan_orchestrator import PlanOrchestrator
from treatment_plan import TreatmentPlan, new_plan_id
from decision_model import Recommendation
from plan_state_machine import PlanState

GOOD_PHYSICS = {"gamma_pass_rate": 0.98, "range_in_target": True,
                "coverage_drop": 0.0, "benchmark_passed": True}
BAD_PHYSICS = {"gamma_pass_rate": 0.80, "range_in_target": False,
               "coverage_drop": 0.3, "benchmark_passed": False}
IMAGING = {"slices": 120, "modality": "CT"}
AI = {"predicted": "ok", "confidence": 0.9}
REVIEWS = {"signed": True, "notes": "تمت المراجعة"}


def _prov(data):
    """مزوّد ثابت: يرجع data بغض النظر عن الخطة"""
    return lambda plan: data


def _full_providers(physics=GOOD_PHYSICS):
    return {"imaging": _prov(IMAGING), "physics": _prov(physics),
            "ai": _prov(AI), "reviews": _prov(REVIEWS)}


@pytest.fixture
def orch():
    return PlanOrchestrator()


class TestFilling:
    def test_all_sections_filled(self, orch):
        res = orch.run(providers=_full_providers())
        assert set(res["sections_filled"]) == {"imaging", "physics", "ai", "reviews"}
        assert res["plan"].is_complete() is True

    def test_missing_provider_leaves_empty(self, orch):
        prov = {"imaging": _prov(IMAGING), "physics": _prov(GOOD_PHYSICS)}
        res = orch.run(providers=prov)
        assert set(res["sections_filled"]) == {"imaging", "physics"}
        assert res["plan"].section_filled("ai") is False

    def test_no_providers_empty_plan(self, orch):
        res = orch.run()
        assert res["sections_filled"] == []
        assert res["plan"].completeness() == 0.0

    def test_providers_used_recorded(self, orch):
        res = orch.run(providers=_full_providers())
        assert set(res["providers_used"]) == {"imaging", "physics", "ai", "reviews"}

    def test_provider_receives_plan(self, orch):
        seen = {}
        def capture(plan):
            seen["got"] = plan
            return IMAGING
        orch.run(plan=TreatmentPlan("pX", "anon"), providers={"imaging": capture})
        assert seen["got"].plan_id == "pX"


class TestEvaluationDecision:
    def test_green_signed_approve(self, orch):
        res = orch.run(providers=_full_providers(),
                       physician_signed=True, physics_signed=True)
        assert res["evaluation"]["overall"].name == "GREEN"
        assert res["decision"].recommendation == Recommendation.APPROVE

    def test_red_reject(self, orch):
        res = orch.run(providers=_full_providers(physics=BAD_PHYSICS),
                       physician_signed=True, physics_signed=True)
        assert res["evaluation"]["overall"].name == "RED"
        assert res["decision"].recommendation == Recommendation.REJECT

    def test_unsigned_review(self, orch):
        res = orch.run(providers=_full_providers())  # تواقيع False
        assert res["decision"].recommendation == Recommendation.REVIEW_REQUIRED


class TestAutoAdvance:
    def test_full_green_signed_reaches_ready(self, orch):
        # بدون specialist → أقصى حالة = READY
        res = orch.run(providers=_full_providers(),
                       physician_signed=True, physics_signed=True)
        assert res["state"] == PlanState.READY.value

    def test_with_approve_reaches_delivered(self, orch):
        res = orch.run(providers=_full_providers(),
                       physician_signed=True, physics_signed=True,
                       specialist_decision="approve", specialist_id="dr1")
        assert res["state"] == PlanState.DELIVERED.value

    def test_red_stops_at_physics(self, orch):
        # أحمر → PHYSICS→PHYSICIAN يفشل (overall RED)
        res = orch.run(providers=_full_providers(physics=BAD_PHYSICS),
                       physician_signed=True, physics_signed=True)
        assert res["state"] == PlanState.PHYSICS_REVIEW.value

    def test_unsigned_physician_stops_at_physician(self, orch):
        # physics_signed=True بس physician_signed=False → يتوقف بـ PHYSICIAN_REVIEW
        res = orch.run(providers=_full_providers(),
                       physician_signed=False, physics_signed=True)
        assert res["state"] == PlanState.PHYSICIAN_REVIEW.value

    def test_unsigned_physics_stops_at_physics(self, orch):
        res = orch.run(providers=_full_providers(),
                       physician_signed=True, physics_signed=False)
        assert res["state"] == PlanState.PHYSICS_REVIEW.value

    def test_auto_advance_disabled_stays_draft(self, orch):
        res = orch.run(providers=_full_providers(),
                       physician_signed=True, physics_signed=True,
                       auto_advance=False)
        assert res["state"] == PlanState.DRAFT.value

    def test_history_length_matches_advances(self, orch):
        res = orch.run(providers=_full_providers(),
                       physician_signed=True, physics_signed=True)
        # DRAFT→PHYSICS→PHYSICIAN→READY = 3 انتقالات
        assert len(res["state_history"]) == 3

    def test_delivered_history_four(self, orch):
        res = orch.run(providers=_full_providers(),
                       physician_signed=True, physics_signed=True,
                       specialist_decision="approve", specialist_id="dr1")
        assert len(res["state_history"]) == 4


class TestSpecialistSafety:
    def test_specialist_without_id_raises(self, orch):
        with pytest.raises(ValueError):
            orch.run(providers=_full_providers(), specialist_decision="approve")

    def test_specialist_without_id_empty_string_raises(self, orch):
        with pytest.raises(ValueError):
            orch.run(providers=_full_providers(),
                     specialist_decision="approve", specialist_id="   ")

    def test_no_specialist_no_error(self, orch):
        res = orch.run(providers=_full_providers())  # بلا specialist → عادي
        assert res["decision"].specialist_decision is None

    def test_reject_records_decision(self, orch):
        res = orch.run(providers=_full_providers(),
                       specialist_decision="reject", specialist_id="dr2")
        assert res["decision"].specialist_decision == "reject"
        assert res["state"] == PlanState.REJECTED.value


class TestPlanBuilding:
    def test_builds_plan_when_none(self, orch):
        res = orch.run(providers=_full_providers())
        assert isinstance(res["plan"], TreatmentPlan)
        assert res["plan"].patient_id == "anonymous"

    def test_custom_patient_id(self, orch):
        res = orch.run(patient_id="anon_99")
        assert res["plan"].patient_id == "anon_99"

    def test_uses_passed_plan(self, orch):
        p = TreatmentPlan("pZ", "anon_z")
        res = orch.run(plan=p, providers=_full_providers())
        assert res["plan"].plan_id == "pZ"
        assert res["plan"].is_complete() is True  # انملأت


class TestReports:
    def test_markdown_present(self, orch):
        res = orch.run(providers=_full_providers(),
                       physician_signed=True, physics_signed=True)
        assert "# " in res["report_markdown"]
        assert "مؤشرات الجودة" in res["report_markdown"]

    def test_html_present(self, orch):
        res = orch.run(providers=_full_providers())
        assert "<!DOCTYPE html>" in res["report_html"]
        assert 'dir="rtl"' in res["report_html"]

    def test_dashboard_model_present(self, orch):
        res = orch.run(providers=_full_providers())
        assert "indicators" in res["dashboard"]
        assert len(res["dashboard"]["indicators"]) == 6


class TestComparison:
    def test_comparison_passed_to_dashboard(self, orch):
        comp = {"ranking": ["A", "B"], "recommended": "A",
                "recommendation_reason": "سبب"}
        res = orch.run(providers=_full_providers(), comparison=comp)
        assert res["dashboard"]["comparison"]["recommended"] == "A"
        assert "مقارنة الخطط" in res["report_markdown"]


class TestResultKeys:
    def test_all_keys(self, orch):
        res = orch.run(providers=_full_providers())
        for k in ["plan", "evaluation", "decision", "dashboard", "state",
                  "state_history", "sections_filled", "providers_used",
                  "report_markdown", "report_html"]:
            assert k in res


class TestInjection:
    def test_defaults_built(self, orch):
        from quality_indicators import QualityIndicators
        from decision_model import DecisionModel
        from clinical_dashboard import ClinicalDashboard
        assert isinstance(orch.quality, QualityIndicators)
        assert isinstance(orch.decision, DecisionModel)
        assert isinstance(orch.dashboard, ClinicalDashboard)
