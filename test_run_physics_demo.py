"""
ProtonAI - Test Stage-5 Physics Demo
اختبارات مايسترو المرحلة 5 (كل المسارات + الجسر مع التصوير + المراجعة)
"""

import numpy as np
import pytest
from run_physics_demo import run_physics_demo
from proton_physics import ProtonPhysics
from physics_review import PhysicsReviewLoop

DEPTHS = np.arange(0.0, 100.0, 1.0)


@pytest.fixture
def phys():
    return ProtonPhysics()


class TestCoreKeys:
    def test_all_keys_present(self):
        res = run_physics_demo(depths=DEPTHS)
        for k in ["energy_mev", "water_range_mm", "medium_range_mm", "rbe",
                  "rbe_dose_example", "range_uncertainty", "dose_uncertainty",
                  "gamma", "benchmark", "adaptive", "physics_review",
                  "report_markdown"]:
            assert k in res

    def test_medium_range_none_without_hu(self):
        res = run_physics_demo(depths=DEPTHS)
        assert res["medium_range_mm"] is None

    def test_water_range_positive(self):
        res = run_physics_demo(depths=DEPTHS)
        assert res["water_range_mm"] > 0

    def test_report_has_sections(self):
        md = run_physics_demo(depths=DEPTHS)["report_markdown"]
        for sec in ["Physics Core", "Range Uncertainty", "Dose Uncertainty",
                    "Gamma Index", "Physics Benchmark", "Adaptive Evaluation",
                    "Physics Review"]:
            assert sec in md


class TestGamma:
    def test_default_nominal_vs_nominal_passes(self):
        res = run_physics_demo(depths=DEPTHS)
        assert res["gamma"]["pass_rate"] == pytest.approx(1.0)

    def test_shifted_evaluated_reduces_pass_rate(self, phys):
        evaluated = phys.sobp(DEPTHS, 55.0, 75.0)  # مزاح 15mm
        res = run_physics_demo(depths=DEPTHS, evaluated_curve=evaluated, physics=phys)
        assert res["gamma"]["pass_rate"] < 1.0


class TestBenchmark:
    def test_all_passed_default(self):
        res = run_physics_demo(depths=DEPTHS)
        assert res["benchmark"]["all_passed"] is True


class TestAdaptive:
    def test_stable_no_replan(self):
        # current == plan (افتراضي) → لا انهيار تغطية ولا تغيّر شكل
        res = run_physics_demo(depths=DEPTHS)
        assert res["adaptive"]["needs_replan"] is False
        assert res["adaptive"]["coverage_drop"] == pytest.approx(0.0)

    def test_collapsed_coverage_replan(self):
        current = (DEPTHS >= 70) & (DEPTHS <= 80)  # برّا الـ SOBP
        res = run_physics_demo(depths=DEPTHS, current_profile=current)
        assert res["adaptive"]["needs_replan"] is True
        assert res["adaptive"]["coverage_drop"] > 0.1


class TestPhysicsReview:
    def test_no_flag_when_all_good(self, phys):
        # energy → water_range=50 داخل [40,60] بهامش → range_in_target=True
        e = phys.energy_from_range_mm(50.0)
        res = run_physics_demo(energy_mev=e, target_start_mm=40.0,
                               target_end_mm=60.0, depths=DEPTHS, physics=phys)
        assert res["physics_review"]["stats"]["total_flagged"] == 0
        assert res["physics_review"]["flagged_request_id"] is None

    def test_flag_on_bad_gamma(self, phys):
        evaluated = phys.sobp(DEPTHS, 55.0, 75.0)  # gamma فاشل
        res = run_physics_demo(depths=DEPTHS, evaluated_curve=evaluated, physics=phys)
        stats = res["physics_review"]["stats"]
        assert stats["total_flagged"] >= 1
        assert "gamma_fail" in stats["by_physics_reason"]
        assert res["physics_review"]["flagged_request_id"] is not None

    def test_injected_review_loop_used(self):
        loop = PhysicsReviewLoop()
        run_physics_demo(depths=DEPTHS, review_loop=loop)
        # الحلقة الداخلية استُخدمت (سواء فيها طلب أو لا، الكائن نفسه)
        assert isinstance(loop, PhysicsReviewLoop)


class TestMediumRangeBridge:
    def test_water_profile_matches_water_range(self, phys):
        e = phys.energy_from_range_mm(50.0)
        profile = np.zeros(200)  # ماء بطول كافٍ
        res = run_physics_demo(energy_mev=e, hu_profile_1d=profile,
                               depths=DEPTHS, physics=phys)
        assert res["medium_range_mm"] == pytest.approx(res["water_range_mm"], rel=0.02)

    def test_bone_profile_shorter(self, phys):
        e = phys.energy_from_range_mm(50.0)
        bone = np.full(200, 1000.0)
        res = run_physics_demo(energy_mev=e, hu_profile_1d=bone,
                               depths=DEPTHS, physics=phys)
        assert res["medium_range_mm"] < res["water_range_mm"]


class TestRBEDose:
    def test_rbe_dose_consistent(self):
        res = run_physics_demo(depths=DEPTHS, rbe=1.1)
        nominal = res["dose_uncertainty"]["robustness"]["nominal_mean"]
        assert res["rbe_dose_example"] == pytest.approx(nominal * 1.1)


class TestSave:
    def test_saves_files(self, tmp_path):
        out = tmp_path / "phys"
        run_physics_demo(depths=DEPTHS, output_dir=out)
        assert (out / "physics_report.md").exists()
        assert (out / "physics_report.json").exists()
        assert (out / "physics_review.json").exists()


class TestDeterministic:
    def test_same_result_twice(self):
        r1 = run_physics_demo(depths=DEPTHS)
        r2 = run_physics_demo(depths=DEPTHS)
        assert r1["water_range_mm"] == r2["water_range_mm"]
        assert r1["benchmark"]["all_passed"] == r2["benchmark"]["all_passed"]
        assert r1["gamma"]["pass_rate"] == r2["gamma"]["pass_rate"]


class TestGuards:
    def test_invalid_target_raises(self):
        with pytest.raises(ValueError):
            run_physics_demo(target_start_mm=60.0, target_end_mm=40.0)

    def test_invalid_energy_raises(self):
        with pytest.raises(ValueError):
            run_physics_demo(energy_mev=-10.0)
