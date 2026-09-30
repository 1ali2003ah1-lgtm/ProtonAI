"""A3: usability specification guard (5 tests)."""
from __future__ import annotations

from pathlib import Path

from tools.make_prm import RISKS
from tools.make_usp import OUT, TASKS, USER_PROFILES


def test_doc_exists_controlled():
    t = OUT.read_text(encoding="utf-8")
    assert "USP-001" in t and "EFFECTIVE" in t and "IEC 62366-1" in t


def test_critical_tasks_link_real_risks():
    risk_ids = {r["id"] for r in RISKS}
    for t in TASKS:
        assert t["risk"] in risk_ids


def test_doc_contains_profiles_and_tasks():
    t = OUT.read_text(encoding="utf-8")
    for p in USER_PROFILES:
        assert f"| {p['id']} |" in t
    for task in TASKS:
        assert f"| {task['id']} |" in t


def test_formative_success_matches_prd_kpi():
    t = OUT.read_text(encoding="utf-8")
    assert "95" in t and "first-use" in t


def test_traceability():
    t = OUT.read_text(encoding="utf-8")
    for ref in ("PRM-001", "NEXUS-PRD-001", "CLIN-001", "IEC 62366-1"):
        assert ref in t
