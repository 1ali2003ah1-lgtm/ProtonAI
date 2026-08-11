"""
ProtonAI - Test Harmonization
"""

import numpy as np
import pytest
from harmonization import target_shape, normalize_hu, harmonize


class TestTargetShape:
    def test_upsample(self):
        assert target_shape((100,), (2.0,), (1.0,)) == (200,)

    def test_downsample(self):
        assert target_shape((100,), (1.0,), (2.0,)) == (50,)

    def test_3d(self):
        assert target_shape((10, 20, 30), (1, 1, 2), (1, 1, 1)) == (10, 20, 60)


class TestNormalize:
    def test_water_half(self):
        assert normalize_hu(np.array([0.0]))[0] == pytest.approx(0.5)

    def test_bounds(self):
        assert normalize_hu(np.array([-1000.0]))[0] == 0.0
        assert normalize_hu(np.array([1000.0]))[0] == 1.0

    def test_clip(self):
        v = normalize_hu(np.array([5000.0]))[0]
        assert v == 1.0


class TestHarmonize:
    def test_site_metadata(self):
        r = harmonize(np.zeros((4, 4)), (1, 1), "CT-THIQAR-01")
        assert r["site"] == "CT-THIQAR-01"

    def test_image_in_range(self):
        r = harmonize(np.random.default_rng(0).uniform(-1200, 1200, (6, 6)),
                      (1, 1), "S1")
        assert r["image"].min() >= 0.0 and r["image"].max() <= 1.0
