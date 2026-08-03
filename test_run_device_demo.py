"""
ProtonAI - Test Device Readiness Demo
اختبارات مايسترو الجاهزية (MC ضخم + torch شرطياً + لوحة + تقرير)
"""

import pytest
from run_device_demo import run_device_demo
from torch_segmenter import TORCH_AVAILABLE
from streamlit_dashboard import STREAMLIT_AVAILABLE


@pytest.fixture
def res():
    return run_device_demo()


class TestCore:
    def test_keys(self, res):
        for k in ["mc", "mc_histories", "torch_seg", "dashboard",
                  "streamlit", "readiness_markdown"]:
            assert k in res

    def test_mc_large_and_accurate(self, res):
        assert res["mc_histories"] == 100_000
        assert res["mc"]["rel_diff"] < 0.06


class TestTorchConditional:
    def test_flag_consistent(self, res):
        assert res["torch_seg"]["available"] is TORCH_AVAILABLE

    def test_dice_only_when_available(self, res):
        if TORCH_AVAILABLE:
            assert res["torch_seg"]["dice"] > 0.7
        else:
            assert res["torch_seg"]["dice"] is None
            assert "torch" in res["torch_seg"]["note"]


class TestDashboard:
    def test_delivered(self, res):
        assert res["dashboard"]["state"] == "delivered"
        assert res["dashboard"]["overall"] == "GREEN"

    def test_streamlit_flag(self, res):
        assert res["streamlit"] is STREAMLIT_AVAILABLE


class TestReadiness:
    def test_markdown_sections(self, res):
        md = res["readiness_markdown"]
        assert "تقرير جاهزية الجهاز" in md
        assert "Monte Carlo" in md
        assert "torch" in md
        assert "Streamlit" in md


class TestSave:
    def test_saves(self, tmp_path):
        out = tmp_path / "dev"
        run_device_demo(output_dir=out)
        assert (out / "device_readiness.md").exists()

    def test_no_save_no_crash(self):
        assert run_device_demo()["mc"]["rel_diff"] < 0.06
