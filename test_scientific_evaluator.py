"""
ProtonAI - Test Scientific Evaluator
اختبارات المقيّم العلمي
"""

import pytest
from scientific_evaluator import (
    ScientificEvaluator, bootstrap_ci, bootstrap_metric_ci,
    _percentile, _std,
)
from generic_model import GenericModel


def _class_data(n=60):
    data = []
    for i in range(n):
        v = 10 + i
        data.append({"f1": v, "f2": v * 2, "label": "M" if v > 40 else "B"})
    return data


def _reg_data(n=60):
    data = []
    for i in range(n):
        x = float(i)
        data.append({"x": x, "z": x * 3, "y": 2 * x + 5})
    return data


class TestHelpers:
    def test_percentile_median(self):
        assert _percentile([1.0, 2.0, 3.0], 0.5) == 2.0

    def test_percentile_single(self):
        assert _percentile([7.0], 0.5) == 7.0

    def test_percentile_empty_raises(self):
        with pytest.raises(ValueError):
            _percentile([], 0.5)

    def test_std_single_is_zero(self):
        assert _std([5.0]) == 0.0

    def test_std_known(self):
        assert abs(_std([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]) - 2.0) < 1e-9


class TestBootstrapCI:
    def test_constant_values_zero_width(self):
        ci = bootstrap_ci([3.0, 3.0, 3.0, 3.0])
        assert ci.mean == 3.0
        assert ci.ci_low == 3.0
        assert ci.ci_high == 3.0

    def test_ci_bounds_order(self):
        ci = bootstrap_ci([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        assert ci.ci_low <= ci.mean <= ci.ci_high
        assert ci.ci_low <= ci.ci_high

    def test_n_bootstrap_recorded(self):
        ci = bootstrap_ci([1.0, 2.0, 3.0], n_bootstrap=123)
        assert ci.n_bootstrap == 123

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            bootstrap_ci([])


class TestBootstrapMetricCI:
    def test_ci_around_point_estimate(self):
        yt = [1, 0, 1, 1, 0, 1, 0, 1]
        yp = [1, 0, 1, 0, 0, 1, 1, 1]
        ci = bootstrap_metric_ci(yt, yp, lambda a, b: sum(x == y for x, y in zip(a, b)) / len(a))
        assert ci.ci_low <= ci.mean <= ci.ci_high

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            bootstrap_metric_ci([], [], lambda a, b: 0.0)


class TestClassification:
    def test_perfect_accuracy(self):
        ev = ScientificEvaluator().evaluate_classification(["M", "B", "M"], ["M", "B", "M"])
        assert ev["accuracy"] == 1.0
        assert ev["f1_macro"] == 1.0

    def test_keys_present(self):
        ev = ScientificEvaluator().evaluate_classification(["M", "B"], ["M", "M"])
        for k in ["accuracy", "precision_macro", "recall_macro", "f1_macro", "classes", "confusion"]:
            assert k in ev

    def test_confusion_shape(self):
        ev = ScientificEvaluator().evaluate_classification(["M", "B", "M"], ["M", "B", "B"])
        assert len(ev["confusion"]) == 2
        assert all(len(row) == 2 for row in ev["confusion"])

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            ScientificEvaluator().evaluate_classification([], [])


class TestRegression:
    def test_perfect_mae_zero(self):
        ev = ScientificEvaluator().evaluate_regression([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        assert ev["mae"] == 0.0
        assert ev["clinical_acceptance_pct"] == 100.0

    def test_keys_present(self):
        ev = ScientificEvaluator().evaluate_regression([1.0, 2.0], [1.5, 2.5])
        for k in ["mae", "rmse", "r2", "clinical_acceptance_pct", "tolerance"]:
            assert k in ev

    def test_tolerance_affects_acceptance(self):
        ev_strict = ScientificEvaluator().evaluate_regression([10.0], [15.0], tolerance=1.0)
        ev_loose = ScientificEvaluator().evaluate_regression([10.0], [15.0], tolerance=10.0)
        assert ev_strict["clinical_acceptance_pct"] == 0.0
        assert ev_loose["clinical_acceptance_pct"] == 100.0

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            ScientificEvaluator().evaluate_regression([], [])


class TestCrossValidate:
    def test_k_folds_returned(self):
        ev = ScientificEvaluator()
        res = ev.cross_validate(_class_data(), lambda: GenericModel(["f1", "f2"], "label"), k=4)
        assert res["k"] == 4
        assert len(res["per_fold"]) == 4

    def test_mean_metrics_has_accuracy(self):
        ev = ScientificEvaluator()
        res = ev.cross_validate(_class_data(), lambda: GenericModel(["f1", "f2"], "label"), k=3)
        assert "accuracy" in res["mean_metrics"]
        assert "accuracy" in res["ci_metrics"]

    def test_stratified_keeps_both_classes(self):
        ev = ScientificEvaluator()
        res = ev.cross_validate(
            _class_data(), lambda: GenericModel(["f1", "f2"], "label"),
            k=4, stratify=True, stratify_key="label")
        for fold in res["per_fold"]:
            assert set(fold["classes"]) == {"B", "M"}

    def test_too_few_records_raises(self):
        ev = ScientificEvaluator()
        with pytest.raises(ValueError):
            ev.cross_validate(_class_data(3), lambda: GenericModel(["f1", "f2"], "label"), k=5)

    def test_regression_cv(self):
        ev = ScientificEvaluator()
        res = ev.cross_validate(_reg_data(), lambda: GenericModel(["x", "z"], "y"), k=3)
        assert "mae" in res["mean_metrics"]


class TestCompareModels:
    def test_ranking_contains_all(self):
        ev = ScientificEvaluator()
        factories = {
            "big": lambda: GenericModel(["f1", "f2"], "label", n_estimators=50),
            "small": lambda: GenericModel(["f1", "f2"], "label", n_estimators=5),
        }
        res = ev.compare_models(_class_data(), factories, k=3)
        assert set(res["ranking"]) == {"big", "small"}
        assert res["primary_metric"] == "accuracy"
        assert res["higher_better"] is True

    def test_empty_factories_raises(self):
        with pytest.raises(ValueError):
            ScientificEvaluator().compare_models(_class_data(), {})
