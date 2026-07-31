"""
ProtonAI - Test Quality Indicators
اختبارات إشارات المرور السريرية (كل مؤشر + overall + unknown + plan)
"""

import pytest
from quality_indicators import QualityIndicators, Status, Indicator
from treatment_plan import TreatmentPlan


@pytest.fixture
def qi():
    return QualityIndicators()


def _status_of(result, name):
    """استخراج حالة مؤشر بالاسم من نتيجة evaluate"""
    for ind in result["indicators"]:
        if ind.name == name:
            return ind.status
    raise KeyError(name)


class TestGamma:
    def test_green(self, qi):
        assert _status_of(qi.evaluate({"gamma_pass_rate": 0.98}), "gamma_pass_rate") == Status.GREEN

    def test_amber(self, qi):
        assert _status_of(qi.evaluate({"gamma_pass_rate": 0.92}), "gamma_pass_rate") == Status.AMBER

    def test_red(self, qi):
        assert _status_of(qi.evaluate({"gamma_pass_rate": 0.80}), "gamma_pass_rate") == Status.RED

    def test_boundary_green(self, qi):
        assert _status_of(qi.evaluate({"gamma_pass_rate": 0.95}), "gamma_pass_rate") == Status.GREEN

    def test_boundary_amber(self, qi):
        assert _status_of(qi.evaluate({"gamma_pass_rate": 0.90}), "gamma_pass_rate") == Status.AMBER

    def test_unknown(self, qi):
        assert _status_of(qi.evaluate({}), "gamma_pass_rate") == Status.UNKNOWN


class TestRange:
    def test_green(self, qi):
        assert _status_of(qi.evaluate({"range_in_target": True}), "range_in_target") == Status.GREEN

    def test_red(self, qi):
        assert _status_of(qi.evaluate({"range_in_target": False}), "range_in_target") == Status.RED

    def test_no_amber(self, qi):
        # المدى ثنائي: لا حالة أصفر أبداً
        for v in (True, False):
            assert _status_of(qi.evaluate({"range_in_target": v}), "range_in_target") in (
                Status.GREEN, Status.RED)

    def test_unknown(self, qi):
        assert _status_of(qi.evaluate({}), "range_in_target") == Status.UNKNOWN


class TestCoverage:
    def test_green(self, qi):
        assert _status_of(qi.evaluate({"coverage_drop": 0.0}), "coverage_drop") == Status.GREEN

    def test_amber(self, qi):
        assert _status_of(qi.evaluate({"coverage_drop": 0.08}), "coverage_drop") == Status.AMBER

    def test_red(self, qi):
        assert _status_of(qi.evaluate({"coverage_drop": 0.3}), "coverage_drop") == Status.RED

    def test_boundary_green(self, qi):
        assert _status_of(qi.evaluate({"coverage_drop": 0.05}), "coverage_drop") == Status.GREEN


class TestBenchmark:
    def test_green(self, qi):
        assert _status_of(qi.evaluate({"benchmark_passed": True}), "benchmark_passed") == Status.GREEN

    def test_red(self, qi):
        assert _status_of(qi.evaluate({"benchmark_passed": False}), "benchmark_passed") == Status.RED


class TestCompleteness:
    def test_green(self, qi):
        assert _status_of(qi.evaluate({"completeness": 1.0}), "completeness") == Status.GREEN

    def test_amber(self, qi):
        assert _status_of(qi.evaluate({"completeness": 0.75}), "completeness") == Status.AMBER

    def test_red(self, qi):
        assert _status_of(qi.evaluate({"completeness": 0.25}), "completeness") == Status.RED


class TestReviews:
    def test_green(self, qi):
        assert _status_of(qi.evaluate({"reviews_signed": True}), "reviews_signed") == Status.GREEN

    def test_red(self, qi):
        assert _status_of(qi.evaluate({"reviews_signed": False}), "reviews_signed") == Status.RED

    def test_unknown(self, qi):
        assert _status_of(qi.evaluate({}), "reviews_signed") == Status.UNKNOWN


class TestOverall:
    def test_all_green(self, qi):
        r = qi.evaluate({
            "gamma_pass_rate": 0.98, "range_in_target": True, "coverage_drop": 0.0,
            "benchmark_passed": True, "completeness": 1.0, "reviews_signed": True})
        assert r["overall"] == Status.GREEN
        assert r["n_red"] == 0 and r["n_amber"] == 0

    def test_worst_wins_red(self, qi):
        r = qi.evaluate({
            "gamma_pass_rate": 0.98, "range_in_target": False,  # red
            "coverage_drop": 0.08,  # amber
            "benchmark_passed": True, "completeness": 1.0, "reviews_signed": True})
        assert r["overall"] == Status.RED

    def test_worst_wins_amber(self, qi):
        r = qi.evaluate({
            "gamma_pass_rate": 0.92, "range_in_target": True, "coverage_drop": 0.0,
            "benchmark_passed": True, "completeness": 1.0, "reviews_signed": True})
        assert r["overall"] == Status.AMBER

    def test_unknown_excluded_from_overall(self, qi):
        # gamma أصفر + الباقي unknown → overall أصفر (unknown ما يدخل)
        r = qi.evaluate({"gamma_pass_rate": 0.92})
        assert r["overall"] == Status.AMBER
        assert r["n_unknown"] == 5  # الخمسة الباقين unknown

    def test_all_unknown_gives_unknown(self, qi):
        # completeness مفقود صراحة → كلهم unknown
        r = qi.evaluate({"completeness": None})
        assert r["overall"] == Status.UNKNOWN

    def test_empty_metrics_overall_unknown(self, qi):
        # بس completeness بالـ evaluate المباشر مفقود → unknown كله
        r = qi.evaluate({})
        assert r["overall"] == Status.UNKNOWN
        assert r["n_unknown"] == 6


class TestIndicatorObject:
    def test_to_dict_has_symbol(self, qi):
        r = qi.evaluate({"gamma_pass_rate": 0.98})
        ind = r["indicators"][0]
        d = ind.to_dict()
        assert d["status"] == "GREEN"
        assert d["symbol"] == "🟢"
        assert d["name"] == "gamma_pass_rate"
        assert isinstance(ind, Indicator)

    def test_message_non_empty(self, qi):
        r = qi.evaluate({"gamma_pass_rate": 0.80})
        assert all(ind.message for ind in r["indicators"])


class TestEvaluatePlan:
    def _full_plan(self):
        p = TreatmentPlan("p1", "anon")
        p.set_section("physics", {
            "gamma_pass_rate": 0.98, "range_in_target": True,
            "coverage_drop": 0.0, "benchmark_passed": True})
        p.set_section("reviews", {"signed": True})
        p.set_section("imaging", {"x": 1})
        p.set_section("ai", {"y": 2})
        return p

    def test_full_plan_green(self, qi):
        r = qi.evaluate_plan(self._full_plan())
        assert r["overall"] == Status.GREEN

    def test_incomplete_plan_red_on_completeness(self, qi):
        p = TreatmentPlan("p1", "anon")  # فاضية → completeness=0 → red
        r = qi.evaluate_plan(p)
        assert _status_of(r, "completeness") == Status.RED

    def test_unsigned_reviews_red(self, qi):
        p = self._full_plan()
        p.set_section("reviews", {"signed": False})
        r = qi.evaluate_plan(p)
        assert _status_of(r, "reviews_signed") == Status.RED

    def test_missing_physics_keys_unknown(self, qi):
        p = TreatmentPlan("p1", "anon")
        p.set_section("imaging", {"x": 1})  # completeness=0.25 → red
        r = qi.evaluate_plan(p)
        assert _status_of(r, "gamma_pass_rate") == Status.UNKNOWN


class TestCustomThresholds:
    def test_custom_gamma(self):
        qi = QualityIndicators(gamma_green=0.99, gamma_amber=0.95)
        # 0.97 صار amber الآن (كان green بالافتراضي)
        assert _status_of(qi.evaluate({"gamma_pass_rate": 0.97}), "gamma_pass_rate") == Status.AMBER

    def test_custom_coverage(self):
        qi = QualityIndicators(coverage_green=0.01, coverage_amber=0.02)
        assert _status_of(qi.evaluate({"coverage_drop": 0.05}), "coverage_drop") == Status.RED


class TestGuards:
    def test_invalid_gamma_thresholds(self):
        with pytest.raises(ValueError):
            QualityIndicators(gamma_green=0.8, gamma_amber=0.9)  # amber > green
        with pytest.raises(ValueError):
            QualityIndicators(gamma_green=1.5)

    def test_invalid_coverage_thresholds(self):
        with pytest.raises(ValueError):
            QualityIndicators(coverage_green=0.2, coverage_amber=0.1)

    def test_invalid_completeness_thresholds(self):
        with pytest.raises(ValueError):
            QualityIndicators(completeness_green=0.3, completeness_amber=0.5)
