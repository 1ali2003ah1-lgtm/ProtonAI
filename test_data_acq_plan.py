"""P4-S3: DATA-ACQ-001 plan guard (document <-> code consistency)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))

from power_analysis import paired_n  # noqa: E402

DOC = ROOT / "docs" / "quality_system" / "iso_13485" / \
    "DATA-ACQ-001_REAL_DATA_ACQUISITION_PLAN.md"


def test_doc_exists():
    assert DOC.exists()


def test_mandatory_sections():
    text = DOC.read_text(encoding="utf-8")
    for s in ("De-Identification Gate", "Executable QC", "Statistical Power",
              "Inclusion", "Governance", "Approval"):
        assert s in text


def test_gate_is_machine_enforced():
    text = DOC.read_text(encoding="utf-8")
    assert "ingest_real_series" in text and "allow_phi=False" in text


def test_power_numbers_match_tool():
    text = DOC.read_text(encoding="utf-8")
    assert f"n_min = {paired_n()}" in text and "target = 30" in text


def test_traceability():
    text = DOC.read_text(encoding="utf-8")
    for ref in ("R-003", "ADR-001", "ADR-005", "CLIN-001"):
        assert ref in text
