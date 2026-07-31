"""
ProtonAI - Test Adaptive Physics Evaluation
اختبارات التقييم التكيّفي (تغطية الجرعة + ربط motion_planner)
"""

import numpy as np
import pytest
from adaptive_physics import (
    AdaptivePhysics, DEFAULT_DOSE_THRESHOLD_FRAC, DEFAULT_COVERAGE_DROP_THRESHOLD,
)
from motion_planner import MotionPlanner

DEPTHS = np.arange(0, 100, 1.0)


def _dose():
    """توزيع جرعة شكلي: فعّال بـ [40,60] وصفر برّا"""
    return np.where((DEPTHS >= 40) & (DEPTHS <= 60), 1.0, 0.0)


def _prof(lo, hi):
    """قناع ورم 1D بـ [lo, hi]"""
    return (DEPTHS >= lo) & (DEPTHS <= hi)


@pytest.fixture
def ap():
    return AdaptivePhysics()


class TestCoverage:
    def test_full_when_inside(self, ap):
        assert ap.coverage(_prof(45, 55), _dose()) == pytest.approx(1.0)

    def test_zero_when_outside(self, ap):
        assert ap.coverage(_prof(70, 80), _dose()) == pytest.approx(0.0)

    def test_partial_when_shifted(self, ap):
        # [55,65]: التقاطع مع [40,60] = [55,60] = 6 من 11
        assert ap.coverage(_prof(55, 65), _dose()) == pytest.approx(6 / 11)

    def test_empty_tumor_returns_one(self, ap):
        assert ap.coverage(_prof(200, 200), _dose()) == pytest.approx(1.0)  # فاضي

    def test_threshold_stricter_reduces_coverage(self, ap):
        # منحنى متدرّج: 0.5 بـ [40,50]، 1.0 بـ [50,60]
        dose = np.where((DEPTHS >= 50) & (DEPTHS <= 60), 1.0,
               np.where((DEPTHS >= 40) & (DEPTHS < 50), 0.5, 0.0))
        tumor = _prof(40, 60)  # 21 بكسل
        # frac=0.95 → فعّال = [50,60] = 11 → 11/21
        assert ap.coverage(tumor, dose, dose_threshold_frac=0.95) == pytest.approx(11 / 21)
        # frac=0.4 → فعّال = [40,60] = 21 → 1.0
        assert ap.coverage(tumor, dose, dose_threshold_frac=0.4) == pytest.approx(1.0)

    def test_invalid_threshold_raises(self, ap):
        with pytest.raises(ValueError):
            ap.coverage(_prof(45, 55), _dose(), dose_threshold_frac=1.5)

    def test_zero_dose_raises(self, ap):
        with pytest.raises(ValueError):
            ap.coverage(_prof(45, 55), np.zeros_like(DEPTHS))


class TestEvaluateNoReplan:
    def test_identical_no_replan(self, ap):
        res = ap.evaluate(_prof(45, 55), _prof(45, 55), _dose())
        assert res["needs_replan"] is False
        assert res["reasons"] == []
        assert res["coverage_drop"] == pytest.approx(0.0)
        assert res["nominal_coverage"] == pytest.approx(1.0)

    def test_nominal_and_current_full(self, ap):
        res = ap.evaluate(_prof(45, 55), _prof(45, 55), _dose())
        assert res["current_coverage"] == pytest.approx(1.0)


class TestEvaluateReplanCoverage:
    def test_replan_when_coverage_collapses(self, ap):
        # الورم تحرّك لـ [55,65] → تغطية تنهار
        res = ap.evaluate(_prof(45, 55), _prof(55, 65), _dose())
        assert res["needs_replan"] is True
        assert "coverage_drop" in res["reasons"]
        assert res["coverage_drop"] > DEFAULT_COVERAGE_DROP_THRESHOLD

    def test_replan_from_coverage_only_with_lenient_motion(self):
        # motion متساهل جداً (ما يفعّل أبداً) → replan بسبب coverage فقط
        lenient = MotionPlanner(dice_threshold=0.0, volume_change_threshold=1e9)
        ap = AdaptivePhysics(motion_planner=lenient)
        res = ap.evaluate(_prof(45, 55), _prof(55, 65), _dose())
        assert res["motion"]["needs_replan"] is False  # motion ما قال replan
        assert res["needs_replan"] is True              # بس coverage قال
        assert res["reasons"] == ["coverage_drop"]


class TestEvaluateReplanMotion:
    def test_replan_from_motion_only(self, ap):
        # current أكبر بنفس الموضع تقريباً → coverage=1 (drop=0) بس motion replan
        # plan [45,55]=11, current [42,58]=17 داخل [40,60] → coverage=1 لكليهما
        res = ap.evaluate(_prof(45, 55), _prof(42, 58), _dose())
        assert res["coverage_drop"] == pytest.approx(0.0)
        assert res["motion"]["needs_replan"] is True
        assert res["needs_replan"] is True
        assert "coverage_drop" not in res["reasons"]
        assert ("motion_dice" in res["reasons"] or "motion_volume" in res["reasons"])


class TestEvaluateReasons:
    def test_both_reasons_when_shifted_and_resized(self, ap):
        # تحرّك + تغيّر حجم → coverage ينهار + motion replan
        res = ap.evaluate(_prof(45, 55), _prof(55, 70), _dose())
        assert res["needs_replan"] is True
        assert "coverage_drop" in res["reasons"]

    def test_improvement_does_not_trigger(self, ap):
        # current مغطى أكثر من plan (تحسّن) → drop سالب → ما يفعّل coverage
        # plan [40,70] (جزء برّا [40,60])، current [45,55] (كله داخل)
        res = ap.evaluate(_prof(40, 70), _prof(45, 55), _dose())
        assert res["coverage_drop"] < 0  # تحسّن
        # coverage_drop سالب ما يفعّل؛ motion قد يفعّل حسب dice — نتحقق المنطق فقط
        assert "coverage_drop" not in res["reasons"]


class TestResultKeys:
    def test_keys(self, ap):
        res = ap.evaluate(_prof(45, 55), _prof(45, 55), _dose())
        for k in ["nominal_coverage", "current_coverage", "coverage_drop",
                  "coverage_drop_threshold", "motion", "needs_replan", "reasons"]:
            assert k in res

    def test_motion_subdict_present(self, ap):
        res = ap.evaluate(_prof(45, 55), _prof(45, 55), _dose())
        assert "dice" in res["motion"]
        assert "needs_replan" in res["motion"]


class TestInjection:
    def test_default_builds_motion(self, ap):
        assert isinstance(ap.motion, MotionPlanner)

    def test_uses_injected_motion(self):
        m = MotionPlanner()
        ap = AdaptivePhysics(motion_planner=m)
        assert ap.motion is m


class TestGuards:
    def test_size_mismatch_raises(self, ap):
        with pytest.raises(ValueError):
            ap.evaluate(_prof(45, 55), _prof(45, 55), _dose()[:10])

    def test_empty_raises(self, ap):
        with pytest.raises(ValueError):
            ap.evaluate(np.array([]), np.array([]), np.array([]))

    def test_invalid_coverage_drop_threshold(self, ap):
        with pytest.raises(ValueError):
            ap.evaluate(_prof(45, 55), _prof(45, 55), _dose(),
                        coverage_drop_threshold=-0.1)
