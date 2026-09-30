"""A2: product risk management (ISO 14971) - register as code.

FMEA scales 1-5; RPN = S*O*D; acceptable iff RPN < ACCEPT_RPN.
Mitigations must reference controlled assets only.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "quality_system" / "iso_13485" / \
    "PRM-001_PRODUCT_RISK.md"
ACCEPT_RPN = 40

ALLOWED_MITIGATIONS = {
    "CLIN-001", "CLIN-002", "PMS-001", "ADR-007", "ADR-008", "USP-001",
    "REG-001", "SVP-001", "schema v2", "playbook", "ISO 27001",
    "interlock", "QMS ISO 13485", "calm design", "confidence display",
}

RISKS = [
    {"id": "R-101", "hazard": "Incorrect auto-segmentation",
     "harm": "Wrong target volume / mistreatment", "S": 5, "O": 2, "D": 2,
     "mitigations": ["CLIN-002", "CLIN-001", "interlock"]},
    {"id": "R-102", "hazard": "Automation bias (rubber-stamp approval)",
     "harm": "Unchecked erroneous plan", "S": 4, "O": 3, "D": 3,
     "mitigations": ["interlock", "confidence display", "USP-001"]},
    {"id": "R-103", "hazard": "Performance drift (population shift)",
     "harm": "Silent degradation of contours", "S": 4, "O": 3, "D": 2,
     "mitigations": ["PMS-001", "playbook"]},
    {"id": "R-104", "hazard": "PHI exposure",
     "harm": "Privacy breach / legal", "S": 4, "O": 2, "D": 2,
     "mitigations": ["schema v2", "ISO 27001"]},
    {"id": "R-105", "hazard": "Train/deploy model mismatch",
     "harm": "Unverified shipped model", "S": 4, "O": 1, "D": 1,
     "mitigations": ["ADR-008"]},
    {"id": "R-106", "hazard": "Insufficient real-world evidence at launch",
     "harm": "Unsupported clinical claims", "S": 3, "O": 4, "D": 2,
     "mitigations": ["SVP-001", "playbook"]},
    {"id": "R-107", "hazard": "Regulatory pathway change",
     "harm": "Delayed market entry", "S": 3, "O": 2, "D": 3,
     "mitigations": ["REG-001", "QMS ISO 13485"]},
    {"id": "R-108", "hazard": "Use error (overlay misinterpretation)",
     "harm": "Wrong clinical decision", "S": 3, "O": 3, "D": 2,
     "mitigations": ["USP-001", "calm design"]},
]


def rpn(r):
    return r["S"] * r["O"] * r["D"]


def acceptable(r):
    return rpn(r) < ACCEPT_RPN


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    for r in RISKS:
        for m in r["mitigations"]:
            if m not in ALLOWED_MITIGATIONS:
                raise SystemExit(f"uncontrolled mitigation: {m}")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# PRM-001: Product Risk Management (ISO 14971)", "",
             "## Document Control",
             "| ID | Version | Generated | Generator commit | Status |",
             "|---|---|---|---|---|",
             f"| PRM-001 | 1.0 | {now} | {git_commit()} | EFFECTIVE |", "",
             "## 1. Method",
             f"FMEA scales 1-5; RPN = S x O x D; acceptable iff RPN < "
             f"{ACCEPT_RPN}. Mitigations reference controlled assets only.",
             "", "## 2. Risk Register",
             "| ID | Hazard | S | O | D | RPN | Mitigations | Acceptable |",
             "|---|---|---|---|---|---|---|---|"]
    for r in RISKS:
        lines.append(f"| {r['id']} | {r['hazard']} | {r['S']} | {r['O']} | "
                     f"{r['D']} | {rpn(r)} | {', '.join(r['mitigations'])} | "
                     f"{acceptable(r)} |")
    lines += ["", "## 3. Residual Risk Evaluation",
              f"- Max RPN = {max(rpn(r) for r in RISKS)} (< {ACCEPT_RPN}); "
              "all residual risks acceptable.",
              "- R-102 (automation bias) is watched: enforced interlock + "
              "formative usability testing (USP-001).",
              "", "## 4. Review Cadence",
              "- Quarterly with PMS-001 review; on every new module or "
              "adverse event.", "", "## 5. Traceability",
              "NEXUS-PRD-001 s9, RPT-001 v4.0, CLIN-001, CLIN-002, PMS-001, "
              "ADR-007, ADR-008, USP-001, REG-001, SVP-001, ISO 14971.", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"PRM-001: risks={len(RISKS)} max_rpn={max(rpn(r) for r in RISKS)} "
          f"all_acceptable={all(acceptable(r) for r in RISKS)}")
    print("Saved -> docs/quality_system/iso_13485/PRM-001_PRODUCT_RISK.md")


if __name__ == "__main__":
    main()
