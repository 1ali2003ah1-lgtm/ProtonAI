"""P4-S2: executable enforcement of CLIN-001 uncertainty flagging policy.

The MD document is prose for humans; this module is the machine-enforceable
specification used by any clinical integration. Policy integrity (evidence
hash) is verified on every load.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLICY = ROOT / "clin001_policy.json"
UQ = ROOT / "uq_analysis_results.json"


class PolicyIntegrityError(RuntimeError):
    """Policy artifact missing or inconsistent with its evidence base."""


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def load_policy(verify=True):
    if not POLICY.exists():
        raise PolicyIntegrityError("clin001_policy.json missing")
    pol = _load(POLICY)
    if verify:
        if pol.get("uq_artifact_sha256") != \
                hashlib.sha256(UQ.read_bytes()).hexdigest():
            raise PolicyIntegrityError("policy evidence hash mismatch")
    return pol


def review_required(uncertainty: float, policy=None) -> bool:
    pol = policy or load_policy()
    return uncertainty > pol["theta"]


def batch_decision(flags, policy=None) -> str:
    """AUTO | FLAGGED_REVIEW | SUSPEND_AND_CAPA per CLIN-001 s3."""
    pol = policy or load_policy()
    if not any(flags):
        return "AUTO"
    frac = sum(flags) / len(flags)
    if frac > pol["suspend_fraction"]:
        return "SUSPEND_AND_CAPA"
    return "FLAGGED_REVIEW"
