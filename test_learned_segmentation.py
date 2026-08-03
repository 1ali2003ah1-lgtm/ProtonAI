"""
ProtonAI - Test Learned Segmentation
اختبارات التقسيم المتعلّم (تدريب + Dice + حفظ/تحميل + حراس)
"""

import numpy as np
import pytest
from learned_segmentation import LearnedSegmenter


def _synthetic():
    """صورة HU: خلفية منخفضة + ورم عالي بـ [5:10,5:10]"""
    rng = np.random.RandomState(0)
    hu = rng.normal(-200, 50, (20, 20))          # خلفية
    labels = np.zeros((20, 20), dtype=int)
    labels[5:10, 5:10] = 1
    # فهرسة شرائح (تقبل 2D) بدل القناع المنطقي (1D فقط)
    hu[5:10, 5:10] = rng.normal(300, 50, (5, 5))  # ورم عالي HU
    return hu, labels


def _dice(a, b):
    a, b = a.astype(bool), b.astype(bool)
    return 2 * (a & b).sum() / (a.sum() + b.sum())


@pytest.fixture
def seg():
    return LearnedSegmenter()


class TestFitSegment:
    def test_learns_and_recovers(self, seg):
        hu, labels = _synthetic()
        seg.fit(hu, labels)
        mask = seg.segment(hu)
        assert _dice(mask, labels) > 0.8

    def test_mask_bool_same_shape(self, seg):
        hu, labels = _synthetic()
        seg.fit(hu, labels)
        mask = seg.segment(hu)
        assert mask.shape == hu.shape
        assert mask.dtype == bool

    def test_unfitted_raises(self, seg):
        hu, _ = _synthetic()
        with pytest.raises(ValueError):
            seg.segment(hu)


class TestSaveLoad:
    def test_roundtrip_same_predictions(self, seg, tmp_path):
        hu, labels = _synthetic()
        seg.fit(hu, labels)
        p = tmp_path / "seg.pkl"
        seg.save(p)
        loaded = LearnedSegmenter.load(p)
        assert loaded.fitted is True
        assert np.array_equal(loaded.segment(hu), seg.segment(hu))

    def test_loaded_can_segment_without_refit(self, seg, tmp_path):
        hu, labels = _synthetic()
        seg.fit(hu, labels)
        p = tmp_path / "seg.pkl"
        seg.save(p)
        loaded = LearnedSegmenter.load(p)
        assert _dice(loaded.segment(hu), labels) > 0.8


class TestGuards:
    def test_shape_mismatch_raises(self, seg):
        hu, labels = _synthetic()
        with pytest.raises(ValueError):
            seg.fit(hu, labels[:5, :])

    def test_empty_raises(self, seg):
        with pytest.raises(ValueError):
            seg.fit(np.array([]), np.array([]))

    def test_invalid_estimators_raises(self):
        with pytest.raises(ValueError):
            LearnedSegmenter(n_estimators=0)
