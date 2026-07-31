"""
ProtonAI - Test Ensemble Model
اختبارات تجميع النماذج
"""

import pytest
from ensemble_model import EnsembleModel


def _class_data(n=80):
    data = []
    for i in range(n):
        v = 10 + i
        data.append({"f1": v, "f2": v * 2, "label": "M" if v > 50 else "B"})
    return data


def _reg_data(n=80):
    import random
    random.seed(5)
    data = []
    for i in range(n):
        x = float(i)
        data.append({"x": x, "z": x * 2, "y": 3 * x + random.uniform(-3, 3)})
    return data


def _ens_class(configs=None, **kw):
    return EnsembleModel(["f1", "f2"], "label", configs=configs, **kw)


def _ens_reg(configs=None, **kw):
    return EnsembleModel(["x", "z"], "y", configs=configs, **kw)


class TestFit:
    def test_default_three_models(self):
        e = _ens_class()
        res = e.fit(_class_data())
        assert res["n_models"] == 3
        assert res["task"] == "classification"
        assert e.is_trained is True

    def test_custom_configs(self):
        e = _ens_class(configs=[{"n_estimators": 10}, {"n_estimators": 30}])
        res = e.fit(_class_data())
        assert res["n_models"] == 2

    def test_regression_task(self):
        e = _ens_reg()
        res = e.fit(_reg_data())
        assert res["task"] == "regression"

    def test_empty_records_raises(self):
        with pytest.raises(ValueError):
            _ens_class().fit([])

    def test_empty_configs_raises(self):
        with pytest.raises(ValueError):
            EnsembleModel(["f1"], "label", configs=[])

    def test_empty_features_raises(self):
        with pytest.raises(ValueError):
            EnsembleModel([], "label")

    def test_invalid_ci_raises(self):
        with pytest.raises(ValueError):
            EnsembleModel(["f1"], "label", ci=1.5)


class TestPredictClassification:
    def test_returns_labels(self):
        e = _ens_class()
        e.fit(_class_data())
        preds = e.predict(_class_data()[:5])
        assert len(preds) == 5
        assert all(p in ("M", "B") for p in preds)

    def test_high_accuracy(self):
        e = _ens_class()
        e.fit(_class_data())
        ev = e.evaluate(_class_data())
        assert ev["accuracy"] >= 0.9

    def test_proba_sums_to_one(self):
        e = _ens_class()
        e.fit(_class_data())
        probs = e.predict_proba_ensemble(_class_data()[:5])
        assert len(probs) == 5
        for row in probs:
            assert set(row.keys()) == {"M", "B"}
            assert abs(sum(row.values()) - 1.0) < 1e-6

    def test_proba_regression_raises(self):
        e = _ens_reg()
        e.fit(_reg_data())
        with pytest.raises(RuntimeError):
            e.predict_proba_ensemble(_reg_data()[:1])

    def test_empty_records(self):
        e = _ens_class()
        e.fit(_class_data())
        assert e.predict([]) == []
        assert e.predict_proba_ensemble([]) == []


class TestPredictRegression:
    def test_returns_floats(self):
        e = _ens_reg()
        e.fit(_reg_data())
        preds = e.predict(_reg_data()[:5])
        assert len(preds) == 5
        assert all(isinstance(p, float) for p in preds)

    def test_low_mae(self):
        e = _ens_reg()
        e.fit(_reg_data())
        ev = e.evaluate(_reg_data())
        assert ev["mae"] < 3.0

    def test_uncertainty_keys_and_order(self):
        e = _ens_reg()
        e.fit(_reg_data())
        unc = e.predict_with_uncertainty(_reg_data()[:5])
        assert len(unc) == 5
        for u in unc:
            assert {"mean", "std", "ci_low", "ci_high", "n_models"} <= set(u)
            assert u["ci_low"] <= u["mean"] <= u["ci_high"]
            assert u["std"] >= 0

    def test_uncertainty_classification_raises(self):
        e = _ens_class()
        e.fit(_class_data())
        with pytest.raises(RuntimeError):
            e.predict_with_uncertainty(_class_data()[:1])

    def test_uncertainty_empty(self):
        e = _ens_reg()
        e.fit(_reg_data())
        assert e.predict_with_uncertainty([]) == []


class TestEvaluate:
    def test_classification_keys(self):
        e = _ens_class()
        e.fit(_class_data())
        ev = e.evaluate(_class_data())
        assert {"task", "accuracy", "n_models", "samples"} <= set(ev)

    def test_regression_keys(self):
        e = _ens_reg()
        e.fit(_reg_data())
        ev = e.evaluate(_reg_data())
        assert {"task", "mae", "r2", "n_models", "samples"} <= set(ev)


class TestPersistence:
    def test_save_load_classification(self, tmp_path):
        e = _ens_class()
        e.fit(_class_data())
        p1 = e.predict(_class_data()[:5])
        path = tmp_path / "ens.pkl"
        e.save(path)
        e2 = _ens_class()
        e2.load(path)
        p2 = e2.predict(_class_data()[:5])
        assert p1 == p2
        assert e2.is_trained is True
        assert len(e2.models) == 3

    def test_save_load_regression(self, tmp_path):
        e = _ens_reg()
        e.fit(_reg_data())
        p1 = e.predict(_reg_data()[:5])
        path = tmp_path / "ens.pkl"
        e.save(path)
        e2 = _ens_reg()
        e2.load(path)
        p2 = e2.predict(_reg_data()[:5])
        assert p1 == p2


class TestGuards:
    def test_predict_before_fit_raises(self):
        with pytest.raises(RuntimeError):
            _ens_class().predict(_class_data()[:1])

    def test_evaluate_before_fit_raises(self):
        with pytest.raises(RuntimeError):
            _ens_class().evaluate(_class_data()[:1])
