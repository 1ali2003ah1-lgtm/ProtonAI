"""
ProtonAI - Test Segmentation Training Scaffold
"""

import numpy as np
import pytest
import segmentation_train
from segmentation_train import make_synthetic_volume


class TestSynthetic:
    def test_shapes(self):
        img, mask = make_synthetic_volume()
        assert img.shape == mask.shape == (16, 16, 16)

    def test_mask_nontrivial(self):
        _, mask = make_synthetic_volume()
        assert 0 < mask.sum() < mask.size

    def test_tumor_brighter(self):
        img, mask = make_synthetic_volume()
        assert img[mask].mean() > img[~mask].mean()


class TestGuard:
    def test_train_requires_torch(self, monkeypatch):
        monkeypatch.setattr(segmentation_train, "TORCH_AVAILABLE", False)
        with pytest.raises(RuntimeError):
            segmentation_train.train([np.zeros((4, 4, 4))], [np.zeros((4, 4, 4), bool)])
