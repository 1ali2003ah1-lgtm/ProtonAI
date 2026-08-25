"""
ProtonAI - Test FMEA
"""

from fmea import FAILURE_MODES, rpn, table, high_risk


class TestRpn:
    def test_computation(self):
        fm = FAILURE_MODES[0]
        assert rpn(fm) == 9 * 3 * 4

    def test_table_length(self):
        assert len(table()) == len(FAILURE_MODES)


class TestHighRisk:
    def test_flags_top(self):
        ids = [t["id"] for t in high_risk()]
        assert "FM-02" in ids and "FM-10" in ids

    def test_audit_low(self):
        ids = [t["id"] for t in high_risk()]
        assert "FM-07" not in ids
