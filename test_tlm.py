"""A7 enhanced: self-auditing TLM guard (6 tests)."""
from __future__ import annotations

import hashlib

from tools.make_tlm import (CORE_ASSETS, DOCS, OUT, REQUIRED_LINKS, sha12)


def test_doc_exists_controlled():
    t = OUT.read_text(encoding="utf-8")
    assert "TLM-001" in t and "| 2.0 |" in t and "EFFECTIVE" in t


def test_discovered_matrix_marks_known_links():
    t = OUT.read_text(encoding="utf-8")
    row = [ln for ln in t.split("\n") if ln.startswith("| PRM-001 |")]
    assert row and "✓" in row[0]


def test_required_links_listed():
    t = OUT.read_text(encoding="utf-8")
    for s, tgt in REQUIRED_LINKS[:5]:
        assert f"{s}->{tgt}" in t


def test_core_asset_coverage():
    t = OUT.read_text(encoding="utf-8")
    for a in CORE_ASSETS:
        assert f"| {a} |" in t


def test_fingerprints_current():
    t = OUT.read_text(encoding="utf-8")
    for n, p in DOCS.items():
        assert sha12(p) in t


def test_method_self_auditing():
    t = OUT.read_text(encoding="utf-8")
    for s in ("DISCOVERED", "sha256", "refuse"):
        assert s in t
