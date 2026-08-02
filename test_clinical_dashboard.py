"""
ProtonAI - Test Clinical Dashboard
اختبارات اللوحة (build + markdown + html + escape + مقارنة + حفظ)
"""

import pytest
from clinical_dashboard import ClinicalDashboard, _esc, _fmt_value
from quality_indicators import QualityIndicators, Status
from decision_model import DecisionModel, Recommendation
from treatment_plan import TreatmentPlan


def _good_eval():
    return QualityIndicators().evaluate({
        "gamma_pass_rate": 0.98, "range_in_target": True, "coverage_drop": 0.0,
        "benchmark_passed": True, "completeness": 1.0, "reviews_signed": True})


def _bad_eval():
    return QualityIndicators().evaluate({
        "gamma_pass_rate": 0.80, "range_in_target": False, "coverage_drop": 0.3,
        "benchmark_passed": False, "completeness": 1.0, "reviews_signed": False})


def _full_plan():
    p = TreatmentPlan("p1", "anon_x")
    p.set_section("imaging", {"slices": 100})
    p.set_section("ai", {"pred": "ok"})
    p.set_section("physics", {"gamma_pass_rate": 0.98, "range_in_target": True,
                              "coverage_drop": 0.0, "benchmark_passed": True})
    p.set_section("reviews", {"signed": True})
    return p


@pytest.fixture
def db():
    return ClinicalDashboard()


class TestHelpers:
    def test_esc_escapes_angle_brackets(self):
        assert "&lt;" in _esc("<script>") and "&gt;" in _esc("<script>")

    def test_esc_quotes(self):
        assert "&quot;" in _esc('a"b')

    def test_fmt_float(self):
        assert _fmt_value(0.9876) == "0.99"

    def test_fmt_none(self):
        assert _fmt_value(None) == "—"

    def test_fmt_other(self):
        assert _fmt_value(True) == "True"


class TestBuild:
    def test_keys_present(self, db):
        m = db.build(evaluation=_good_eval())
        for k in ["title", "generated_at", "plan_summary", "indicators",
                  "overall_symbol", "overall_status", "n_red", "n_amber",
                  "n_unknown", "decision", "comparison"]:
            assert k in m

    def test_six_indicators(self, db):
        m = db.build(evaluation=_good_eval())
        assert len(m["indicators"]) == 6

    def test_overall_green(self, db):
        m = db.build(evaluation=_good_eval())
        assert m["overall_status"] == "GREEN"
        assert m["overall_symbol"] == "🟢"

    def test_decision_auto_built(self, db):
        # بدون decision ممرّر → يُبنى تلقائياً (تواقيع False → review)
        m = db.build(evaluation=_good_eval())
        assert m["decision"]["recommendation"] == Recommendation.REVIEW_REQUIRED.value

    def test_decision_signed_approve(self, db):
        m = db.build(evaluation=_good_eval(), physician_signed=True, physics_signed=True)
        assert m["decision"]["recommendation"] == Recommendation.APPROVE.value
        assert m["decision"]["can_deliver"] is True

    def test_empty_build_no_crash(self, db):
        # بلا مدخلات → evaluation فاضي → overall UNKNOWN → incomplete
        m = db.build()
        assert m["overall_status"] == "UNKNOWN"
        assert m["decision"]["recommendation"] == Recommendation.INCOMPLETE.value

    def test_plan_summary_included(self, db):
        m = db.build(plan=_full_plan(), physician_signed=True, physics_signed=True)
        assert m["plan_summary"]["plan_id"] == "p1"
        assert m["plan_summary"]["patient_id"] == "anon_x"

    def test_comparison_optional(self, db):
        comp = {"ranking": ["A", "B"], "recommended": "A",
                "recommendation_reason": "x"}
        m = db.build(evaluation=_good_eval(), comparison=comp)
        assert m["comparison"]["recommended"] == "A"

    def test_no_comparison_is_none(self, db):
        m = db.build(evaluation=_good_eval())
        assert m["comparison"] is None


class TestBuildPlan:
    def test_end_to_end(self, db):
        m = db.build_plan(_full_plan(), physician_signed=True, physics_signed=True)
        assert m["overall_status"] == "GREEN"
        assert m["decision"]["can_deliver"] is True
        assert m["plan_summary"]["is_complete"] is True


class TestMarkdown:
    def test_has_title_and_overall(self, db):
        md = db.to_markdown(db.build(evaluation=_good_eval()))
        assert "🟢" in md
        assert "GREEN" in md

    def test_has_indicators_table(self, db):
        md = db.to_markdown(db.build(evaluation=_good_eval()))
        assert "|" in md
        assert "مؤشرات الجودة" in md

    def test_has_decision_section(self, db):
        md = db.to_markdown(db.build(evaluation=_good_eval(),
                                     physician_signed=True, physics_signed=True))
        assert "القرار السريري" in md
        assert "approve" in md

    def test_comparison_section_when_present(self, db):
        comp = {"ranking": ["A", "B"], "recommended": "A",
                "recommendation_reason": "سبب"}
        md = db.to_markdown(db.build(evaluation=_good_eval(), comparison=comp))
        assert "مقارنة الخطط" in md
        assert "سبب" in md

    def test_no_comparison_section_when_absent(self, db):
        md = db.to_markdown(db.build(evaluation=_good_eval()))
        assert "مقارنة الخطط" not in md

    def test_plan_summary_section(self, db):
        md = db.to_markdown(db.build(plan=_full_plan()))
        assert "ملخص الخطة" in md
        assert "anon_x" in md

    def test_override_warning(self, db):
        dm = DecisionModel()
        rec = dm.recommend(_bad_eval(), physician_signed=True, physics_signed=True)
        dm.record_specialist_decision(rec, "approve", "dr_senior")  # override
        m = db.build(evaluation=_bad_eval(), decision=rec)
        md = db.to_markdown(m)
        assert "تجاوز" in md


class TestHTML:
    def test_is_full_html_document(self, db):
        h = db.to_html(db.build(evaluation=_good_eval()))
        assert "<!DOCTYPE html>" in h
        assert "<html" in h and "</html>" in h
        assert "<style>" in h

    def test_rtl_and_lang(self, db):
        h = db.to_html(db.build(evaluation=_good_eval()))
        assert 'dir="rtl"' in h
        assert 'lang="ar"' in h

    def test_contains_symbols(self, db):
        h = db.to_html(db.build(evaluation=_good_eval()))
        assert "🟢" in h

    def test_contains_decision(self, db):
        h = db.to_html(db.build(evaluation=_good_eval(),
                                physician_signed=True, physics_signed=True))
        assert "القرار السريري" in h
        assert "approve" in h

    def test_six_cards(self, db):
        h = db.to_html(db.build(evaluation=_good_eval()))
        assert h.count('class="card"') == 6

    def test_comparison_section(self, db):
        comp = {"ranking": ["A", "B"], "recommended": "A",
                "recommendation_reason": "سبب"}
        h = db.to_html(db.build(evaluation=_good_eval(), comparison=comp))
        assert "مقارنة الخطط" in h

    def test_xss_escaped_in_patient_id(self, db):
        p = TreatmentPlan("p1", "<script>alert(1)</script>")
        p.set_section("imaging", {"x": 1})
        h = db.to_html(db.build(plan=p))
        assert "<script>alert(1)</script>" not in h  # ما يظهر حرفي
        assert "&lt;script&gt;" in h

    def test_xss_escaped_in_title(self, db):
        m = db.build(evaluation=_good_eval(), title="<b>bad</b>")
        h = db.to_html(m)
        assert "<b>bad</b>" not in h
        assert "&lt;b&gt;" in h

    def test_override_warning_html(self, db):
        dm = DecisionModel()
        rec = dm.recommend(_bad_eval(), physician_signed=True, physics_signed=True)
        dm.record_specialist_decision(rec, "approve", "dr_senior")
        h = db.to_html(db.build(evaluation=_bad_eval(), decision=rec))
        assert "تجاوز" in h
        assert 'class="warn"' in h


class TestSave:
    def test_save_markdown_only(self, db, tmp_path):
        m = db.build(evaluation=_good_eval())
        md = tmp_path / "d.md"
        db.save(m, md)
        assert md.exists()
        assert "🟢" in md.read_text(encoding="utf-8")

    def test_save_both(self, db, tmp_path):
        m = db.build(evaluation=_good_eval())
        md = tmp_path / "out" / "d.md"
        h = tmp_path / "out" / "d.html"
        db.save(m, md, h)
        assert md.exists() and h.exists()
        assert "<html" in h.read_text(encoding="utf-8")


class TestInjection:
    def test_default_builds_quality(self, db):
        assert isinstance(db.qi, QualityIndicators)

    def test_uses_injected_quality(self):
        qi = QualityIndicators(gamma_green=0.99)
        d = ClinicalDashboard(quality=qi)
        assert d.qi is qi
