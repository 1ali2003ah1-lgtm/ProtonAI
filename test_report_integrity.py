"""P4-S1: controlled-report integrity guard (RPT-001 v3.0)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "EXPERIMENT_REPORT.md"
EV = ROOT / "external_validation_results.json"
UQ = ROOT / "uq_analysis_results.json"
PROV3 = ROOT / "docs" / "experiments" / "PROVENANCE_phase3.json"
MARK9 = "## 9. Phase 3: Real-World Readiness Evidence"
MARK10 = "## 10. Document Revision History"


@pytest.fixture(scope="module")
def text():
    return REPORT.read_text(encoding="utf-8")


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_version_bumped(text):
    assert "| RPT-001 | 3.0 |" in text


def test_markers_exactly_once(text):
    assert text.count(MARK9) == 1
    assert text.count(MARK10) == 1


def test_exec_summary_covers_both_phases(text):
    head = text.split("## 2. Hypothesis")[0]
    assert "Phase-2" in head and "Phase-3" in head
    assert "CLIN-001" in head


def test_report_numbers_match_artifacts(text):
    ev, uq = load(EV), load(UQ)
    assert f"{uq['cross_domain']['mean_uncertainty']:.4f}" in text
    assert f"{ev['experiment']['gap_S1_to_S2']:+.4f}" in text
    assert f"{uq['ood_mannwhitney_p']:.4f}" in text


def test_sealing_table_in_report(text):
    prov = load(PROV3)
    for h in prov["hashes"].values():
        assert h[:16] in text


def test_provenance_hashes_current():
    prov = load(PROV3)
    for rel in ("external_validation_results.json",
                "uq_analysis_results.json"):
        h = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert prov["hashes"][rel] == h
