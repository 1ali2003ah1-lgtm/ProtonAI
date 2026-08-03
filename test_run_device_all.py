"""
ProtonAI - Test Run All (Device Capstone)
"""

import pytest
from run_device_all import run_device_all


@pytest.fixture
def res():
    return run_device_all()


class TestSummaries:
    def test_all_keys(self, res):
        for k in ["clinical", "enterprise", "evolution", "device"]:
            assert k in res["summaries"]

    def test_clinical_delivered(self, res):
        assert res["summaries"]["clinical"]["state"] == "delivered"

    def test_enterprise_gate(self, res):
        assert res["summaries"]["enterprise"]["gate"] == "approved"

    def test_evolution_dice(self, res):
        assert res["summaries"]["evolution"]["segmentation_dice"] > 0.8

    def test_device_flags(self, res):
        d = res["summaries"]["device"]
        assert isinstance(d["torch_available"], bool)
        assert isinstance(d["streamlit_available"], bool)


class TestMarkdown:
    def test_has_sections(self, res):
        md = res["markdown"]
        for s in ["سريري", "مؤسسي", "تطور", "جهاز"]:
            assert s in md


class TestSave:
    def test_saves(self, tmp_path):
        out = tmp_path / "all"
        run_device_all(output_dir=out)
        assert (out / "run_all_report.md").exists()
