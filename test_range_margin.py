"""
ProtonAI - Test Range Margin
"""

import math
from range_margin import components, total_uncertainty, suggested_margin


class TestComponents:
    def test_calibration_scales(self):
        c = components(100, rsp_unc=0.03)
        assert c["calibration"] == 3.0

    def test_density_scales(self):
        c = components(100, density_pct=0.03)
        assert c["density"] == 3.0


class TestTotal:
    def test_bounds(self):
        t = total_uncertainty(100)
        c = components(100)
        assert t >= max(c.values())
        assert t <= sum(c.values())

    def test_increases_with_range(self):
        assert total_uncertainty(200) > total_uncertainty(100)


class TestMargin:
    def test_k2(self):
        m = suggested_margin(100)
        assert m >= 2 * total_uncertainty(100) - 0.5

    def test_half_rounding(self):
        m = suggested_margin(100)
        assert (m * 2) == int(m * 2)

    def test_higher_unc_higher_margin(self):
        assert suggested_margin(100, rsp_unc=0.06) > \
               suggested_margin(100, rsp_unc=0.03)
