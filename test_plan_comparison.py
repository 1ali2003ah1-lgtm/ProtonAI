"""
ProtonAI - Test Plan Comparison
اختبارات مقارنة الخطط (جدول + ترتيب + توصية + تعادل + بلا بيانات)
"""

import pytest
from plan_comparison import PlanComparison, _status_rank_value, _NO_DATA_RANK
from quality_indicators import QualityIndicators, Status
from treatment_plan import TreatmentPlan, new_plan_id


def _plan(physics=None, reviews_signed=None):
    """خطة مع imaging+ai ثابتين؛ physics/reviews اختياريان للتحكم بالاكتمال"""
    p = TreatmentPlan(new_plan_id(), "anon")
    p.set_section("imaging", {"slices": 100})
    p.set_section("ai", {"pred": "ok"})
    if physics is not None:
        p.set_section("physics", physics)
    if reviews_signed is not None:
        p.set_section("reviews", {"signed": reviews_signed})
    return p


GOOD_PHYSICS = {"gamma_pass_rate": 0.98, "range_in_target": True,
                "coverage_drop": 0.0, "benchmark_passed": True}
BAD_PHYSICS = {"gamma_pass_rate": 0.80, "range_in_target": False,
               "coverage_drop": 0.3, "benchmark_passed": False}
AMBER_PHYSICS = {"gamma_pass_rate": 0.92, "range_in_target": True,
                 "coverage_drop": 0.0, "benchmark_passed": True}


def _good():
    return _plan(GOOD_PHYSICS, reviews_signed=True)


def _bad():
    return _plan(BAD_PHYSICS, reviews_signed=False)


def _amber():
    return _plan(AMBER_PHYSICS, reviews_signed=True)


@pytest.fixture
def cmp():
    return PlanComparison()


class TestStatusRankValue:
    def test_unknown_is_no_data(self):
        assert _status_rank_value(Status.UNKNOWN) == _NO_DATA_RANK

    def test_ordering(self):
        assert _status_rank_value(Status.GREEN) < _status_rank_value(Status.AMBER)
        assert _status_rank_value(Status.AMBER) < _status_rank_value(Status.RED)
        assert _status_rank_value(Status.RED) < _NO_DATA_RANK


class TestCompareGoodVsBad:
    def test_recommended_is_good(self, cmp):
        res = cmp.compare({"A": _good(), "B": _bad()})
        assert res["recommended"] == "A"
        assert res["is_decisive"] is True

    def test_ranking_order(self, cmp):
        res = cmp.compare({"A": _good(), "B": _bad()})
        assert res["ranking"] == ["A", "B"]

    def test_reason_mentions_preferred(self, cmp):
        res = cmp.compare({"A": _good(), "B": _bad()})
        assert "A" in res["recommendation_reason"]
        assert res["recommendation_reason"]  # غير فارغ


class TestCompareTie:
    def test_identical_plans_no_recommendation(self, cmp):
        res = cmp.compare({"A": _good(), "B": _good()})
        assert res["recommended"] is None
        assert res["is_decisive"] is False
        assert "تعادل" in res["recommendation_reason"]

    def test_ranking_still_two(self, cmp):
        res = cmp.compare({"A": _good(), "B": _good()})
        assert set(res["ranking"]) == {"A", "B"}


class TestCompareAmberVsGreen:
    def test_green_beats_amber(self, cmp):
        res = cmp.compare({"G": _good(), "Y": _amber()})
        assert res["recommended"] == "G"
        assert res["is_decisive"] is True

    def test_ranking_green_first(self, cmp):
        res = cmp.compare({"G": _good(), "Y": _amber()})
        assert res["ranking"][0] == "G"


class TestThreePlans:
    def test_full_ranking(self, cmp):
        res = cmp.compare({"G": _good(), "Y": _amber(), "R": _bad()})
        assert res["ranking"] == ["G", "Y", "R"]
        assert res["recommended"] == "G"


class TestNoData:
    def test_all_unknown_no_recommendation(self, cmp):
        qi = QualityIndicators()
        res = cmp.compare_evaluations({"A": qi.evaluate({}), "B": qi.evaluate({})})
        assert res["recommended"] is None
        assert res["is_decisive"] is False

    def test_unknown_loses_to_evaluated(self, cmp):
        qi = QualityIndicators()
        # A مقيّمة خضرا، B بلا بيانات
        res = cmp.compare_evaluations({
            "A": qi.evaluate({"gamma_pass_rate": 0.98, "range_in_target": True,
                              "coverage_drop": 0.0, "benchmark_passed": True,
                              "completeness": 1.0, "reviews_signed": True}),
            "B": qi.evaluate({}),
        })
        assert res["recommended"] == "A"
        assert res["ranking"][-1] == "B"  # بلا بيانات بالآخر


class TestIndicatorTable:
    def test_table_length_six(self, cmp):
        res = cmp.compare({"A": _good(), "B": _bad()})
        assert len(res["indicator_table"]) == 6

    def test_row_keys(self, cmp):
        res = cmp.compare({"A": _good(), "B": _bad()})
        row = res["indicator_table"][0]
        for k in ["indicator", "label", "values", "statuses", "symbols", "winner"]:
            assert k in row

    def test_winner_per_indicator(self, cmp):
        res = cmp.compare({"A": _good(), "B": _bad()})
        gamma_row = next(r for r in res["indicator_table"] if r["indicator"] == "gamma_pass_rate")
        assert gamma_row["winner"] == "A"  # A خضرا، B حمرا
        assert gamma_row["statuses"]["A"] == "GREEN"
        assert gamma_row["statuses"]["B"] == "RED"

    def test_winner_none_on_tie_indicator(self, cmp):
        res = cmp.compare({"A": _good(), "B": _good()})
        # كل المؤشرات متطابقة → لا فائز بأي مؤشر
        assert all(r["winner"] is None for r in res["indicator_table"])

    def test_values_present(self, cmp):
        res = cmp.compare({"A": _good(), "B": _bad()})
        gamma_row = next(r for r in res["indicator_table"] if r["indicator"] == "gamma_pass_rate")
        assert gamma_row["values"]["A"] == pytest.approx(0.98)
        assert gamma_row["values"]["B"] == pytest.approx(0.80)


class TestPerPlan:
    def test_keys(self, cmp):
        res = cmp.compare({"A": _good(), "B": _bad()})
        for k in ["overall", "overall_symbol", "n_red", "n_amber", "n_unknown", "rank_key"]:
            assert k in res["per_plan"]["A"]

    def test_good_has_no_red(self, cmp):
        res = cmp.compare({"A": _good(), "B": _bad()})
        assert res["per_plan"]["A"]["n_red"] == 0
        assert res["per_plan"]["A"]["overall"] == "GREEN"

    def test_bad_red_except_completeness(self, cmp):
        # الخطة السيئة مكتملة الأقسام (imaging+ai+physics+reviews ممتلئة)
        # → completeness أخضر (مكتملة البيانات ≠ بيانات جيدة).
        # فالأحمر = 5: gamma + range + coverage + benchmark + reviews
        res = cmp.compare({"A": _good(), "B": _bad()})
        assert res["per_plan"]["B"]["n_red"] == 5
        assert res["per_plan"]["B"]["overall"] == "RED"


class TestCompareEvaluationsDirect:
    def test_works_with_evaluate_output(self, cmp):
        qi = QualityIndicators()
        e_good = qi.evaluate({"gamma_pass_rate": 0.98, "range_in_target": True,
                              "coverage_drop": 0.0, "benchmark_passed": True,
                              "completeness": 1.0, "reviews_signed": True})
        e_bad = qi.evaluate({"gamma_pass_rate": 0.80, "range_in_target": False,
                             "coverage_drop": 0.3, "benchmark_passed": False,
                             "completeness": 1.0, "reviews_signed": False})
        res = cmp.compare_evaluations({"X": e_good, "Y": e_bad})
        assert res["recommended"] == "X"


class TestInjection:
    def test_default_builds_quality(self, cmp):
        assert isinstance(cmp.qi, QualityIndicators)

    def test_uses_injected_quality(self):
        qi = QualityIndicators(gamma_green=0.99)
        c = PlanComparison(quality=qi)
        assert c.qi is qi


class TestGuards:
    def test_single_plan_raises(self, cmp):
        with pytest.raises(ValueError):
            cmp.compare({"A": _good()})

    def test_single_evaluation_raises(self, cmp):
        qi = QualityIndicators()
        with pytest.raises(ValueError):
            cmp.compare_evaluations({"A": qi.evaluate({})})
