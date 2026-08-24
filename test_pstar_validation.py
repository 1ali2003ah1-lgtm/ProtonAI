"""
ProtonAI - Test PSTAR Validation
"""

from pstar_validation import validate, our_range_cm, PSTAR_WATER_CM


class TestPstar:
    def test_within_tolerance(self):
        r = validate()
        assert r["within_tolerance"] is True

    def test_max_rel_small(self):
        r = validate()
        assert r["max_rel_diff"] < 0.03

    def test_rows_cover_all(self):
        r = validate()
        assert len(r["rows"]) == len(PSTAR_WATER_CM)

    def test_monotonic(self):
        es = sorted(PSTAR_WATER_CM)
        ranges = [our_range_cm(e) for e in es]
        assert all(a < b for a, b in zip(ranges, ranges[1:]))
