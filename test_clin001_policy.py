"""P4-S2: CLIN-001 policy + executable gate guard (9 tests)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import clinical_gate
from clinical_gate import batch_decision, review_required

ROOT = Path(__file__).resolve().parent
DOC = ROOT / "docs" / "quality_system" / "iso_13485" / \
    "CLIN-001_UNCERTAINTY_FLAGGING.md"
POL = ROOT / "clin001_policy.json"
UQ = ROOT / "uq_analysis_results.json"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def policy():
    return clinical_gate.load_policy()


@pytest.fixture(scope="module")
def uq():
    return load(UQ)


def test_policy_artifacts_exist():
    assert DOC.exists() and POL.exists()


def test_theta_evidence_derived(policy, uq):
    theta = max(uq["in_domain"]["per_case_uncertainty"])
    assert policy["theta"] == theta
    assert f"{theta:.6f}" in DOC.read_text(encoding="utf-8")


def test_policy_hash_matches_uq(policy):
    import hashlib
    assert policy["uq_artifact_sha256"] == \
        hashlib.sha256(UQ.read_bytes()).hexdigest()


def test_gate_flags_all_cross_failures(policy, uq):
    ux = uq["cross_domain"]
    for u, d in zip(ux["per_case_uncertainty"], ux["per_case_dice"]):
        if d < uq["fail_threshold"]:
            assert review_required(u, policy)


def test_gate_no_in_domain_flags(policy, uq):
    for u in uq["in_domain"]["per_case_uncertainty"]:
        assert not review_required(u, policy)


def test_batch_suspend(policy):
    assert batch_decision([True] * 3 + [False] * 5, policy) == "SUSPEND_AND_CAPA"


def test_batch_flagged_review(policy):
    assert batch_decision([True] + [False] * 7, policy) == "FLAGGED_REVIEW"


def test_batch_auto(policy):
    assert batch_decision([False] * 8, policy) == "AUTO"


def test_md_approval_and_traceability():
    text = DOC.read_text(encoding="utf-8")
    for ref in ("R-010", "ADR-006", "RPT-001", "CAPA",
                "Medical Physicist", "audit"):
        assert ref in text
