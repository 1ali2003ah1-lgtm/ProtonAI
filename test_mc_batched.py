"""
ProtonAI - Test Batched Monte Carlo
اختبارات MC الدفعات (مطابقة + دفعات متعددة + مدى + حراس)
"""

import numpy as np
import pytest
from mc_batched import BatchedMonteCarlo
from monte_carlo_physics import MonteCarloPhysics


@pytest.fixture
def bmc():
    return BatchedMonteCarlo(seed=42, chunk_size=100)


class TestEquivalence:
    def test_single_chunk_matches_stage9(self):
        depths = np.arange(0, 100, 1.0)
        single = MonteCarloPhysics().simulate_depth_dose(100.0, 500, depths, seed=7)
        big_chunk = BatchedMonteCarlo(chunk_size=10_000_000)
        batched = big_chunk.simulate_depth_dose(100.0, 500, depths, seed=7)
        assert np.allclose(single, batched)

    def test_multi_chunk_close_to_full(self):
        depths = np.arange(0, 100, 1.0)
        full = MonteCarloPhysics().simulate_depth_dose(100.0, 2000, depths, seed=1)
        batched = BatchedMonteCarlo(chunk_size=100).simulate_depth_dose(
            100.0, 2000, depths, seed=1)
        assert np.abs(full - batched).max() < 0.1 * full.max()


class TestBatched:
    def test_shape_and_positive(self, bmc):
        depths = np.arange(0, 100, 1.0)
        dose = bmc.simulate_depth_dose(100.0, 500, depths)
        assert dose.shape == depths.shape
        assert dose.sum() > 0

    def test_multiple_chunks_run(self, bmc):
        # n=500 وchunk=100 → 5 دفعات، يشتغل بدون انفجار
        depths = np.arange(0, 100, 1.0)
        dose = bmc.simulate_depth_dose(100.0, 500, depths, seed=3)
        assert np.all(dose >= 0)

    def test_estimate_range_close(self, bmc):
        R = bmc.physics.water_range_mm(100.0)
        est = bmc.estimate_range(100.0, 2000, seed=42)
        assert abs(est - R) / R < 0.06


class TestGuards:
    def test_invalid_chunk_raises(self):
        with pytest.raises(ValueError):
            BatchedMonteCarlo(chunk_size=0)

    def test_invalid_energy_raises(self, bmc):
        with pytest.raises(ValueError):
            bmc.simulate_depth_dose(-5.0)

    def test_invalid_n_raises(self, bmc):
        with pytest.raises(ValueError):
            bmc.simulate_depth_dose(100.0, n_histories=0)


class TestInheritance:
    def test_is_monte_carlo(self, bmc):
        assert isinstance(bmc, MonteCarloPhysics)

    def test_statistical_error_inherited(self):
        assert BatchedMonteCarlo.relative_statistical_error(100) == pytest.approx(0.1)
