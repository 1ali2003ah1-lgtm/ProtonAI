"""D1 FINAL: self-consistent partnership guard (9 tests)."""
from __future__ import annotations

import json
from pathlib import Path

D = Path(__file__).resolve().parent / "docs" / "partnership"
HP = D / "HOSPITAL-PARTNERSHIP-001.md"
DSA = D / "DSA-001_DATA_SHARING.md"
RDP = D / "REAL-DATA-PLAYBOOK.md"
DEID = D / "DEID-CHECKLIST-001.md"
SEC = D / "DATA-TRANSFER-SECURITY-001.md"
IRB = D / "IRB-TEMPLATE-001.md"
MANIFEST = D / "PARTNERSHIP-MANIFEST.json"


def _spec():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_all_six_plus_manifest():
    for p in (HP, DSA, RDP, DEID, SEC, IRB, MANIFEST):
        assert p.exists()


def test_honesty():
    t = HP.read_text(encoding="utf-8")
    assert "NOT yet validated on human patients" in t


def test_legal():
    assert "not legal advice" in DSA.read_text(encoding="utf-8")


def test_rdp_ops():
    t = RDP.read_text(encoding="utf-8")
    assert "Pre-Flight" in t and "Escalation" in t


def test_deid_matches_manifest():
    t = DEID.read_text(encoding="utf-8")
    for tag in _spec()["deid_tags"]:
        assert tag in t


def test_security_matches_manifest():
    t = SEC.read_text(encoding="utf-8")
    for c in _spec()["security_controls"]:
        assert c in t


def test_hp_min_cases_matches_manifest():
    assert str(_spec()["min_cases"]) in HP.read_text(encoding="utf-8")


def test_irb_waiver():
    assert "Consent Waiver" in IRB.read_text(encoding="utf-8")


def test_traceability():
    combined = "".join(p.read_text(encoding="utf-8")
                       for p in (HP, DSA, RDP, DEID, SEC, IRB))
    for ref in ("NEXUS-PRD-001", "SVP-001", "REG-001", "RPT-001",
                "PLAYBOOK-001", "PMS-001", "PARTNERSHIP-MANIFEST"):
        assert ref in combined
