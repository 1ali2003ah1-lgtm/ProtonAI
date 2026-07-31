"""
ProtonAI - Test AI Model Compare
اختبارات مقارنة النماذج
"""

import random
import pytest
from ai_model_compare import (
    AIModelComparer, NAME_SINGLE, NAME_TUNED, NAME_ENSEMBLE,
)


def _class_data(n=80):
    data = []
    for i in range(n):
        v = 10 + i
        data.append({"f1": v, "f2": v * 2, "label": "M" if v > 50 else "B"})
    return data


def _reg_data(n=80):
    random.seed(3)
    data = []
    for i in range(n):
        x = float(i)
        data.append({"x": x, "z": x * 2, "y": 3 * x + random.uniform(-2, 2)})
    return data


def _comparer_cls(**kw):
    return AIModelComparer(["f1", "f2"], "label", **kw)


def _comparer_reg(**kw):
    return AIModelComparer(["x", "z"], "y", **kw)


@pytest.fixture(scope="module")
def cls_result():
    return _comparer_cls().compare(_class_data())


@pytest.fixture(scope="module")
def reg_result():
    return _comparer_reg().compare(_reg_data())


class TestStructure:
    def test_top_keys(self, cls_result):
        for k in ["task", "primary_metric", "higher_better", "train", "test",
                  "split_fingerprint", "table", "ranking", "best_name",
                  "single_value", "values", "improvements", "beats_single"]:
            assert k in cls_result

    def test_table_has_three(self, cls_result):
        assert len(cls_result["table"]) == 3
        names = [e["name"] for e in cls_result["table"]]
        assert set(names) == {NAME_SINGLE, NAME_TUNED, NAME_ENSEMBLE}

    def test_ranking_has_three(self, cls_result):
        assert set(cls_result["ranking"]) == {NAME_SINGLE, NAME_TUNED, NAME_ENSEMBLE}

    def test_best_name_in_ranking(self, cls_result):
        assert cls_result["best_name"] in cls_result["ranking"]
        assert cls_result["best_name"] == cls_result["ranking"][0]

    def test_split_fingerprint(self, cls_result):
        assert len(cls_result["split_fingerprint"]) == 64


class TestClassification:
    def test_primary_metric_accuracy(self, cls_result):
        assert cls_result["primary_metric"] == "accuracy"
        assert cls_result["higher_better"] is True
        assert cls_result["task"] == "classification"

    def test_values_in_range(self, cls_result):
        for v in cls_result["values"].values():
            assert 0.0 <= v <= 1.0

    def test_improvements_consistent(self, cls_result):
        vals = cls_result["values"]
        imp = cls_result["improvements"]
        # classification: delta = model - single
        assert abs(imp[NAME_TUNED] - (vals[NAME_TUNED] - vals[NAME_SINGLE])) < 1e-9
        assert abs(imp[NAME_ENSEMBLE] - (vals[NAME_ENSEMBLE] - vals[NAME_SINGLE])) < 1e-9

    def test_beats_single_is_bool(self, cls_result):
        for v in cls_result["beats_single"].values():
            assert v in (True, False)

    def test_ensemble_does_not_collapse(self, cls_result):
        assert cls_result["values"][NAME_ENSEMBLE] >= 0.5


class TestRegression:
    def test_primary_metric_mae(self, reg_result):
        assert reg_result["primary_metric"] == "mae"
        assert reg_result["higher_better"] is False
        assert reg_result["task"] == "regression"

    def test_values_non_negative(self, reg_result):
        for v in reg_result["values"].values():
            assert v >= 0.0

    def test_improvements_consistent(self, reg_result):
        vals = reg_result["values"]
        imp = reg_result["improvements"]
        # regression: delta = single - model (lower mae = better)
        assert abs(imp[NAME_TUNED] - (vals[NAME_SINGLE] - vals[NAME_TUNED])) < 1e-9
        assert abs(imp[NAME_ENSEMBLE] - (vals[NAME_SINGLE] - vals[NAME_ENSEMBLE])) < 1e-9


class TestSplitSizes:
    def test_train_test_sum_cls(self, cls_result):
        assert cls_result["train"] + cls_result["test"] == 80

    def test_train_test_sum_reg(self, reg_result):
        assert reg_result["train"] + reg_result["test"] == 80


class TestDeterministic:
    def test_same_result_twice(self, cls_result):
        r2 = _comparer_cls().compare(_class_data())
        assert r2["ranking"] == cls_result["ranking"]
        assert r2["values"] == cls_result["values"]
        assert r2["split_fingerprint"] == cls_result["split_fingerprint"]


class TestCustomConfigs:
    def test_custom_ensemble_and_grid(self):
        comp = _comparer_cls(
            ensemble_configs=[{"n_estimators": 10}, {"n_estimators": 20}],
            tuner_grid={"n_estimators": [10, 20]},
        )
        res = comp.compare(_class_data())
        assert len(res["table"]) == 3
        # الـ ensemble فيه نموذجان
        ens_entry = next(e for e in res["table"] if e["name"] == NAME_ENSEMBLE)
        assert ens_entry["metrics"]["n_models"] == 2


class TestGuards:
    def test_empty_records_raises(self):
        with pytest.raises(ValueError):
            _comparer_cls().compare([])

    def test_invalid_train_ratio_raises(self):
        with pytest.raises(ValueError):
            _comparer_cls(train_ratio=1.0)
        with pytest.raises(ValueError):
            _comparer_cls(train_ratio=0.0)

    def test_empty_features_raises(self):
        with pytest.raises(ValueError):
            AIModelComparer([], "label")

    def test_empty_ensemble_configs_raises(self):
        with pytest.raises(ValueError):
            _comparer_cls(ensemble_configs=[])

    def test_empty_tuner_grid_raises(self):
        with pytest.raises(ValueError):
            _comparer_cls(tuner_grid={})
