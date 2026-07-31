"""
ProtonAI - Test Benchmark Baselines
اختبارات المقارنة المعيارية
"""

import math
import pytest
from benchmark import BenchmarkEvaluator, _median, _accuracy, _mae, _mse


@pytest.fixture
def ev():
    return BenchmarkEvaluator()


class TestHelpers:
    def test_median_odd(self):
        assert _median([1.0, 2.0, 3.0]) == 2.0

    def test_median_even(self):
        assert _median([1.0, 2.0, 3.0, 4.0]) == 2.5

    def test_median_single(self):
        assert _median([7.0]) == 7.0

    def test_median_empty_raises(self):
        with pytest.raises(ValueError):
            _median([])

    def test_accuracy(self):
        assert _accuracy(["M", "B", "M"], ["M", "M", "M"]) == pytest.approx(2 / 3)

    def test_accuracy_empty(self):
        assert _accuracy([], []) == 0.0

    def test_mae(self):
        assert _mae([1.0, 2.0], [2.0, 4.0]) == 1.5

    def test_mse(self):
        assert _mse([1.0, 2.0], [2.0, 4.0]) == 2.5


class TestMajority:
    def test_majority_picks_most_common(self, ev):
        acc = ev.majority_class_accuracy(["M", "M", "B"], ["M", "B"])
        assert acc == 0.5  # يتوقع M دايماً → يصيب الأول فقط

    def test_majority_all_same(self, ev):
        acc = ev.majority_class_accuracy(["M", "M"], ["M", "B"])
        assert acc == 0.5

    def test_majority_empty_train_raises(self, ev):
        with pytest.raises(ValueError):
            ev.majority_class_accuracy([], ["M"])


class TestStratifiedRandom:
    def test_balanced_expected(self, ev):
        # p_train = (0.5, 0.5), p_test = (0.5, 0.5) → 0.5
        acc = ev.stratified_random_expected_accuracy(
            ["M", "M", "B", "B"], ["M", "B"])
        assert acc == pytest.approx(0.5)

    def test_skewed_expected(self, ev):
        # p_train_M = 0.75, p_test_M = 1.0 → 0.75*1.0 + 0.25*0 = 0.75
        acc = ev.stratified_random_expected_accuracy(
            ["M", "M", "M", "B"], ["M", "M"])
        assert acc == pytest.approx(0.75)

    def test_empty_raises(self, ev):
        with pytest.raises(ValueError):
            ev.stratified_random_expected_accuracy([], ["M"])
        with pytest.raises(ValueError):
            ev.stratified_random_expected_accuracy(["M"], [])


class TestRegressionBaselines:
    def test_mean_baseline(self, ev):
        m = ev.mean_baseline_metrics([1.0, 2.0, 3.0], [2.0, 4.0])
        assert m["constant"] == 2.0
        assert m["mae"] == 1.0  # |2-2|+|4-2| / 2
        assert m["mse"] == 2.0  # (0+4)/2

    def test_median_baseline(self, ev):
        m = ev.median_baseline_metrics([1.0, 2.0, 3.0, 4.0], [2.5])
        assert m["constant"] == 2.5
        assert m["mae"] == 0.0

    def test_mean_empty_raises(self, ev):
        with pytest.raises(ValueError):
            ev.mean_baseline_metrics([], [1.0])

    def test_median_empty_raises(self, ev):
        with pytest.raises(ValueError):
            ev.median_baseline_metrics([], [1.0])


class TestSkillScores:
    def test_classification_skill(self, ev):
        # (0.9 - 0.5)/(1 - 0.5) = 0.8
        assert ev.classification_skill(0.9, 0.5) == pytest.approx(0.8)

    def test_classification_skill_perfect_base(self, ev):
        # base = 1.0 → ما في مجال للتحسن → 0.0
        assert ev.classification_skill(1.0, 1.0) == 0.0

    def test_classification_skill_negative(self, ev):
        # نموذج أسوأ من الـ baseline
        assert ev.classification_skill(0.3, 0.5) < 0.0

    def test_regression_skill(self, ev):
        # 1 - 1/4 = 0.75
        assert ev.regression_skill(1.0, 4.0) == pytest.approx(0.75)

    def test_regression_skill_both_zero(self, ev):
        assert ev.regression_skill(0.0, 0.0) == 1.0

    def test_regression_skill_base_zero_model_not(self, ev):
        assert ev.regression_skill(1.0, 0.0) == float("-inf")


class TestBaselinesAggregates:
    def test_classification_baselines_keys(self, ev):
        b = ev.classification_baselines(["M", "M", "B"], ["M", "B"])
        assert set(b.keys()) == {"majority_class", "stratified_random"}

    def test_regression_baselines_keys(self, ev):
        b = ev.regression_baselines([1.0, 2.0, 3.0], [2.0])
        assert set(b.keys()) == {"mean", "median"}
        assert "mae" in b["mean"] and "mse" in b["mean"]


class TestVerdict:
    def test_classification_beats_all(self, ev):
        v = ev.verdict({"accuracy": 0.9},
                       {"majority_class": 0.5, "stratified_random": 0.5},
                       "classification")
        assert v["beats_all_baselines"] is True
        assert all(v["beats"].values())

    def test_classification_not_beats(self, ev):
        v = ev.verdict({"accuracy": 0.4},
                       {"majority_class": 0.5, "stratified_random": 0.5},
                       "classification")
        assert v["beats_all_baselines"] is False

    def test_regression_beats_all(self, ev):
        v = ev.verdict({"mae": 1.0},
                       {"mean": {"mae": 2.0}, "median": {"mae": 2.5}},
                       "regression")
        assert v["beats_all_baselines"] is True

    def test_regression_not_beats(self, ev):
        v = ev.verdict({"mae": 3.0},
                       {"mean": {"mae": 2.0}, "median": {"mae": 2.5}},
                       "regression")
        assert v["beats_all_baselines"] is False

    def test_unknown_task_raises(self, ev):
        with pytest.raises(ValueError):
            ev.verdict({}, {}, "weird")
