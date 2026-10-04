"""H1 FINAL: publication guard (7 tests, cross-consistency)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ABS = ROOT / "docs" / "publication" / "ABSTRACT-001.md"
MS = ROOT / "docs" / "publication" / "PAP-3-draft.md"
COVER = ROOT / "docs" / "publication" / "COVER-LETTER-001.md"
PITCH = ROOT / "docs" / "marketing" / "PITCH-DECK.md"
SUM = ROOT / "docs" / "publication" / "publication_summary.json"


def test_all_exist():
    for p in (ABS, MS, COVER, PITCH, SUM):
        assert p.exists()


def test_abstract_keywords():
    t = ABS.read_text(encoding="utf-8")
    assert "Keywords" in t and "Methods" in t


def test_manuscript_authors_refs_honesty():
    t = MS.read_text(encoding="utf-8")
    assert "Authors" in t and "References" in t and "Lyman" in t
    assert "NOT for clinical use" in t


def test_cover_letter():
    t = COVER.read_text(encoding="utf-8")
    assert "Dear Editor" in t and "Sincerely" in t


def test_pitch_complete():
    t = PITCH.read_text(encoding="utf-8")
    for s in ("Problem", "Solution", "Market", "Moat", "Ask"):
        assert s in t


def test_summary_keys():
    r = json.loads(SUM.read_text(encoding="utf-8"))
    assert {"d95_mean", "p", "verdict", "tcp", "ntcp"} <= set(r)


def test_cross_consistency():
    r = json.loads(SUM.read_text(encoding="utf-8"))
    key = f"{r['d95_mean']:.3f}"
    assert key in ABS.read_text(encoding="utf-8")
    assert key in MS.read_text(encoding="utf-8")
    assert key in COVER.read_text(encoding="utf-8")
