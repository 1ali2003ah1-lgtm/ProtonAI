"""
ProtonAI - Test Radiobiology
"""

import pytest
from radiobiology import variable_rbe, tcp, ntcp_lkb


class TestRbe:
    def test_baseline(self):
        assert variable_rbe(2, 0) == pytest.approx(1.0)

    def test_increases_with_let(self):
        assert variable_rbe(2, 5) > variable_rbe(2, 2)

    def test_decreases_with_dose(self):
        assert variable_rbe(8, 5) < variable_rbe(2, 5)


class TestTcpNtcp:
    def test_tcp_half(self):
        assert tcp(50, 50) == pytest.approx(0.5)

    def test_tcp_monotonic(self):
        assert tcp(70, 50) > tcp(60, 50)

    def test_ntcp_half(self):
        assert ntcp_lkb(50, 50) == pytest.approx(0.5)

    def test_ntcp_monotonic(self):
        assert ntcp_lkb(70, 50) > ntcp_lkb(60, 50)
