"""A5: scientific validation plan guard (5 tests)."""
from __future__ import annotations

from pathlib import Path

from tools.make_svp import OUT, PAPERS


def test_doc_exists_controlled():
    t = OUT.read_text(encoding="utf-8")
    assert "SVP-001" in t and "EFFECTIVE" in t


def test_three_papers_with_journals():
    t = OUT.read_text(encoding="utf-8")
    for p in PAPERS:
        assert p["id"] in t and p["journal"] in t


def test_evidence_links():
    t = OUT.read_text(encoding="utf-8")
    assert "REPRO_BUNDLE.json" in t
    assert "confidence_analysis_results.json" in t
    assert "dose bridge" in t and "real-data" in t


def test_statistical_plan():
    t = OUT.read_text(encoding="utf-8")
    for s in ("Wilcoxon", "bootstrap", "HD95", "DVH"):
        assert s in t


def test_integrity_and_traceability():
    t = OUT.read_text(encoding="utf-8")
    for s in ("Preregister", "p-hacking", "PRM-001", "MSS-001"):
        assert s in t
