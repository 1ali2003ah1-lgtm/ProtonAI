"""P5-S4: report v4.0 + readiness guard (5 tests)."""
from __future__ import annotations

import json
from pathlib import Path

REPORT = Path("EXPERIMENT_REPORT.md")
MARK11 = "## 11. Phase 5: Clinical Confidence & Real-Data Readiness"
REF_SEAL = Path("docs/experiments/PROVENANCE_DATASET-000-SYNTH-REF.json")


def load(n):
    return json.loads(Path(n).read_text(encoding="utf-8"))


def test_reference_sealed():
    assert REF_SEAL.exists()
    m = json.loads(REF_SEAL.read_text(encoding="utf-8"))
    assert m["schema"] == 2 and m["dataset_id"] == "DATASET-000-SYNTH-REF"


def test_version_and_marker():
    t = REPORT.read_text(encoding="utf-8")
    assert "| RPT-001 | 4.0 |" in t
    assert t.count(MARK11) == 1


def test_stats_rigor_bounds():
    rv = load("registered_validation_results.json")
    for r in rv["datasets"]:
        if r.get("wilcoxon_p") is not None:
            assert 0.0 <= r["wilcoxon_p"] <= 1.0
        assert 0.0 <= r.get("seed_concordance", 0.0) <= 1.0
        lo, hi = r.get("paired_diff_ci95", [0, 0])
        assert lo <= hi


def test_readiness_truthful():
    rv = load("registered_validation_results.json")
    t = REPORT.read_text(encoding="utf-8")
    assert rv["readiness"] is True
    assert f"Readiness: {rv['readiness']}" in t


def test_report_numbers_match_artifacts():
    t = REPORT.read_text(encoding="utf-8")
    conf = load("confidence_analysis_results.json")
    io = load("inter_observer_study.json")
    assert f"{conf['threshold_C']:.6f}" in t
    assert f"{io['mean_dice']:.4f}" in t
