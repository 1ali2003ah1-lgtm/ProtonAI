"""
ProtonAI - Test Grand Demo
اختبارات نقطة الدخول الشاملة (كل الطبقات + الحفظ)
"""

import pytest
from run_grand_demo import run_grand_demo


@pytest.fixture
def res():
    return run_grand_demo()


class TestClinical:
    def test_delivered(self, res):
        assert res["clinical"]["state"] == "delivered"

    def test_overall_green(self, res):
        assert res["clinical"]["overall"] == "GREEN"


class TestResearch:
    def test_accuracy_present(self, res):
        assert 0 <= res["research"]["retro_accuracy"] <= 1
        assert 0 <= res["research"]["external_accuracy"] <= 1

    def test_robust_and_ready(self, res):
        # 0.9 vs 0.88 → فجوة 0.02 robust + خارجي فوق الحد → جاهز
        assert res["research"]["publication_ready"] is True
        assert res["research"]["generalization_gap"] == pytest.approx(0.02)


class TestImprovement:
    def test_iteration_recorded(self, res):
        assert res["improvement"]["iteration"] == 1

    def test_issues_detected(self, res):
        # خطأ واحد منحاز لصنف B → issue واحدة
        assert res["improvement"]["issues"] >= 1


class TestEnterprise:
    def test_denied_and_gate(self, res):
        assert res["enterprise"]["denied"] >= 2
        assert res["enterprise"]["gate"] == "approved"


class TestReproducibility:
    def test_seeds_and_python(self, res):
        assert res["reproducibility"]["seeds"] == [42]
        assert res["reproducibility"]["python"]


class TestRelease:
    def test_feature_bumps_minor(self, res):
        assert res["release"]["version"] == "1.1.0"

    def test_ready_to_launch(self, res):
        assert res["release"]["ready_to_launch"] is True


class TestReport:
    def test_has_sections(self, res):
        md = res["report_markdown"]
        for sec in ["الملخص (Abstract)", "النتائج (Results)",
                    "القيود (Limitations)", "الخاتمة (Conclusion)"]:
            assert sec in md

    def test_stages_in_report(self, res):
        md = res["report_markdown"]
        assert "### سريري" in md
        assert "### بحثي" in md
        assert "### مؤسسي" in md


class TestSave:
    def test_saves_files(self, tmp_path):
        out = tmp_path / "grand"
        run_grand_demo(output_dir=out)
        assert (out / "grand_report.md").exists()
        assert (out / "reproducibility.json").exists()
