"""
ProtonAI - Test Tissue Segmenter
اختبارات تقسيم الأنسجة الكلاسيكي
"""

import numpy as np
import pytest
from tissue_segmenter import (
    TissueSegmenter, DEFAULT_TISSUE_RANGES, UNCLASSIFIED,
)


def _pixels():
    """مصفوفة 2x3 بقيم معروفة تغطي كل النطاقات + فجوة"""
    # air=-1000, lung=-700, fat=-100, soft=50, bone=500, unclassified=-300
    return np.array([[-1000.0, -700.0, -100.0],
                     [50.0, 500.0, -300.0]])


@pytest.fixture
def seg():
    return TissueSegmenter()


class TestSegment:
    def test_each_tissue_mask_shape(self, seg):
        masks = seg.segment(_pixels())
        for name in seg.tissue_names:
            assert masks[name].shape == (2, 3)
            assert masks[name].dtype == bool

    def test_includes_unclassified_by_default(self, seg):
        masks = seg.segment(_pixels())
        assert UNCLASSIFIED in masks

    def test_air_mask(self, seg):
        m = seg.segment(_pixels())["air"]
        assert m[0, 0] is np.True_
        assert m[0, 1] is np.False_

    def test_lung_mask(self, seg):
        m = seg.segment(_pixels())["lung"]
        assert m[0, 1] is np.True_

    def test_fat_mask(self, seg):
        m = seg.segment(_pixels())["fat"]
        assert m[0, 2] is np.True_

    def test_soft_tissue_mask(self, seg):
        m = seg.segment(_pixels())["soft_tissue"]
        assert m[1, 0] is np.True_

    def test_bone_mask(self, seg):
        m = seg.segment(_pixels())["bone"]
        assert m[1, 1] is np.True_

    def test_unclassified_catches_gap(self, seg):
        m = seg.segment(_pixels())[UNCLASSIFIED]
        assert m[1, 2] is np.True_  # -300 بالفجوة

    def test_masks_are_mutually_exclusive(self, seg):
        """كل بكسل ينتمي لفئة وحدة بالضبط (مع unclassified)"""
        masks = seg.segment(_pixels())
        stack = np.stack([masks[n] for n in seg.tissue_names + [UNCLASSIFIED]])
        assert np.all(stack.sum(axis=0) == 1)

    def test_no_unclassified_when_disabled(self):
        s = TissueSegmenter(include_unclassified=False)
        masks = s.segment(_pixels())
        assert UNCLASSIFIED not in masks


class TestBoundary:
    def test_lo_inclusive_hi_exclusive(self, seg):
        # -900 = حد lung السفلي (مغلق) → lung، مو air
        arr = np.array([[-900.0]])
        m = seg.segment(arr)
        assert m["lung"][0, 0] is np.True_
        assert m["air"][0, 0] is np.False_

    def test_hi_exclusive(self, seg):
        # -500 = حد lung العلوي (مفتوح) → ليس lung (فجوة)
        arr = np.array([[-500.0]])
        m = seg.segment(arr)
        assert m["lung"][0, 0] is np.False_
        assert m[UNCLASSIFIED][0, 0] is np.True_


class TestTissueMap:
    def test_shape_and_dtype(self, seg):
        tm = seg.tissue_map(_pixels())
        assert tm.shape == (2, 3)
        assert tm.dtype == int

    def test_zero_for_unclassified(self, seg):
        tm = seg.tissue_map(_pixels())
        assert tm[1, 2] == 0  # -300

    def test_positive_for_classified(self, seg):
        tm = seg.tissue_map(_pixels())
        # كل البكسلات المصنّفة > 0
        assert tm[0, 0] > 0
        assert tm[1, 1] > 0

    def test_alphabetical_ordering(self, seg):
        # air < bone < fat < lung < soft_tissue → أرقام 1..5
        names = seg.tissue_names
        assert names == sorted(names)
        tm = seg.tissue_map(_pixels())
        # air=1, lung=4, fat=3, soft=5, bone=2 (حسب الأبجدي)
        assert tm[0, 0] == names.index("air") + 1
        assert tm[1, 1] == names.index("bone") + 1


class TestVolumeFraction:
    def test_six_pixels_each_one_sixth(self, seg):
        # 6 بكسلات، كل نسيج/فجوة بكسل واحد
        for name in seg.tissue_names:
            assert seg.volume_fraction(_pixels(), name) == pytest.approx(1 / 6)

    def test_unclassified_fraction(self, seg):
        assert seg.volume_fraction(_pixels(), UNCLASSIFIED) == pytest.approx(1 / 6)

    def test_unknown_tissue_raises(self, seg):
        with pytest.raises(ValueError):
            seg.volume_fraction(_pixels(), "plasma")

    def test_unclassified_when_disabled(self):
        s = TissueSegmenter(include_unclassified=False)
        # -300 ما ينتمي لأي نسيج → unclassified محسوب = 1/6
        assert s.volume_fraction(_pixels(), UNCLASSIFIED) == pytest.approx(1 / 6)

    def test_fractions_sum_to_one_with_unclassified(self, seg):
        total = sum(seg.volume_fraction(_pixels(), n)
                    for n in seg.tissue_names + [UNCLASSIFIED])
        assert total == pytest.approx(1.0)


class TestSummary:
    def test_keys_per_tissue(self, seg):
        summ = seg.summary(_pixels())
        for name in seg.tissue_names + [UNCLASSIFIED]:
            assert {"count", "fraction", "mean_hu"} <= set(summ[name])

    def test_count_correct(self, seg):
        summ = seg.summary(_pixels())
        assert summ["air"]["count"] == 1
        assert summ["bone"]["count"] == 1

    def test_mean_hu_correct(self, seg):
        summ = seg.summary(_pixels())
        assert summ["air"]["mean_hu"] == pytest.approx(-1000.0)
        assert summ["bone"]["mean_hu"] == pytest.approx(500.0)

    def test_unclassified_mean_hu(self, seg):
        summ = seg.summary(_pixels())
        assert summ[UNCLASSIFIED]["mean_hu"] == pytest.approx(-300.0)

    def test_no_unclassified_key_when_disabled(self):
        s = TissueSegmenter(include_unclassified=False)
        summ = s.summary(_pixels())
        assert UNCLASSIFIED not in summ


class TestCustomRanges:
    def test_custom_overrides(self):
        s = TissueSegmenter(ranges={"water": (-10.0, 10.0)})
        arr = np.array([[0.0, 50.0]])
        m = s.segment(arr)
        assert "water" in m
        assert m["water"][0, 0] is np.True_
        assert m["water"][0, 1] is np.False_
        assert s.tissue_names == ["water"]

    def test_invalid_range_raises(self):
        with pytest.raises(ValueError):
            TissueSegmenter(ranges={"x": (10.0, 10.0)})  # lo == hi

    def test_inverted_range_raises(self):
        with pytest.raises(ValueError):
            TissueSegmenter(ranges={"x": (100.0, 10.0)})  # lo > hi

    def test_empty_ranges_raises(self):
        with pytest.raises(ValueError):
            TissueSegmenter(ranges={})


class TestGuards:
    def test_empty_pixels_raises(self, seg):
        with pytest.raises(ValueError):
            seg.segment(np.array([]))

    def test_accepts_list_input(self, seg):
        # تحويل تلقائي من قائمة
        m = seg.segment([[-1000.0, 50.0]])
        assert m["air"][0, 0] is np.True_

    def test_default_ranges_loaded(self, seg):
        assert set(seg.tissue_names) == set(DEFAULT_TISSUE_RANGES.keys())
