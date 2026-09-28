"""P4-S2: generate CLIN-001 policy artifacts (machine JSON + human MD).

theta = max in-domain per-case vote entropy (evidence-derived).
Separation margin = min cross-domain FAILING-case uncertainty - theta.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UQ = ROOT / "uq_analysis_results.json"
POL = ROOT / "clin001_policy.json"
OUT = ROOT / "docs" / "quality_system" / "iso_13485" / \
    "CLIN-001_UNCERTAINTY_FLAGGING.md"
SUSPEND_FRACTION = 0.20


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    uq = load(UQ)
    ui, ux = uq["in_domain"], uq["cross_domain"]
    theta = max(ui["per_case_uncertainty"])
    flags = [u > theta for u in ux["per_case_uncertainty"]]
    fails = [d < uq["fail_threshold"] for d in ux["per_case_dice"]]
    captured = all(fl for f, fl in zip(fails, flags) if f)
    failing_unc = [u for u, f in zip(ux["per_case_uncertainty"], fails) if f]
    margin = (min(failing_unc) - theta) if failing_unc else None
    margin_str = f"{margin:.6f}" if margin is not None else \
        "n/a (no cross-domain failures observed)"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    policy = {"id": "CLIN-001", "version": "1.0", "theta": theta,
              "suspend_fraction": SUSPEND_FRACTION,
              "uq_artifact_sha256": hashlib.sha256(UQ.read_bytes()).hexdigest(),
              "separation_margin": margin,
              "cross_flag_rate": [sum(flags), len(flags)],
              "failures_captured": captured,
              "generated": now, "generator_commit": git_commit()}
    POL.write_text(json.dumps(policy, indent=2, sort_keys=True),
                   encoding="utf-8")
    md = "\n".join([
        "# CLIN-001: Uncertainty Flagging & Physicist Review Policy",
        "",
        "## Document Control",
        "| ID | Version | Generated | Generator commit | Status |",
        "|---|---|---|---|---|",
        f"| CLIN-001 | 1.0 | {now} | {git_commit()} | EFFECTIVE |",
        "",
        "## 1. Scope",
        "Applies to every ProtonAI organ-at-risk segmentation released into",
        "a proton therapy planning workflow.",
        "",
        "## 2. Definitions",
        "- Vote entropy: mean pixel-wise binary entropy across the K=5 seed",
        "  ensemble (ADR-006).",
        "- Flagging threshold theta: maximum in-domain per-case vote entropy",
        "  in the validated evidence set (uq_analysis_results.json).",
        "- Separation margin: min cross-domain FAILING-case uncertainty",
        "  minus theta (safety trench between safe and failing regions).",
        "",
        "## 3. Flagging Rule (mandatory, machine-enforced)",
        f"- theta = {theta:.6f}",
        f"- Separation margin = {margin_str}",
        "- Decision states (enforced by clinical_gate.py):",
        "",
        "| State | Condition | Action |",
        "|---|---|---|",
        "| AUTO | no flagged cases | release pathway |",
        "| FLAGGED_REVIEW | 0 < flag fraction <= 0.20 | flagged cases to",
        "physicist review; remainder released |",
        "| SUSPEND_AND_CAPA | flag fraction > 0.20 | suspend automated",
        "pathway; manual contouring; CAPA within 24h |",
        "",
        "- A flagged case MUST receive documented medical physicist review",
        "  before any contour is used in planning. Release without review",
        "  is a procedure violation.",
        "",
        "## 4. Records & Audit",
        "- Per case: uncertainty value, flag decision, decision state,",
        "  reviewer ID, decision timestamp. Immutable audit trail (T-05).",
        "",
        "## 5. Threshold Governance",
        "- theta is recomputed only under change control: model retrain,",
        "  new domain data, or annual review. Each change bumps this",
        "  document version, clin001_policy.json, and the CHANGELOG.",
        "",
        "## 6. Evidence Basis & Validation",
        f"- In-domain maximum (threshold source): {theta:.6f}",
        f"- Cross-domain flag rate at theta: {sum(flags)}/{len(flags)}",
        f"- Cross-domain failures captured by flag: {captured}",
        f"- OOD sensitivity: Mann-Whitney p = {uq['ood_mannwhitney_p']:.4f}",
        "- Traceability: RISK_REGISTER R-010; ADR-006; RPT-001 v3.0 s9.2.",
        "",
        "## 7. Approval",
        "| Role | Name | Signature | Date |",
        "|---|---|---|---|",
        "| Author (Research Lead) | (pending) | (pending) | (pending) |",
        "| Reviewer (Medical Physicist) | (pending) | (pending) | (pending) |",
        "| Approver (QMS Manager) | (pending) | (pending) | (pending) |",
        "",
    ])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(md, encoding="utf-8")
    print(f"CLIN-001 artifacts written; theta={theta:.6f}; "
          f"margin={margin_str}; flags={sum(flags)}/{len(flags)}; "
          f"captured={captured}")


if __name__ == "__main__":
    main()
