"""
ProtonAI - Test Explainability
اختبارات تفسير القرارات
"""

import random
import pytest
from explainability import Explainability, _accuracy, _neg_mae
from generic_model import GenericModel


def _reg_data(n=120):
    """y يعتمد على f1 فقط بقوة، f2 ضوضاء عشوائية"""
    random.seed(11)
    data = []
    for i in range(n):
        f1 = float(i)
        f2 = random.uniform(-100, 100)  # لا يؤثر بـ y
        data.append({"f1": f1, "f2": f2, "y": 10 * f1 + random.uniform(-0.1, 0.1)})
    return data


def _class_data(n=120):
    data = []
    for i in range(n):
        v = 10 + i
        data.append({"f1": v, "f2": v * 2, "label": "M" if v > 70 else "B"})
    return data


@pytest.fixture
def reg_model():
    m = GenericModel(["f1", "f2"], "y", n_estimators=40, random_seed=11)
    m.fit(_reg_data())
    return m


@pytest.fixture
def cls_model():
    m = GenericModel(["f1", "f2"], "label", n_estimators=40, random_seed=11)
    m.fit(_class_data())
    return m


class TestHelpers:
    def test_accuracy(self):
        assert _accuracy(["M", "B"], ["M", "M"]) == 0.5

    def test_neg_mae(self):
        assert _neg_mae([1.0, 2.0], [2.0, 4.0]) == -1.5


class TestGlobalImportance:
    def test_keys_match_features(self, reg_model):
        imp = Explainability().global_importance(reg_model)
        assert set(imp.keys()) == {"f1", "f2"}

    def test_non_negative_and_sum_to_one(self, reg_model):
        imp = Explainability().global_importance(reg_model)
        assert all(v >= 0 for v in imp.values())
        assert abs(sum(imp.values()) - 1.0) < 1e-6

    def test_informative_feature_dominates(self, reg_model):
        imp = Explainability().global_importance(reg_model)
        assert imp["f1"] > imp["f2"]  # f1 هو المؤثر الحقيقي


class TestTopFeatures:
    def test_length_and_order(self, reg_model):
        top = Explainability().top_features(reg_model, k=2)
        assert len(top) == 2
        assert top[0]["importance"] >= top[1]["importance"]
        assert top[0]["feature"] == "f1"

    def test_k_one(self, reg_model):
        top = Explainability().top_features(reg_model, k=1)
        assert len(top) == 1

    def test_invalid_k_raises(self, reg_model):
        with pytest.raises(ValueError):
            Explainability().top_features(reg_model, k=0)


class TestPermutationImportance:
    def test_keys_and_structure(self, reg_model):
        res = Explainability(seed=11).permutation_importance(
            reg_model, _reg_data(), "y", n_repeats=4)
        assert set(res.keys()) == {"f1", "f2"}
        assert "mean" in res["f1"] and "std" in res["f1"]
        assert res["f1"]["std"] >= 0

    def test_informative_feature_drops_more(self, reg_model):
        res = Explainability(seed=11).permutation_importance(
            reg_model, _reg_data(), "y", n_repeats=8)
        assert res["f1"]["mean"] > res["f2"]["mean"]  # تبديل f1 يضر أكثر

    def test_noise_feature_near_zero(self, reg_model):
        res = Explainability(seed=11).permutation_importance(
            reg_model, _reg_data(), "y", n_repeats=8)
        assert abs(res["f2"]["mean"]) < res["f1"]["mean"]

    def test_empty_records_raises(self, reg_model):
        with pytest.raises(ValueError):
            Explainability().permutation_importance(reg_model, [], "y")

    def test_invalid_repeats_raises(self, reg_model):
        with pytest.raises(ValueError):
            Explainability().permutation_importance(reg_model, _reg_data(), "y", n_repeats=0)


class TestLocalExplanation:
    def test_regression_contribution_zero_when_ref_equals_record(self, reg_model):
        rec = _reg_data()[5]
        ex = Explainability().local_explanation(reg_model, rec, reference=rec)
        assert ex["task"] == "regression"
        assert ex["predicted"] is not None
        for f in ex["features"]:
            assert f["approx_contribution"] is not None
            assert abs(f["approx_contribution"]) < 1e-6  # نفس القيمة → لا تأثير

    def test_regression_contribution_nonzero_with_different_ref(self, reg_model):
        rec = _reg_data()[5]
        ref = dict(rec)
        ref["f1"] = 0.0  # تغيير كبير بـ f1 المؤثر
        ex = Explainability().local_explanation(reg_model, rec, reference=ref)
        contribs = {f["feature"]: f["approx_contribution"] for f in ex["features"]}
        assert abs(contribs["f1"]) > abs(contribs["f2"])  # f1 يساهم أكثر

    def test_regression_no_reference_means_no_contribution(self, reg_model):
        ex = Explainability().local_explanation(reg_model, _reg_data()[0])
        assert all(f["approx_contribution"] is None for f in ex["features"])

    def test_classification_has_probabilities(self, cls_model):
        ex = Explainability().local_explanation(cls_model, _class_data()[0])
        assert ex["task"] == "classification"
        assert ex["predicted"] in ("M", "B")
        probs = ex["class_probabilities"]
        assert set(probs.keys()) == {"M", "B"}
        assert abs(sum(probs.values()) - 1.0) < 1e-6

    def test_classification_no_contribution_field_used(self, cls_model):
        ex = Explainability().local_explanation(cls_model, _class_data()[0], reference={"f1": 0})
        # بالتصنيف لا نحسب approx_contribution (يبقى None)
        assert all(f["approx_contribution"] is None for f in ex["features"])


class TestGuards:
    def test_untrained_global_raises(self):
        m = GenericModel(["f1"], "y")
        with pytest.raises(RuntimeError):
            Explainability().global_importance(m)

    def test_untrained_permutation_raises(self):
        m = GenericModel(["f1"], "y")
        with pytest.raises(RuntimeError):
            Explainability().permutation_importance(m, [{"f1": 1, "y": 1}], "y")

    def test_untrained_local_raises(self):
        m = GenericModel(["f1"], "y")
        with pytest.raises(RuntimeError):
            Explainability().local_explanation(m, {"f1": 1})
