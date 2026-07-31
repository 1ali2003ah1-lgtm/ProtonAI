"""
ProtonAI - Test Pretrained Segmenter
اختبارات واجهة النموذج الجاهز + الجسر إلى OARSegmenter
"""

import numpy as np
import pytest
from pretrained_segmenter import PretrainedSegmenter, RuleBasedDemoModel
from oar_segmenter import OARSegmenter


def _pixels():
    """4x4 تغطي النطاقات (lung/heart/spinal/bone + خلفية)"""
    return np.array([
        [-700.0, -700.0, 50.0, 50.0],
        [-700.0, 20.0, 200.0, 50.0],
        [50.0, 20.0, 200.0, -1000.0],
        [200.0, -1000.0, 50.0, 20.0],
    ])


@pytest.fixture
def demo():
    return PretrainedSegmenter()


class TestDemoModel:
    def test_is_real_false_by_default(self, demo):
        assert demo.is_real_model is False

    def test_predict_keys_match_ranges(self, demo):
        masks = demo.predict(_pixels())
        assert set(masks.keys()) == set(demo.ranges.keys())

    def test_predict_masks_bool_and_shape(self, demo):
        for m in demo.predict(_pixels()).values():
            assert m.dtype == bool
            assert m.shape == (4, 4)

    def test_region_masks_subset_of_ranges(self, demo):
        regs = demo.region_masks(_pixels())
        # الـ demo يعرف heart + spinal_cord فقط من الـ ranges الافتراضية
        assert set(regs.keys()) <= set(demo.ranges.keys())
        assert "heart" in regs and "spinal_cord" in regs

    def test_region_masks_bool_and_shape(self, demo):
        for m in demo.region_masks(_pixels()).values():
            assert m.dtype == bool
            assert m.shape == (4, 4)

    def test_3d_raises(self, demo):
        with pytest.raises(ValueError):
            demo.predict(np.zeros((2, 4, 4)))

    def test_empty_raises(self, demo):
        with pytest.raises(ValueError):
            demo.predict(np.array([]))

    def test_heart_restricted_to_left_middle(self, demo):
        # قلب = HU(30..80) ∩ rows[1:3],cols[0:2]
        m = demo.predict(_pixels())["heart"]
        # (0,2)=50 بس خارج المنطقة (row 0) → False
        assert m[0, 2] is np.False_
        # (2,0)=50 وداخل المنطقة (rows 1:3, cols 0:2) → True
        assert m[2, 0] is np.True_
        # (1,0)=-700 (رئة) مو قلب حتى لو داخل المنطقة → False
        assert m[1, 0] is np.False_

    def test_lung_uses_full_region(self, demo):
        # الرئة بلا region بالـ demo → كل بكسل -700 يُلتقط
        m = demo.predict(_pixels())["lung"]
        assert m[0, 0] is np.True_
        assert m[1, 0] is np.True_


class TestInjectedModel:
    def test_is_real_true_when_injected(self):
        class FakeModel:
            def predict(self, px):
                return {"heart": np.ones(px.shape, dtype=bool)}
            def region_masks(self, px):
                return {"heart": np.ones(px.shape, dtype=bool)}
        seg = PretrainedSegmenter(model=FakeModel())
        assert seg.is_real_model is True

    def test_injected_predict_passthrough(self):
        marker = np.array([[True, False], [False, True]])
        class FakeModel:
            def predict(self, px):
                return {"heart": marker}
            def region_masks(self, px):
                return {}
        seg = PretrainedSegmenter(model=FakeModel())
        out = seg.predict(np.zeros((2, 2)))
        assert np.array_equal(out["heart"], marker)


class TestBridgeToOAR:
    def test_build_returns_oar_segmenter(self, demo):
        oar = demo.build_oar_segmenter(_pixels())
        assert isinstance(oar, OARSegmenter)

    def test_bridge_equals_predict(self, demo):
        """الجسر: oar.segment(px)[name] == demo.predict(px)[name] لكل عضو"""
        px = _pixels()
        oar = demo.build_oar_segmenter(px)
        pred = demo.predict(px)
        for name in demo.ranges:
            assert np.array_equal(oar.segment(px)[name], pred[name]), name

    def test_bridge_with_background(self, demo):
        px = _pixels()
        oar = demo.build_oar_segmenter(px, include_background=True)
        assert "background" in oar.segment(px)

    def test_bridge_custom_ranges(self):
        custom = {"kidney": (20.0, 40.0)}
        seg = PretrainedSegmenter(ranges=custom)
        px = np.array([[30.0, 90.0]])
        oar = seg.build_oar_segmenter(px)
        # kidney مو بالـ demo regions → يُفصل بالـ HU فقط، ومتطابق
        assert np.array_equal(oar.segment(px)["kidney"], seg.predict(px)["kidney"])


class TestCustomRanges:
    def test_demo_uses_custom_ranges(self):
        seg = PretrainedSegmenter(ranges={"heart": (0.0, 100.0)})
        masks = seg.predict(_pixels())
        assert set(masks.keys()) == {"heart"}
