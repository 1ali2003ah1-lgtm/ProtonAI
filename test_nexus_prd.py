"""A1: NEXUS PRD — investor-grade product requirements (6 tests)."""
from __future__ import annotations

from pathlib import Path

PRD = Path("docs/product/NEXUS-PRD-001.md")


def test_prd_exists():
    assert PRD.exists()


def test_prd_controlled():
    t = PRD.read_text(encoding="utf-8")
    assert "NEXUS-PRD-001" in t and "| 2.0 |" in t and "EFFECTIVE" in t
    assert "Owner" in t


def test_prd_defensibility():
    t = PRD.read_text(encoding="utf-8")
    for s in ("Defensibility", "schema v2", "ADR-007", "cannot be copied"):
        assert s in t


def test_prd_success_metrics():
    t = PRD.read_text(encoding="utf-8")
    assert "Success Metrics" in t and "KPI" in t
    for metric in ("Segmentation time", "DVH", "PMS drift"):
        assert metric in t


def test_prd_acceptance_criteria():
    t = PRD.read_text(encoding="utf-8")
    assert "Acceptance Criteria" in t
    for mod in ("Cockpit", "What-if", "CLIN-002", "Provenance"):
        assert mod in t


def test_prd_traceability_to_siblings():
    t = PRD.read_text(encoding="utf-8")
    for sib in ("PRM-001", "USP-001", "MSS-001", "SVP-001",
                "REG-001", "TLM-001"):
        assert sib in t
