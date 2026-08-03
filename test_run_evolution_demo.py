"""
ProtonAI - Test Stage-9 Evolution Demo
اختبارات مايسترو التطور (MC + عدم يقين + تقسيم + FHIR حي + تقرير)
"""

import pytest
from run_evolution_demo import run_evolution_demo, _synthetic, _dice


@pytest.fixture
def res():
    return run_evolution_demo()


class TestCoreKeys:
    def test_all_keys(self, res):
        for k in ["physics_mc", "uncertainty", "n_histories_target",
                  "segmentation_dice", "fhir", "report_markdown"]:
            assert k in res


class TestPhysicsMC:
    def test_rel_diff_small(self, res):
        assert res["physics_mc"]["rel_diff"] < 0.06

    def test_ranges_positive(self, res):
        assert res["physics_mc"]["mc_range"] > 0
        assert res["physics_mc"]["analytic_range"] > 0


class TestUncertainty:
    def test_combined_dominates(self, res):
        c = res["uncertainty"]["components"]
        assert c["combined"] >= c["clinical"]

    def test_n_target_achieves_goal(self, res):
        n = res["n_histories_target"]
        assert 1.0 / (n ** 0.5) <= 0.01


class TestSegmentation:
    def test_dice_high(self, res):
        assert res["segmentation_dice"] > 0.8

    def test_dice_helper(self):
        import numpy as np
        a = np.array([[1, 0], [1, 0]])
        b = np.array([[1, 0], [0, 0]])
        assert _dice(a, b) == pytest.approx(2 * 1 / (2 + 1))


class TestFHIR:
    def test_post_created(self, res):
        assert res["fhir"]["status"] == 201

    def test_reachable(self, res):
        assert res["fhir"]["reachable"] is True


class TestReport:
    def test_has_sections(self, res):
        md = res["report_markdown"]
        assert "فيزياء Monte Carlo" in md
        assert "عدم اليقين المدموج" in md
        assert "التقسيم المتعلّم" in md
        assert "التكامل الحي" in md
        assert "القيود" in md  # القيود الصادقة الافتراضية


class TestSave:
    def test_saves_report(self, tmp_path):
        out = tmp_path / "evo"
        run_evolution_demo(output_dir=out)
        assert (out / "evolution_report.md").exists()

    def test_no_save_no_crash(self):
        r = run_evolution_demo()
        assert r["fhir"]["reachable"] is True


class TestDeterministic:
    def test_same_seed_same_dice(self):
        r1 = run_evolution_demo(seed=7)
        r2 = run_evolution_demo(seed=7)
        assert r1["segmentation_dice"] == r2["segmentation_dice"]
