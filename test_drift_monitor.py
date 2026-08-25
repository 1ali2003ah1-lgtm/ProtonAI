"""
ProtonAI - Test Drift Monitor
"""

import pytest
from drift_monitor import DriftMonitor, psi


class TestStatus:
    def test_green_stable(self):
        d = DriftMonitor(0.9, 0.05)
        for v in [0.9, 0.91, 0.89]:
            d.update(v)
        assert d.status() == "GREEN"

    def test_red_shift(self):
        d = DriftMonitor(0.9, 0.05)
        for _ in range(3):
            d.update(1.1)   # z = 4
        assert d.status() == "RED"

    def test_amber_shift(self):
        d = DriftMonitor(0.9, 0.05)
        for _ in range(3):
            d.update(1.025)  # z = 2.5
        assert d.status() == "AMBER"

    def test_invalid_std(self):
        with pytest.raises(ValueError):
            DriftMonitor(0.9, 0)


class TestPsi:
    def test_identical_zero(self):
        p = [0.5, 0.3, 0.2]
        assert psi(p, p) == pytest.approx(0.0, abs=1e-6)

    def test_shift_positive(self):
        assert psi([0.5, 0.5], [0.8, 0.2]) > 0.1
