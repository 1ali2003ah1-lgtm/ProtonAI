"""
ProtonAI - Test Dose Engine
اختبارات محرك الجرعة السريري الموحد
"""

import random
import pytest
from dose_engine import (
    DoseEngine, DEFAULT_PROTOCOLS,
    STATUS_IN_RANGE, STATUS_ABOVE, STATUS_BELOW, STATUS_UNKNOWN, STATUS_NA,
)
from generic_model import GenericModel


def _reg_data(n=90):
    """تنبؤات تقريباً بين 63 و 72"""
    random.seed(2)
    data = []
    for i in range(n):
        age = 30 + (i % 50)
        vol = 50 + (i % 200)
        extra = age * 2
        tumor = ["lung", "brain", "prostate"][i % 3]
        dose = 60 + 0.1 * age + 0.01 * vol + random.uniform(-1, 1)
        data.append({"age": age, "volume": vol, "extra": extra,
                     "tumor_type": tumor, "dose": round(dose, 2)})
    return data


def _cls_data(n=80):
    data = []
    for i in range(n):
        v = 10 + i
        data.append({"f1": v, "f2": v * 2, "tumor_type": "lung",
                     "label": "M" if v > 50 else "B"})
    return data


@pytest.fixture
def reg_model():
    m = GenericModel(["age", "volume", "extra"], "dose", n_estimators=30, random_seed=2)
    m.fit(_reg_data())
    return m


@pytest.fixture
def cls_model():
    m = GenericModel(["f1", "f2"], "label", n_estimators=30, random_seed=2)
    m.fit(_cls_data())
    return m


WIDE = {"lung": (0, 10000), "brain": (0, 10000), "prostate": (0, 10000)}
TINY = {"lung": (0, 0.001), "brain": (0, 0.001), "prostate": (0, 0.001)}
HIGH = {"lung": (10000, 20000), "brain": (10000, 20000), "prostate": (10000, 20000)}


class TestRegressionRecommend:
    def test_in_range(self, reg_model):
        rec = _reg_data()[0]
        res = DoseEngine(reg_model, protocols=WIDE).recommend(rec)
        assert res["protocol"]["status"] == STATUS_IN_RANGE
        assert res["protocol"]["in_range"] is True
        assert res["requires_review"] is False

    def test_above_range(self, reg_model):
        rec = _reg_data()[0]
        res = DoseEngine(reg_model, protocols=TINY).recommend(rec)
        assert res["protocol"]["status"] == STATUS_ABOVE
        assert res["requires_review"] is True

    def test_below_range(self, reg_model):
        rec = _reg_data()[0]
        res = DoseEngine(reg_model, protocols=HIGH).recommend(rec)
        assert res["protocol"]["status"] == STATUS_BELOW
        assert res["requires_review"] is True

    def test_unknown_tumor(self, reg_model):
        rec = dict(_reg_data()[0])
        rec["tumor_type"] = "rare_new"
        res = DoseEngine(reg_model).recommend(rec)
        assert res["protocol"]["status"] == STATUS_UNKNOWN
        assert res["protocol"]["range"] is None
        assert res["requires_review"] is True

    def test_uncertainty_present_and_ordered(self, reg_model):
        res = DoseEngine(reg_model, protocols=WIDE).recommend(_reg_data()[0])
        u = res["uncertainty"]
        assert u is not None
        assert u["ci_low"] <= res["predicted"] <= u["ci_high"]
        assert u["std"] >= 0

    def test_unit_is_gy_rbe(self, reg_model):
        res = DoseEngine(reg_model, protocols=WIDE).recommend(_reg_data()[0])
        assert res["unit"] == "Gy(RBE)"

    def test_top_factors_structure(self, reg_model):
        res = DoseEngine(reg_model, protocols=WIDE, top_k=3).recommend(_reg_data()[0])
        assert len(res["top_factors"]) == 3
        for f in res["top_factors"]:
            assert {"feature", "value", "importance"} <= set(f)
        # مرتبة تنازلياً بالأهمية
        imps = [f["importance"] for f in res["top_factors"]]
        assert imps == sorted(imps, reverse=True)

    def test_recommendation_non_empty(self, reg_model):
        res = DoseEngine(reg_model, protocols=WIDE).recommend(_reg_data()[0])
        assert isinstance(res["recommendation"], str)
        assert len(res["recommendation"]) > 0

    def test_task_field(self, reg_model):
        res = DoseEngine(reg_model, protocols=WIDE).recommend(_reg_data()[0])
        assert res["task"] == "regression"


class TestCustomProtocols:
    def test_custom_overrides_default(self, reg_model):
        # نطاق ضيق مخصص للـ lung فقط
        custom = {"lung": (65.0, 66.0)}
        eng = DoseEngine(reg_model, protocols=custom)
        assert set(eng.protocols.keys()) == {"lung"}
        # سجل lung → يُفحص بالنطاق المخصص (مو الافتراضي)
        rec = next(r for r in _reg_data() if r["tumor_type"] == "lung")
        res = eng.recommend(rec)
        assert res["protocol"]["range"] == [65.0, 66.0]

    def test_case_insensitive_tumor_match(self, reg_model):
        rec = dict(_reg_data()[0])
        rec["tumor_type"] = "LUNG"  # حروف كبيرة
        res = DoseEngine(reg_model, protocols=WIDE).recommend(rec)
        # طُبّق لـ lung → ليس unknown
        assert res["protocol"]["status"] != STATUS_UNKNOWN


class TestClassificationRecommend:
    def test_not_applicable_and_review(self, cls_model):
        res = DoseEngine(cls_model).recommend(_cls_data()[0])
        assert res["protocol"]["status"] == STATUS_NA
        assert res["requires_review"] is True
        assert res["uncertainty"] is None
        assert res["unit"] is None
        assert res["task"] == "classification"

    def test_top_factors_still_present(self, cls_model):
        res = DoseEngine(cls_model, top_k=2).recommend(_cls_data()[0])
        assert len(res["top_factors"]) == 2


class TestBatch:
    def test_batch_length(self, reg_model):
        recs = _reg_data()[:7]
        out = DoseEngine(reg_model, protocols=WIDE).recommend_batch(recs)
        assert len(out) == 7
        assert all("predicted" in r for r in out)

    def test_batch_empty(self, reg_model):
        assert DoseEngine(reg_model).recommend_batch([]) == []


class TestGuards:
    def test_invalid_top_k_raises(self, reg_model):
        with pytest.raises(ValueError):
            DoseEngine(reg_model, top_k=0)

    def test_default_protocols_loaded(self, reg_model):
        eng = DoseEngine(reg_model)
        assert set(eng.protocols.keys()) == set(DEFAULT_PROTOCOLS.keys())
