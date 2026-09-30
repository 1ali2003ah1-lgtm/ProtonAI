"""A4: market strategy guard (5 tests)."""
from __future__ import annotations

from tools.make_mss import COMPETITORS, GT_PHASES, OUT, PRICING


def test_doc_exists_controlled():
    t = OUT.read_text(encoding="utf-8")
    assert "MSS-001" in t and "EFFECTIVE" in t


def test_competitors_present():
    t = OUT.read_text(encoding="utf-8")
    for c in COMPETITORS:
        assert c["name"] in t and c["edge"] in t


def test_pricing_and_gtm():
    t = OUT.read_text(encoding="utf-8")
    for p in PRICING:
        assert p["tier"] in t
    for g in GT_PHASES:
        assert f"| {g['phase']} |" in t


def test_honesty_guard():
    t = OUT.read_text(encoding="utf-8")
    assert "ESTIMATES" in t and "Honesty Note" in t


def test_traceability():
    t = OUT.read_text(encoding="utf-8")
    for ref in ("NEXUS-PRD-001", "SVP-001", "REG-001", "ADR-007"):
        assert ref in t
