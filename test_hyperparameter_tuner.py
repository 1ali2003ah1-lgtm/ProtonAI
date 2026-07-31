"""
ProtonAI - Test Hyperparameter Tuner
اختبارات ضبط المعاملات الذاتي
"""

import pytest
from hyperparameter_tuner import HyperparameterTuner, TuningResult, KNOWN_PARAMS


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
        data.append({"x": x, "z": x * 2, "y": 3 * x + 1})
    return data


def _tuner_class(grid=None, **kw):
    grid = grid or {"n_estimators": [5, 20, 40]}
    return HyperparameterTuner(["f1", "f2"], "label", grid, **kw)


def _tuner_reg(grid=None, **kw):
    grid = grid or {"n_estimators": [5, 20]}
    return HyperparameterTuner(["x", "z"], "y", grid, **kw)


class TestValidation:
    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError):
            _tuner_class(strategy="weird")

    def test_invalid_val_ratio_raises(self):
        with pytest.raises(ValueError):
            _tuner_class(val_ratio=0.0)
        with pytest.raises(ValueError):
            _tuner_class(val_ratio=1.0)

    def test_invalid_n_iter_raises(self):
        with pytest.raises(ValueError):
            _tuner_class(n_iter=0)

    def test_empty_grid_raises(self):
        with pytest.raises(ValueError):
            HyperparameterTuner(["f1"], "label", {})

    def test_empty_value_list_raises(self):
        with pytest.raises(ValueError):
            HyperparameterTuner(["f1"], "label", {"n_estimators": []})

    def test_unknown_param_raises(self):
        with pytest.raises(ValueError):
            HyperparameterTuner(["f1"], "label", {"weird_param": [1]})

    def test_known_params_defined(self):
        assert "n_estimators" in KNOWN_PARAMS


class TestGridSearch:
    def test_all_combos_tried(self):
        res = _tuner_class({"n_estimators": [5, 20, 40]}).search(_class_data())
        assert res.n_trials == 3
        assert res.strategy == "grid"

    def test_two_params_product(self):
        res = _tuner_class({
            "n_estimators": [5, 20], "missing_strategy": ["drop", "fill_mean"]
        }).search(_class_data())
        assert res.n_trials == 4

    def test_best_in_results(self):
        res = _tuner_class().search(_class_data())
        scores = [r["score"] for r in res.all_results]
        assert res.best_score == max(scores)
        assert any(r["config"] == res.best_config for r in res.all_results)


class TestRandomSearch:
    def test_respects_n_iter(self):
        res = _tuner_class({"n_estimators": [5, 10, 20, 40]},
                           strategy="random", n_iter=2).search(_class_data())
        assert res.n_trials == 2

    def test_caps_at_total_combos(self):
        res = _tuner_class({"n_estimators": [5, 10]},
                           strategy="random", n_iter=99).search(_class_data())
        assert res.n_trials == 2

    def test_deterministic_with_seed(self):
        r1 = _tuner_class(strategy="random", n_iter=2, seed=7).search(_class_data())
        r2 = _tuner_class(strategy="random", n_iter=2, seed=7).search(_class_data())
        assert [r["config"] for r in r1.all_results] == [r["config"] for r in r2.all_results]


class TestImprovement:
    def test_improvement_equals_diff(self):
        res = _tuner_class().search(_class_data())
        assert abs(res.improvement - (res.best_score - res.baseline_score)) < 1e-9

    def test_baseline_config_empty(self):
        res = _tuner_class().search(_class_data())
        assert res.baseline_config == {}

    def test_higher_better_true(self):
        res = _tuner_class().search(_class_data())
        assert res.higher_better is True


class TestMetrics:
    def test_classification_metric_name(self):
        res = _tuner_class().search(_class_data())
        assert res.metric_name == "accuracy"
        assert 0.0 <= res.best_score <= 1.0

    def test_regression_metric_name(self):
        res = _tuner_reg().search(_reg_data())
        assert res.metric_name == "neg_mae"
        assert res.best_score <= 0.0  # neg_mae سالب أو صفر


class TestSplitInfo:
    def test_split_fingerprint_present(self):
        res = _tuner_class().search(_class_data())
        assert len(res.split_fingerprint) == 64

    def test_train_val_sizes(self):
        res = _tuner_class(val_ratio=0.25).search(_class_data())
        assert res.train_samples + res.val_samples == 60
        assert res.val_samples == 15


class TestResultObject:
    def test_to_dict_keys(self):
        res = _tuner_class().search(_class_data())
        d = res.to_dict()
        for k in ["best_config", "best_score", "baseline_score", "improvement",
                  "all_results", "n_trials", "strategy", "metric_name"]:
            assert k in d

    def test_empty_records_raises(self):
        with pytest.raises(ValueError):
            _tuner_class().search([])
