"""P7-S1: triage dashboard guard (7 tests)."""
from __future__ import annotations

import json
from pathlib import Path

from clinical_gate import batch_decision

ROOT = Path(__file__).resolve().parent
JSON = ROOT / "clinical_dashboard.json"
HIST = ROOT / "clinical_dashboard_history.json"
MD = ROOT / "docs" / "quality_system" / "iso_13485" / \
    "CLIN-002_CLINICAL_DASHBOARD.md"


def load(n):
    return json.loads((ROOT / n).read_text(encoding="utf-8"))


def test_artifacts_exist():
    assert JSON.exists() and HIST.exists() and MD.exists()


def test_flags_consistent_with_policy():
    d, pol = load("clinical_dashboard.json"), load("clin001_policy.json")
    for scope in ("in_domain", "cross_domain"):
        for r in d["scopes"][scope]["rows"]:
            assert r["flag"] == (r["vote_entropy"] > pol["theta"])


def test_triage_hierarchy():
    d, uq = load("clinical_dashboard.json"), load("uq_analysis_results.json")
    ux = uq["cross_domain"]
    fails = [x < uq["fail_threshold"] for x in ux["per_case_dice"]]
    fu = [u for u, f in zip(ux["per_case_uncertainty"], fails) if f]
    urgent = max(fu) if fu else None
    for scope in ("in_domain", "cross_domain"):
        for r in d["scopes"][scope]["rows"]:
            if r["triage"] == "AUTO":
                assert not r["flag"] and r["review"] == "auto"
            else:
                assert r["flag"] and r["review"] == "physicist"
            if r["triage"] == "URGENT":
                assert urgent is not None and r["vote_entropy"] >= urgent


def test_batch_states_match_gate():
    d = load("clinical_dashboard.json")
    for scope, s in d["scopes"].items():
        assert s["batch_state"] == batch_decision(
            [r["flag"] for r in s["rows"]])


def test_kpis_match_artifacts():
    d = load("clinical_dashboard.json")
    conf, pol = load("confidence_analysis_results.json"), \
        load("clin001_policy.json")
    assert d["kpis"]["threshold_C"] == conf["threshold_C"]
    assert d["kpis"]["separation_margin"] == pol.get("separation_margin")
    assert d["kpis"]["failures_captured"] is True


def test_history_appended():
    d = load("clinical_dashboard.json")
    hist = load("clinical_dashboard_history.json")
    assert hist and hist[-1]["generated"] == d["generated"]


def test_markdown_triage_and_traceability():
    t = MD.read_text(encoding="utf-8")
    d = load("clinical_dashboard.json")
    for r in d["scopes"]["cross_domain"]["rows"]:
        assert r["case"] in t and r["triage"] in t
    for ref in ("CLIN-001", "ADR-007", "RPT-001"):
        assert ref in t
