"""
ProtonAI - Test Torch Segmenter
تُتخطى تلقائياً على CI بدون torch؛ تشتغل على الجهاز بعد pip install torch
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")  # تخطٍّ آمن على CI
from torch_segmenter import TorchSegmenter, TORCH_AVAILABLE


def _synthetic(seed=0):
    rng = np.random.RandomState(seed)
    hu = rng.normal(-200, 50, (20, 20))
    labels = np.zeros((20, 20), dtype=int)
    labels[5:10, 5:10] = 1
    hu[5:10, 5:10] = rng.normal(300, 50, (5, 5))
    return hu, labels


def _dice(a, b):
    a, b = a.astype(bool), b.astype(bool)
    return 2 * (a & b).sum() / (a.sum() + b.sum())


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch غير مثبت")
class TestTorchSegmenter:
    def test_available(self):
        assert TORCH_AVAILABLE is True

    def test_learns_spatial(self):
        hu, labels = _synthetic()
        seg = TorchSegmenter().fit(hu, labels, epochs=80)
        assert _dice(seg.segment(hu), labels) > 0.7

    def test_mask_bool_shape(self):
        hu, labels = _synthetic()
        seg = TorchSegmenter().fit(hu, labels, epochs=20)
        m = seg.segment(hu)
        assert m.shape == hu.shape
        assert m.dtype == bool

    def test_unfitted_raises(self):
        hu, _ = _synthetic()
        with pytest.raises(ValueError):
            TorchSegmenter().segment(hu)

    def test_save_load(self, tmp_path):
        hu, labels = _synthetic()
        seg = TorchSegmenter().fit(hu, labels, epochs=40)
        p = tmp_path / "cnn.pt"
        seg.save(p)
        loaded = TorchSegmenter().load(p)
        assert np.array_equal(loaded.segment(hu), seg.segment(hu))
