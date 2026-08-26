"""
ProtonAI - Test Phantom QA
"""

import pytest
from qa_phantom import point_diff, phantom_qa


class TestDiff:
    def test_zero(self):
        assert point_diff(2, 2) == 0

    def test_pct(self):
        assert point_diff(103, 100) == pytest.approx(3)

    def test_zero_planned(self):
        with pytest.raises(ValueError):
            point_diff(1, 0)


class TestQa:
    def test_perfect(self):
        r = phantom_qa([2, 2], [2, 2])
        assert r["pass_rate"] == 1.0 and r["status"] == "GREEN"

    def test_red(self):
        r = phantom_qa([2, 3], [2, 2])  # 50% خارج
        assert r["status"] == "RED"

    def test_mismatch(self):
        with pytest.raises(ValueError):
            phantom_qa([1], [1, 2])
