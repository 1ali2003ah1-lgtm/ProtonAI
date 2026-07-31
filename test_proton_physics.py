"""
ProtonAI - Test Proton Physics Engine
اختبارات المحرك الفيزيائي (خصائص فيزيائية نوعية + دقة CSDA التقريبية)
"""

import numpy as np
import pytest
from proton_physics import ProtonPhysics


@pytest.fixture
def pp():
    return ProtonPhysics()


class TestWaterRange:
    def test_monotonic_with_energy(self, pp):
        r100 = pp.water_range_mm(100)
        r150 = pp.water_range_mm(150)
        r200 = pp.water_range_mm(200)
        assert r100 < r150 < r200

    def test_csda_accuracy_100mev(self, pp):
        # المرجع ~77mm للبروتون 100MeV
        assert 70.0 < pp.water_range_mm(100) < 85.0

    def test_csda_accuracy_150mev(self, pp):
        # المرجع ~158mm
        assert 145.0 < pp.water_range_mm(150) < 170.0

    def test_positive_only(self, pp):
        assert pp.water_range_mm(50) > 0

    def test_invalid_energy_raises(self, pp):
        with pytest.raises(ValueError):
            pp.water_range_mm(0)
        with pytest.raises(ValueError):
            pp.water_range_mm(-10)


class TestEnergyFromRange:
    def test_roundtrip(self, pp):
        for e in (50.0, 100.0, 150.0, 200.0):
            assert pp.energy_from_range_mm(pp.water_range_mm(e)) == pytest.approx(e)

    def test_monotonic(self, pp):
        assert pp.energy_from_range_mm(50) < pp.energy_from_range_mm(150)

    def test_invalid_raises(self, pp):
        with pytest.raises(ValueError):
            pp.energy_from_range_mm(0)


class TestRSP:
    def test_water_is_one(self, pp):
        assert pp.rsp_from_hu(0) == pytest.approx(1.0)

    def test_bone_greater_than_one(self, pp):
        assert pp.rsp_from_hu(1000) > 1.0

    def test_lung_less_than_one(self, pp):
        assert pp.rsp_from_hu(-700) < 1.0

    def test_floor_applied(self, pp):
        # -1000 → 1 + 0.001*(-1000) = 0 → يُرفع للحد الأدنى
        assert pp.rsp_from_hu(-1000) >= pp.rsp_floor
        assert pp.rsp_from_hu(-1000) < 1.0

    def test_bone_value_reasonable(self, pp):
        # +1000 → 1.8 (ضمن النطاق الفيزيائي المعقول للعظم)
        assert pp.rsp_from_hu(1000) == pytest.approx(1.8)


class TestRangeInMedium:
    def test_water_profile_equals_water_range(self, pp):
        # ملف HU=0 (ماء) بطول كافٍ → المدى ≈ المدى المائي
        e = 100.0
        profile = np.zeros(200)  # 200mm ماء > range(~77)
        r = pp.proton_range_in_medium(e, profile, voxel_mm=1.0)
        assert r == pytest.approx(pp.water_range_mm(e), rel=0.02)

    def test_denser_medium_shorter_range(self, pp):
        e = 100.0
        bone = np.full(100, 1000.0)  # عظم rsp=1.8
        assert pp.proton_range_in_medium(e, bone, 1.0) < pp.water_range_mm(e)

    def test_lung_longer_range(self, pp):
        e = 100.0
        lung = np.full(400, -700.0)  # رئة rsp=0.3 → مدى أطول بكثير
        assert pp.proton_range_in_medium(e, lung, 1.0) > pp.water_range_mm(e)

    def test_empty_raises(self, pp):
        with pytest.raises(ValueError):
            pp.proton_range_in_medium(100, np.array([]))

    def test_invalid_voxel_raises(self, pp):
        with pytest.raises(ValueError):
            pp.proton_range_in_medium(100, np.zeros(10), voxel_mm=0)

    def test_proton_exits_profile(self, pp):
        # ملف قصير جداً → يرجع طول الملف الكامل
        r = pp.proton_range_in_medium(200, np.zeros(5), voxel_mm=1.0)
        assert r == pytest.approx(5.0)


class TestBraggPeak:
    def test_peak_near_range(self, pp):
        depths = np.arange(0, 100, 1.0)
        curve = pp.bragg_peak(depths, range_mm=50.0)
        argmax = depths[int(np.argmax(curve))]
        assert abs(argmax - 50.0) < 3.0

    def test_falls_off_after_range(self, pp):
        depths = np.arange(0, 100, 1.0)
        curve = pp.bragg_peak(depths, range_mm=50.0)
        assert curve[70] < 0.05 * curve.max()  # بعد المدى بـ20mm ≈ صفر

    def test_entrance_lower_than_peak(self, pp):
        depths = np.arange(0, 100, 1.0)
        curve = pp.bragg_peak(depths, range_mm=50.0)
        assert curve[15] < curve[int(np.argmax(curve))]

    def test_invalid_range_raises(self, pp):
        with pytest.raises(ValueError):
            pp.bragg_peak(np.arange(10), range_mm=0)

    def test_invalid_sigma_raises(self, pp):
        with pytest.raises(ValueError):
            pp.bragg_peak(np.arange(10), range_mm=50, sigma_mm=0)


class TestSOBP:
    def test_wider_than_single_peak(self, pp):
        depths = np.arange(0, 150, 1.0)
        single = pp.bragg_peak(depths, range_mm=50.0)
        sobp = pp.sobp(depths, 30.0, 70.0, n_peaks=7)
        w_single = (single > 0.4 * single.max()).sum()
        w_sobp = (sobp > 0.4 * sobp.max()).sum()
        assert w_sobp > w_single + 10  # SOBP أوسع بكثير

    def test_target_region_has_dose(self, pp):
        depths = np.arange(0, 150, 1.0)
        sobp = pp.sobp(depths, 30.0, 70.0, n_peaks=7)
        target = sobp[(depths >= 30) & (depths <= 70)]
        assert target.mean() >= 0.4 * sobp.max()

    def test_falls_off_after_target(self, pp):
        depths = np.arange(0, 150, 1.0)
        sobp = pp.sobp(depths, 30.0, 70.0, n_peaks=7)
        after = sobp[depths > 85]
        target = sobp[(depths >= 30) & (depths <= 70)]
        assert after.mean() < 0.3 * target.mean()

    def test_invalid_n_peaks_raises(self, pp):
        with pytest.raises(ValueError):
            pp.sobp(np.arange(100), 10, 20, n_peaks=0)

    def test_invalid_target_raises(self, pp):
        with pytest.raises(ValueError):
            pp.sobp(np.arange(100), 20, 10)

    def test_weights_length_mismatch_raises(self, pp):
        with pytest.raises(ValueError):
            pp.sobp(np.arange(100), 10, 20, n_peaks=3, weights=[1, 2])


class TestRBEDose:
    def test_scalar_default_rbe(self, pp):
        assert pp.rbe_dose(2.0) == pytest.approx(2.2)

    def test_scalar_custom_rbe(self, pp):
        assert pp.rbe_dose(2.0, rbe=1.0) == pytest.approx(2.0)

    def test_array(self, pp):
        out = pp.rbe_dose(np.array([1.0, 2.0]), rbe=1.1)
        assert np.allclose(out, [1.1, 2.2])

    def test_invalid_rbe_raises(self, pp):
        with pytest.raises(ValueError):
            pp.rbe_dose(1.0, rbe=0)


class TestGuards:
    def test_invalid_range_a(self):
        with pytest.raises(ValueError):
            ProtonPhysics(range_a=0)

    def test_invalid_range_p(self):
        with pytest.raises(ValueError):
            ProtonPhysics(range_p=0)

    def test_invalid_rsp_floor(self):
        with pytest.raises(ValueError):
            ProtonPhysics(rsp_floor=0)

    def test_invalid_default_rbe(self):
        with pytest.raises(ValueError):
            ProtonPhysics(default_rbe=0)
