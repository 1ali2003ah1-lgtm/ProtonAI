"""
ProtonAI - Test HU→RSP Stoichiometric Calibration
"""

import numpy as np
import pytest
from hu_rsp_calibration import StoichiometricRSP, TISSUE_RSP_UNC


@pytest.fixture
def cal():
    return StoichiometricRSP()


class TestConversion:
    def test_water_is_one(self, cal):
        assert cal.hu_to_rsp(0) == pytest.approx(1.0, abs=1e-6)

    def test_air_near_zero(self, cal):
        assert cal.hu_to_rsp(-1000) == pytest.approx(0.001, abs=1e-6)

    def test_monotonic(self, cal):
        r = cal.hu_to_rsp([-1000, -500, 0, 100, 1000])
        assert np.all(np.diff(r) >= 0)

    def test_array_support(self, cal):
        r = cal.hu_to_rsp([0, 100])
        assert r.shape == (2,)
        assert r[1] > r[0]


class TestUncertainty:
    def test_positive(self, cal):
        for t in TISSUE_RSP_UNC:
            assert cal.rsp_uncertainty(t) > 0

    def test_bone_higher_than_water(self, cal):
        assert cal.rsp_uncertainty("bone") > cal.rsp_uncertainty("water")

    def test_unknown_raises(self, cal):
        with pytest.raises(KeyError):
            cal.rsp_uncertainty("unknown_tissue")


class TestPerScanner:
    def test_scanner_id(self):
        c = StoichiometricRSP(scanner_id="CT-THIQAR-01")
        assert c.scanner_id == "CT-THIQAR-01"

    def test_custom_curve(self):
        c = StoichiometricRSP(points=[(-1000, 0.0), (0, 1.0), (1000, 2.0)])
        assert c.hu_to_rsp(500) == pytest.approx(1.5, abs=1e-6)
