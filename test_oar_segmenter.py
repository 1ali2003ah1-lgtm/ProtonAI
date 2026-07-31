"""
ProtonAI - Test OAR Segmenter
اختبارات تقسيم الأعضاء المعرضة للخطر (HU + region masks)
"""

import numpy as np
import pytest
from oar_segmenter import OARSegmenter, DEFAULT_OAR_RANGES, BACKGROUND


def _pixels():
    """3x3 بقيم معروفة: lung/heart/spinal_cord/bone_marrow + خلفية واحدة"""
    # lung=-700, heart=50, spinal_cord=20, bone_marrow=200, background=-1000
    return np.array([[-700.0, -700.0, 50.0],
                     [50.0, 20.0, 200.0],
                     [200.0, -1000.0, 50.0]])


@pytest.fixture
def seg():
    return OARSegmenter()


class TestSegmentHUOnly:
    def test_organ_masks_shape_and_dtype(self, seg):
        masks = seg.segment(_pixels())
        for name in seg.organ_names:
            assert masks[name].shape == (3, 3)
            assert masks[name].dtype == bool

    def test_no_background_by_default(self, seg):
        assert BACKGROUND not in seg.segment(_pixels())

    def test_lung_mask(self, seg):
        m = seg.segment(_pixels())["lung"]
        assert m[0, 0] is np.True_
        assert m[0, 1] is np.True_
        assert m[0, 2] is np.False_

    def test_heart_mask(self, seg):
        m = seg.segment(_pixels())["heart"]
        assert m[0, 2] is np.True_
        assert m[1, 0] is np.True_
        assert m[2, 2] is np.True_

    def test_spinal_cord_mask(self, seg):
        m = seg.segment(_pixels())["spinal_cord"]
        assert m[1, 1] is np.True_

    def test_bone_marrow_mask(self, seg):
        m = seg.segment(_pixels())["bone_marrow"]
        assert m[1, 2] is np.True_
        assert m[2, 0] is np.True_


class TestRegionMask:
    def _region_heart_top_right(self):
        """region للقلب: True فقط بـ (0,2)"""
        r = np.zeros((3, 3), dtype=bool)
        r[0, 2] = True
        return r

    def test_region_restricts_heart(self):
        s = OARSegmenter(region_masks={"heart": self._region_heart_top_right()})
        m = s.segment(_pixels())["heart"]
        # القلب صار بكسل واحد فقط (التقاطع)
        assert m.sum() == 1
        assert m[0, 2] is np.True_
        assert m[1, 0] is np.False_

    def test_region_does_not_affect_other_organs(self):
        s = OARSegmenter(region_masks={"heart": self._region_heart_top_right()})
        m = s.segment(_pixels())["lung"]
        assert m.sum() == 2  # الرئة بلا region → كما هي

    def test_region_wrong_shape_raises(self):
        bad = np.zeros((2, 2), dtype=bool)  # حجم ≠ 3x3
        s = OARSegmenter(region_masks={"heart": bad})
        with pytest.raises(ValueError):
            s.segment(_pixels())

    def test_region_for_unknown_organ_ignored(self):
        # region لعضو مو بالـ ranges → لا يُستخدم ولا يرفع خطأ
        s = OARSegmenter(region_masks={"plasma": np.ones((3, 3), dtype=bool)})
        masks = s.segment(_pixels())
        assert "plasma" not in masks


class TestBackground:
    def test_background_when_enabled(self):
        s = OARSegmenter(include_background=True)
        m = s.segment(_pixels())[BACKGROUND]
        assert m[2, 1] is np.True_  # -1000 خلفية
        assert m.sum() == 1

    def test_all_classified_no_background_pixels(self):
        # مصفوفة كل بكسلاتها ضمن عضو → background = 0
        arr = np.array([[-700.0, 50.0], [20.0, 200.0]])
        s = OARSegmenter(include_background=True)
        assert s.segment(arr)[BACKGROUND].sum() == 0


class TestOrganMap:
    def test_shape_dtype(self, seg):
        om = seg.organ_map(_pixels())
        assert om.shape == (3, 3)
        assert om.dtype == int

    def test_zero_for_unassigned(self, seg):
        om = seg.organ_map(_pixels())
        assert om[2, 1] == 0  # خلفية

    def test_alphabetical_ids(self, seg):
        # bone_marrow=1, heart=2, lung=3, spinal_cord=4
        names = seg.organ_names
        om = seg.organ_map(_pixels())
        assert om[2, 0] == names.index("bone_marrow") + 1
        assert om[0, 0] == names.index("lung") + 1
        assert om[1, 1] == names.index("spinal_cord") + 1

    def test_region_reflected_in_map(self):
        r = np.zeros((3, 3), dtype=bool)
        r[0, 2] = True
        s = OARSegmenter(region_masks={"heart": r})
        om = s.organ_map(_pixels())
        # (1,0) كان heart=2، بس الـ region قطعه → صار 0
        assert om[1, 0] == 0
        assert om[0, 2] == 2


class TestVolumeFraction:
    def test_lung_fraction(self, seg):
        assert seg.volume_fraction(_pixels(), "lung") == pytest.approx(2 / 9)

    def test_background_fraction(self, seg):
        assert seg.volume_fraction(_pixels(), BACKGROUND) == pytest.approx(1 / 9)

    def test_heart_with_region_fraction(self):
        r = np.zeros((3, 3), dtype=bool)
        r[0, 2] = True
        s = OARSegmenter(region_masks={"heart": r})
        assert s.volume_fraction(_pixels(), "heart") == pytest.approx(1 / 9)

    def test_unknown_organ_raises(self, seg):
        with pytest.raises(ValueError):
            seg.volume_fraction(_pixels(), "plasma")


class TestSummary:
    def test_keys_per_organ(self, seg):
        summ = seg.summary(_pixels())
        for name in seg.organ_names:
            assert {"count", "fraction", "mean_hu"} <= set(summ[name])

    def test_counts(self, seg):
        summ = seg.summary(_pixels())
        assert summ["lung"]["count"] == 2
        assert summ["heart"]["count"] == 3
        assert summ["bone_marrow"]["count"] == 2

    def test_mean_hu(self, seg):
        summ = seg.summary(_pixels())
        assert summ["lung"]["mean_hu"] == pytest.approx(-700.0)
        assert summ["heart"]["mean_hu"] == pytest.approx(50.0)

    def test_background_in_summary_only_when_enabled(self):
        s_on = OARSegmenter(include_background=True)
        s_off = OARSegmenter(include_background=False)
        assert BACKGROUND in s_on.summary(_pixels())
        assert BACKGROUND not in s_off.summary(_pixels())

    def test_background_mean_hu(self):
        s = OARSegmenter(include_background=True)
        summ = s.summary(_pixels())
        assert summ[BACKGROUND]["mean_hu"] == pytest.approx(-1000.0)


class TestCustomRanges:
    def test_custom_overrides(self):
        s = OARSegmenter(ranges={"kidney": (20.0, 40.0)})
        m = s.segment(np.array([[30.0, 90.0]]))
        assert "kidney" in m
        assert m["kidney"][0, 0] is np.True_
        assert m["kidney"][0, 1] is np.False_

    def test_invalid_range_raises(self):
        with pytest.raises(ValueError):
            OARSegmenter(ranges={"x": (10.0, 10.0)})

    def test_inverted_range_raises(self):
        with pytest.raises(ValueError):
            OARSegmenter(ranges={"x": (100.0, 10.0)})

    def test_empty_ranges_raises(self):
        with pytest.raises(ValueError):
            OARSegmenter(ranges={})


class TestGuards:
    def test_empty_pixels_raises(self, seg):
        with pytest.raises(ValueError):
            seg.segment(np.array([]))

    def test_accepts_list_input(self, seg):
        m = seg.segment([[-700.0, 50.0]])
        assert m["lung"][0, 0] is np.True_

    def test_default_ranges_loaded(self, seg):
        assert set(seg.organ_names) == set(DEFAULT_OAR_RANGES.keys())
