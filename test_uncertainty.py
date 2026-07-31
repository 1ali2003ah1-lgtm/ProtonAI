"""
ProtonAI - Test Uncertainty Estimation
اختبارات تقدير عدم اليقين
"""

import math
import pytest
from uncertainty import UncertaintyEstimator, _entropy, _percentile
from generic_model import GenericModel


def _reg_data(n=80):
    """بيانات تنبؤ بضوضاء (عشان يصير تباين بين الأشجار)"""
    import random
    random.seed(7)
    data = []
    for i in range(n):
        x = float(i)
        data.append({"x": x, "z": x * 2, "y": 3 * x + random.uniform(-10, 10)})
    return data


def _class_data(n=80):
    data = []
    for i in range(n):
        v = 10 + i
        data.append({"f1": v, "f2": v * 2, "label": "M" if v > 50 else "B"})
    return data


@pytest.fixture
def reg_model():
    m = GenericModel(["x", "z"], "y", n_estimators=30, random_seed=7)
    m.fit(_reg_data())
    return m


@pytest.fixture
def cls_model():
    m = GenericModel(["f1", "f2"], "label", n_estimators=30, random_seed=7)
    m.fit(_class_data())
    return m


class TestHelpers:
    def test_entropy_uniform_two_classes(self):
        assert abs(_entropy([0.5, 0.5]) - math.log(2)) < 1e-9

    def test_entropy_certain_is_zero(self):
        assert _entropy([1.0, 0.0]) == 0.0

    def test_percentile_bounds(self):
        assert _percentile([1.0, 2.0, 3.0], 0.0) == 1.0
        assert _percentile([1.0, 2.0, 3.0], 1.0) == 3.0


class TestRegressionUncertainty:
    def test_per_sample_keys(self, reg_model):
        u = UncertaintyEstimator()
        res = u.regression_uncertainty(reg_model, _reg_data()[:5])
        assert len(res) == 5
        for s in res:
            assert {"mean", "std", "ci_low", "ci_high", "n_trees"} <= set(s)

    def test_ci_order(self, reg_model):
        u = UncertaintyEstimator()
        for s in u.regression_uncertainty(reg_model, _reg_data()[:10]):
            assert s["ci_low"] <= s["mean"] <= s["ci_high"]

    def test_std_non_negative_and_some_positive(self, reg_model):
        u = UncertaintyEstimator()
        res = u.regression_uncertainty(reg_model, _reg_data())
        assert all(s["std"] >= 0 for s in res)
        assert max(s["std"] for s in res) > 0  # الضوضاء تخلق تبايناً

    def test_empty_records(self, reg_model):
        assert UncertaintyEstimator().regression_uncertainty(reg_model, []) == []


class TestClassificationUncertainty:
    def test_per_sample_keys(self, cls_model):
        u = UncertaintyEstimator()
        res = u.classification_uncertainty(cls_model, _class_data()[:5])
        assert len(res) == 5
        for s in res:
            assert {"predicted", "confidence", "entropy", "margin", "class_probs"} <= set(s)

    def test_predicted_in_classes(self, cls_model):
        u = UncertaintyEstimator()
        for s in u.classification_uncertainty(cls_model, _class_data()[:10]):
            assert s["predicted"] in ("M", "B")

    def test_confidence_bounds(self, cls_model):
        u = UncertaintyEstimator()
        for s in u.classification_uncertainty(cls_model, _class_data()):
            assert 0.0 <= s["confidence"] <= 1.0

    def test_entropy_bounded(self, cls_model):
        u = UncertaintyEstimator()
        max_h = math.log(2) + 1e-9
        for s in u.classification_uncertainty(cls_model, _class_data()):
            assert 0.0 <= s["entropy"] <= max_h

    def test_class_probs_sum_to_one(self, cls_model):
        u = UncertaintyEstimator()
        for s in u.classification_uncertainty(cls_model, _class_data()[:10]):
            assert abs(sum(s["class_probs"].values()) - 1.0) < 1e-6

    def test_empty_records(self, cls_model):
        assert UncertaintyEstimator().classification_uncertainty(cls_model, []) == []


class TestAggregate:
    def test_regression_aggregate_keys(self, reg_model):
        u = UncertaintyEstimator()
        per = u.regression_uncertainty(reg_model, _reg_data())
        agg = u.aggregate_regression(per, high_threshold=1.0)
        assert {"samples", "mean_std", "mean_ci_width", "pct_high_uncertainty"} <= set(agg)
        assert 0.0 <= agg["pct_high_uncertainty"] <= 100.0

    def test_classification_aggregate_keys(self, cls_model):
        u = UncertaintyEstimator()
        per = u.classification_uncertainty(cls_model, _class_data())
        agg = u.aggregate_classification(per, low_conf_threshold=0.99)
        assert {"samples", "mean_confidence", "mean_entropy", "pct_low_confidence"} <= set(agg)
        assert 0.0 <= agg["pct_low_confidence"] <= 100.0

    def test_aggregate_empty(self):
        u = UncertaintyEstimator()
        assert u.aggregate_regression([])["samples"] == 0
        assert u.aggregate_classification([])["samples"] == 0


class TestGuards:
    def test_untrained_model_raises(self):
        m = GenericModel(["x"], "y")
        with pytest.raises(RuntimeError):
            UncertaintyEstimator().regression_uncertainty(m, [{"x": 1}])

    def test_invalid_ci_raises(self):
        with pytest.raises(ValueError):
            UncertaintyEstimator(ci=1.5)
