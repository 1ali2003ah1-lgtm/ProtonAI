"""
ProtonAI - Test Health Economics
"""

import pytest
from cost_effectiveness import qaly, icer, proton_value


class TestQaly:
    def test_simple(self):
        assert qaly(0.8, 10) == pytest.approx(8)

    def test_invalid(self):
        with pytest.raises(ValueError):
            qaly(1.5, 10)


class TestIcer:
    def test_known(self):
        assert icer(10000, 0.5) == pytest.approx(20000)

    def test_no_gain(self):
        with pytest.raises(ValueError):
            icer(1000, 0)


class TestValue:
    def test_effective(self):
        r = proton_value(60000, 50000, 8.0, 7.5)
        assert r["icer"] == pytest.approx(20000)
        assert r["cost_effective"] is True

    def test_not_effective(self):
        r = proton_value(110000, 50000, 8.0, 7.5)
        assert r["cost_effective"] is False

    def test_no_gain(self):
        r = proton_value(60000, 50000, 7.0, 7.5)
        assert r["cost_effective"] is False
