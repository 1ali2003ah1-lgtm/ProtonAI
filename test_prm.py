"""A2: product risk register guard (5 tests)."""
from __future__ import annotations

from pathlib import Path

from tools.make_prm import (ACCEPT_RPN, ALLOWED_MITIGATIONS, OUT, RISKS,
                            acceptable, rpn)


def test_doc_exists_controlled():
    t = OUT.read_text(encoding="utf-8")
    assert "PRM-001" in t and "EFFECTIVE" in t and "ISO 14971" in t


def test_all_risks_acceptable():
    assert all(acceptable(r) for r in RISKS)
    assert max(rpn(r) for r in RISKS) < ACCEPT_RPN


def test_doc_rpn_values_match():
    t = OUT.read_text(encoding="utf-8")
    for r in RISKS:
        assert f"| {r['id']} |" in t
        assert f"| {rpn(r)} |" in t


def test_mitigations_controlled_only():
    for r in RISKS:
        for m in r["mitigations"]:
            assert m in ALLOWED_MITIGATIONS


def test_traceability():
    t = OUT.read_text(encoding="utf-8")
    for ref in ("NEXUS-PRD-001", "RPT-001", "PMS-001", "USP-001", "REG-001"):
        assert ref in t
