"""
ProtonAI - Test Stage-6 Clinical Demo
اختبارات المايسترو السريري (الأربع سيناريوهات + الحفظ + التقارير)
"""

import json
import pytest
from run_clinical_demo import run_clinical_demo, VALID_SCENARIOS, _providers
from plan_orchestrator import PlanOrchestrator
from plan_state_machine import PlanState
from decision_model import Recommendation


@pytest.fixture
def orch():
    return PlanOrchestrator()


class TestApprove:
    def test_delivered_and_green(self, orch):
        r = run_clinical_demo("approve", orchestrator=orch)["result"]
        assert r["state"] == PlanState.DELIVERED.value
        assert r["evaluation"]["overall"].name == "GREEN"
        assert r["decision"].recommendation == Recommendation.APPROVE

    def test_all_sections_filled(self, orch):
        r = run_clinical_demo("approve", orchestrator=orch)["result"]
        assert set(r["sections_filled"]) == {"imaging", "physics", "ai", "reviews"}

    def test_specialist_recorded(self, orch):
        r = run_clinical_demo("approve", orchestrator=orch)["result"]
        assert r["decision"].specialist_decision == "approve"
        assert r["decision"].specialist_id == "dr_demo"


class TestReject:
    def test_rejected_and_red(self, orch):
        r = run_clinical_demo("reject", orchestrator=orch)["result"]
        assert r["state"] == PlanState.REJECTED.value
        assert r["evaluation"]["overall"].name == "RED"
        assert r["decision"].recommendation == Recommendation.REJECT

    def test_specialist_reject_recorded(self, orch):
        r = run_clinical_demo("reject", orchestrator=orch)["result"]
        assert r["decision"].specialist_decision == "reject"


class TestReview:
    def test_review_not_delivered(self, orch):
        r = run_clinical_demo("review", orchestrator=orch)["result"]
        assert r["decision"].recommendation == Recommendation.REVIEW_REQUIRED
        assert r["state"] != PlanState.DELIVERED.value

    def test_no_specialist_decision(self, orch):
        r = run_clinical_demo("review", orchestrator=orch)["result"]
        assert r["decision"].specialist_decision is None

    def test_reaches_ready_when_amber_signed(self, orch):
        # amber + signed + can_deliver → READY (بس التوصية review)
        r = run_clinical_demo("review", orchestrator=orch)["result"]
        assert r["state"] == PlanState.READY.value


class TestCompare:
    def test_chosen_is_good(self, orch):
        c = run_clinical_demo("compare", orchestrator=orch)
        assert c["chosen"] == "good"
        assert c["comparison"]["recommended"] == "good"

    def test_overalls_correct(self, orch):
        c = run_clinical_demo("compare", orchestrator=orch)
        assert c["good_overall"] == "GREEN"
        assert c["bad_overall"] == "RED"

    def test_final_delivered(self, orch):
        c = run_clinical_demo("compare", orchestrator=orch)
        assert c["result"]["state"] == PlanState.DELIVERED.value

    def test_comparison_in_dashboard(self, orch):
        c = run_clinical_demo("compare", orchestrator=orch)
        assert c["result"]["dashboard"]["comparison"]["recommended"] == "good"
        assert "مقارنة الخطط" in c["result"]["report_markdown"]

    def test_ranking_present(self, orch):
        c = run_clinical_demo("compare", orchestrator=orch)
        assert set(c["comparison"]["ranking"]) == {"good", "bad"}


class TestProvidersRealistic:
    def test_imaging_fields(self, orch):
        r = run_clinical_demo("approve", orchestrator=orch)["result"]
        img = r["plan"].imaging
        assert img["modality"] == "CT"
        assert img["slices"] == 156
        assert img["tumor_volume_cc"] == 12.4

    def test_ai_fields(self, orch):
        r = run_clinical_demo("approve", orchestrator=orch)["result"]
        assert r["plan"].ai["predicted"] == "M"
        assert len(r["plan"].ai["top_factors"]) == 3

    def test_reviews_signed_in_good(self, orch):
        r = run_clinical_demo("approve", orchestrator=orch)["result"]
        assert r["plan"].reviews["signed"] is True

    def test_reviews_unsigned_in_bad(self, orch):
        r = run_clinical_demo("reject", orchestrator=orch)["result"]
        assert r["plan"].reviews["signed"] is False


class TestReports:
    def test_markdown_has_sections(self, orch):
        r = run_clinical_demo("approve", orchestrator=orch)["result"]
        md = r["report_markdown"]
        assert "مؤشرات الجودة" in md
        assert "القرار السريري" in md
        assert "DEMO_ANON_001" in md

    def test_html_is_document(self, orch):
        r = run_clinical_demo("approve", orchestrator=orch)["result"]
        h = r["report_html"]
        assert "<!DOCTYPE html>" in h
        assert 'dir="rtl"' in h

    def test_dashboard_six_indicators(self, orch):
        r = run_clinical_demo("approve", orchestrator=orch)["result"]
        assert len(r["dashboard"]["indicators"]) == 6


class TestSave:
    def test_saves_three_files(self, orch, tmp_path):
        out = tmp_path / "demo"
        run_clinical_demo("approve", output_dir=out, orchestrator=orch)
        assert (out / "clinical_approve.md").exists()
        assert (out / "clinical_approve.html").exists()
        assert (out / "clinical_approve.json").exists()

    def test_json_is_valid_and_has_indicators(self, orch, tmp_path):
        out = tmp_path / "demo"
        run_clinical_demo("approve", output_dir=out, orchestrator=orch)
        with open(out / "clinical_approve.json", encoding="utf-8") as f:
            data = json.load(f)
        assert "indicators" in data
        assert len(data["indicators"]) == 6

    def test_html_file_is_real_html(self, orch, tmp_path):
        out = tmp_path / "demo"
        run_clinical_demo("reject", output_dir=out, orchestrator=orch)
        txt = (out / "clinical_reject.html").read_text(encoding="utf-8")
        assert "<html" in txt

    def test_no_save_when_no_dir(self, orch):
        # بلا output_dir → ما يرمي، وما ينشئ ملفات
        r = run_clinical_demo("approve", orchestrator=orch)
        assert r["result"]["state"] == PlanState.DELIVERED.value


class TestCustomPatientId:
    def test_custom_id(self, orch):
        r = run_clinical_demo("approve", orchestrator=orch,
                              patient_id="DEMO_X")[ "result"]
        assert r["plan"].patient_id == "DEMO_X"


class TestDeterministic:
    def test_same_twice(self, orch):
        r1 = run_clinical_demo("approve", orchestrator=orch)["result"]
        r2 = run_clinical_demo("approve", orchestrator=orch)["result"]
        assert r1["state"] == r2["state"]
        assert r1["evaluation"]["overall"].name == r2["evaluation"]["overall"].name


class TestGuards:
    def test_invalid_scenario_raises(self, orch):
        with pytest.raises(ValueError):
            run_clinical_demo("weird", orchestrator=orch)

    def test_valid_scenarios_constant(self):
        assert set(VALID_SCENARIOS) == {"approve", "reject", "review", "compare"}


class TestProvidersHelper:
    def test_providers_return_dicts(self):
        prov = _providers({"x": 1}, {"signed": True})
        assert prov["physics"](None) == {"x": 1}
        assert prov["reviews"](None) == {"signed": True}
        assert prov["imaging"](None)["modality"] == "CT"

    def test_providers_isolate_copies(self):
        # تعديل الناتج ما يؤثر بالأصل (كل fn يرجع dict جديد)
        prov = _providers({"x": 1}, {"signed": True})
        d = prov["physics"](None)
        d["x"] = 999
        assert prov["physics"](None)["x"] == 1
