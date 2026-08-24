"""
ProtonAI - Test Dry-run Pipeline
"""

import pytest

pytest.importorskip("pydicom")

from dry_run_pipeline import run_dry_run


class TestDryRun:
    def test_no_phi_leak(self):
        r = run_dry_run()
        assert r["phi_leak"] is False

    def test_deidentified(self):
        r = run_dry_run()
        assert r["report"]["deidentified"] is True

    def test_rois_parsed(self):
        r = run_dry_run()
        assert "GTV" in r["report"]["rois"]

    def test_image_normalized(self):
        r = run_dry_run()
        lo, hi = r["report"]["image_range"]
        assert lo >= 0.0 and hi <= 1.0

    def test_geometry(self):
        r = run_dry_run()
        assert r["report"]["geometry"]["rows"] == 64
