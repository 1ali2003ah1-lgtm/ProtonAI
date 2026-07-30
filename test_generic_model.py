"""
ProtonAI - Test Generic Model
اختبارات النموذج العام
"""

import pytest
from generic_model import GenericModel


def _class_data():
    """بيانات تصنيف: قيمة عالية → M، منخفضة → B"""
    data = []
    for i in range(40):
        v = 10 + i
        label = "M" if v > 30 else "B"
        data.append({"f1": v, "f2": v * 2, "label": label})
    return data


def _reg_data():
    """بيانات تنبؤ: y = 2x + 5"""
    data = []
    for i in range(40):
        x = float(i)
        data.append({"x": x, "z": x * 3, "y": 2 * x + 5})
    return data


class TestTaskDetection:
    def test_auto_classification(self):
        m = GenericModel(["f1", "f2"], "label")
        res = m.fit(_class_data())
        assert res["task"] == "classification"
        assert m.task_ == "classification"
        assert set(m.classes_) == {"B", "M"}

    def test_auto_regression(self):
        m = GenericModel(["x", "z"], "y")
        res = m.fit(_reg_data())
        assert res["task"] == "regression"

    def test_explicit_task_override(self):
        m = GenericModel(["f1", "f2"], "label", task="classification")
        res = m.fit(_class_data())
        assert res["task"] == "classification"


class TestClassification:
    def test_predict_returns_labels(self):
        m = GenericModel(["f1", "f2"], "label")
        m.fit(_class_data())
        preds = m.predict(_class_data()[:5])
        assert all(p in ("M", "B") for p in preds)

    def test_high_accuracy_on_train(self):
        m = GenericModel(["f1", "f2"], "label")
        m.fit(_class_data())
        ev = m.evaluate(_class_data())
        assert ev["accuracy"] >= 0.9

    def test_confusion_structure(self):
        m = GenericModel(["f1", "f2"], "label")
        m.fit(_class_data())
        ev = m.evaluate(_class_data())
        cm = ev["confusion"]
        assert set(cm.keys()) == {"B", "M"}
        total = sum(cm[a][b] for a in cm for b in cm[a])
        assert total == 40


class TestRegression:
    def test_predict_returns_floats(self):
        m = GenericModel(["x", "z"], "y")
        m.fit(_reg_data())
        preds = m.predict(_reg_data()[:5])
        assert all(isinstance(p, float) for p in preds)

    def test_low_mae_on_train(self):
        m = GenericModel(["x", "z"], "y")
        m.fit(_reg_data())
        ev = m.evaluate(_reg_data())
        assert ev["mae"] < 2.0
        assert ev["task"] == "regression"


class TestEvaluationKeys:
    def test_classification_keys(self):
        m = GenericModel(["f1", "f2"], "label")
        m.fit(_class_data())
        ev = m.evaluate(_class_data())
        assert {"task", "accuracy", "samples", "classes", "confusion"} <= set(ev)

    def test_regression_keys(self):
        m = GenericModel(["x", "z"], "y")
        m.fit(_reg_data())
        ev = m.evaluate(_reg_data())
        assert {"task", "mae", "r2", "samples"} <= set(ev)


class TestPersistence:
    def test_save_load_classification(self, tmp_path):
        m = GenericModel(["f1", "f2"], "label")
        m.fit(_class_data())
        p1 = m.predict(_class_data()[:5])
        path = tmp_path / "model.pkl"
        m.save(path)
        m2 = GenericModel(["f1", "f2"], "label")
        m2.load(path)
        p2 = m2.predict(_class_data()[:5])
        assert p1 == p2
        assert m2.task_ == "classification"


class TestEdgeCases:
    def test_predict_before_fit_raises(self):
        with pytest.raises(RuntimeError):
            GenericModel(["f1"], "label").predict([{"f1": 1}])

    def test_evaluate_before_fit_raises(self):
        with pytest.raises(RuntimeError):
            GenericModel(["f1"], "label").evaluate([{"f1": 1, "label": "M"}])

    def test_empty_fit_raises(self):
        with pytest.raises(ValueError):
            GenericModel(["f1"], "label").fit([])

    def test_invalid_task_raises(self):
        with pytest.raises(ValueError):
            GenericModel(["f1"], "label", task="weird")

    def test_missing_feature_drop(self):
        data = _class_data()
        data[0]["f1"] = None
        m = GenericModel(["f1", "f2"], "label", missing_strategy="drop")
        res = m.fit(data)
        assert res["samples"] == 39
