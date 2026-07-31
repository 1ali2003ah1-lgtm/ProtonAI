"""
ProtonAI - Test Motion / Adaptive Planner
اختبارات معالجة الحركة والتخطيط التكيّفي
"""

import numpy as np
import pytest
from motion_planner import MotionPlanner, _shift


@pytest.fixture
def mp():
    return MotionPlanner()


class TestShift:
    def test_shift_down(self):
        m = np.zeros((3, 3), dtype=bool)
        m[0, 1] = True
        out = _shift(m, 1, 0)
        assert out[1, 1] is np.True_
        assert out[0, 1] is np.False_

    def test_shift_up(self):
        m = np.zeros((3, 3), dtype=bool)
        m[2, 1] = True
        out = _shift(m, -1, 0)
        assert out[1, 1] is np.True_

    def test_shift_right(self):
        m = np.zeros((3, 3), dtype=bool)
        m[1, 0] = True
        out = _shift(m, 0, 1)
        assert out[1, 1] is np.True_

    def test_shift_out_of_bounds_zeroed(self):
        m = np.zeros((3, 3), dtype=bool)
        m[0, 0] = True
        out = _shift(m, -1, 0)  # يطلع فوق → يختفي
        assert out.sum() == 0

    def test_no_wrap_around(self):
        m = np.zeros((3, 3), dtype=bool)
        m[2, 2] = True
        out = _shift(m, 1, 0)  # لأسفل → يختفي، لا يلتف للأعلى
        assert out.sum() == 0


class TestComputeITV:
    def test_union_of_two_phases(self, mp):
        a = np.zeros((3, 3), dtype=bool)
        a[1, 1] = True
        b = np.zeros((3, 3), dtype=bool)
        b[1, 2] = True
        itv = mp.compute_itv([a, b])
        assert itv[1, 1] is np.True_
        assert itv[1, 2] is np.True_
        assert itv[0, 0] is np.False_
        assert itv.sum() == 2

    def test_single_phase_equals_itself(self, mp):
        a = np.zeros((3, 3), dtype=bool)
        a[0, 0] = True
        itv = mp.compute_itv([a])
        assert np.array_equal(itv, a)

    def test_empty_list_raises(self, mp):
        with pytest.raises(ValueError):
            mp.compute_itv([])

    def test_shape_mismatch_raises(self, mp):
        a = np.zeros((3, 3), dtype=bool)
        b = np.zeros((4, 4), dtype=bool)
        with pytest.raises(ValueError):
            mp.compute_itv([a, b])

    def test_accepts_int_input(self, mp):
        a = np.array([[0, 1], [1, 0]])
        itv = mp.compute_itv([a])
        assert itv.dtype == bool
        assert itv[0, 1] is np.True_


class TestExpandMargin:
    def test_radius_zero_unchanged(self, mp):
        m = np.zeros((5, 5), dtype=bool)
        m[2, 2] = True
        out = mp.expand_margin(m, 0)
        assert np.array_equal(out, m)

    def test_radius_one_disk(self, mp):
        m = np.zeros((5, 5), dtype=bool)
        m[2, 2] = True
        out = mp.expand_margin(m, 1)
        # القرص: المركز + الجيران الأربعة (بدون الزوايا)
        assert out[2, 2] is np.True_
        assert out[1, 2] is np.True_
        assert out[3, 2] is np.True_
        assert out[2, 1] is np.True_
        assert out[2, 3] is np.True_
        assert out[1, 1] is np.False_  # زاوية خارج القرص

    def test_radius_two_includes_diagonal(self, mp):
        m = np.zeros((7, 7), dtype=bool)
        m[3, 3] = True
        out = mp.expand_margin(m, 2)
        assert out[1, 3] is np.True_   # مسافة 2 عمودي
        assert out[2, 2] is np.True_   # مسافة sqrt(2) <= 2

    def test_negative_radius_raises(self, mp):
        m = np.zeros((3, 3), dtype=bool)
        with pytest.raises(ValueError):
            mp.expand_margin(m, -1)

    def test_empty_mask_raises(self, mp):
        with pytest.raises(ValueError):
            mp.expand_margin(np.array([]), 1)


class TestMotionMarginFromAmplitude:
    def test_basic(self, mp):
        # 5mm / 2mm = 2.5 → ceil = 3
        assert mp.motion_margin_from_amplitude(5.0, 2.0) == 3

    def test_exact_division(self, mp):
        assert mp.motion_margin_from_amplitude(6.0, 2.0) == 3

    def test_zero_amplitude(self, mp):
        assert mp.motion_margin_from_amplitude(0.0, 2.0) == 0

    def test_small_amplitude_rounds_up(self, mp):
        assert mp.motion_margin_from_amplitude(0.1, 2.0) == 1

    def test_negative_amplitude_raises(self, mp):
        with pytest.raises(ValueError):
            mp.motion_margin_from_amplitude(-1.0, 2.0)

    def test_zero_voxel_raises(self, mp):
        with pytest.raises(ValueError):
            mp.motion_margin_from_amplitude(5.0, 0.0)


class TestAdaptiveCheck:
    def test_identical_no_replan(self, mp):
        m = np.zeros((3, 3), dtype=bool)
        m[1, 1] = True
        res = mp.adaptive_check(m, m)
        assert res["dice"] == pytest.approx(1.0)
        assert res["volume_change_fraction"] == pytest.approx(0.0)
        assert res["needs_replan"] is False

    def test_completely_different_replan(self, mp):
        a = np.zeros((3, 3), dtype=bool)
        a[0, 0] = True
        b = np.zeros((3, 3), dtype=bool)
        b[2, 2] = True
        res = mp.adaptive_check(a, b)
        assert res["dice"] == pytest.approx(0.0)
        assert res["needs_replan"] is True

    def test_both_empty_no_replan(self, mp):
        a = np.zeros((3, 3), dtype=bool)
        b = np.zeros((3, 3), dtype=bool)
        res = mp.adaptive_check(a, b)
        assert res["dice"] == pytest.approx(1.0)
        assert res["needs_replan"] is False

    def test_volume_shrink_triggers_replan(self, mp):
        a = np.zeros((5, 5), dtype=bool)
        a[0:4, 0:4] = True  # 16 بكسل
        b = np.zeros((5, 5), dtype=bool)
        b[0:2, 0:2] = True  # 4 بكسل → تغيّر -75%
        res = mp.adaptive_check(a, b)
        assert res["volume_change_fraction"] == pytest.approx(-0.75)
        assert res["needs_replan"] is True

    def test_partial_overlap_dice(self, mp):
        a = np.zeros((4, 4), dtype=bool)
        a[0:2, 0:2] = True  # 4
        b = np.zeros((4, 4), dtype=bool)
        b[1:3, 1:3] = True  # 4، التداخل = (1,1) فقط = 1
        res = mp.adaptive_check(a, b)
        assert res["dice"] == pytest.approx(2 * 1 / 8)  # 0.25

    def test_custom_thresholds(self, mp):
        a = np.zeros((4, 4), dtype=bool)
        a[0:2, 0:2] = True
        b = np.zeros((4, 4), dtype=bool)
        b[1:3, 1:3] = True  # dice=0.25
        # عتبة dice منخفضة جداً → لا replan من الـ dice، والحجم متساوٍ → لا replan
        res = mp.adaptive_check(a, b, dice_threshold=0.1, volume_change_threshold=1.0)
        assert res["needs_replan"] is False

    def test_shape_mismatch_raises(self, mp):
        a = np.zeros((3, 3), dtype=bool)
        b = np.zeros((4, 4), dtype=bool)
        with pytest.raises(ValueError):
            mp.adaptive_check(a, b)

    def test_result_keys(self, mp):
        m = np.zeros((3, 3), dtype=bool)
        m[1, 1] = True
        res = mp.adaptive_check(m, m)
        assert {"dice", "volume_change_fraction", "needs_replan",
                "plan_volume", "current_volume"} <= set(res)


class TestGuards:
    def test_invalid_dice_threshold(self):
        with pytest.raises(ValueError):
            MotionPlanner(dice_threshold=1.5)

    def test_invalid_volume_threshold(self):
        with pytest.raises(ValueError):
            MotionPlanner(volume_change_threshold=-0.1)
