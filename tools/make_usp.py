"""A3: usability engineering (IEC 62366-1) - use specification as code.

User profiles, tasks with criticality, formative/summative plans.
Every critical task must link to an existing PRM-001 risk id.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.make_prm import RISKS  # noqa: E402
OUT = ROOT / "docs" / "quality_system" / "iso_13485" / \
    "USP-001_USE_SPECIFICATION.md"

USER_PROFILES = [
    {"id": "UP-1", "role": "Medical physicist", "expertise": "high",
     "tasks": "plan approval, DVH review, model-card verification"},
    {"id": "UP-2", "role": "Radiation oncologist", "expertise": "clinical",
     "tasks": "contour review, triage response"},
    {"id": "UP-3", "role": "Dosimetrist", "expertise": "medium",
     "tasks": "contour editing, what-if exploration"},
    {"id": "UP-4", "role": "QA officer", "expertise": "quality",
     "tasks": "PMS review, regulatory bundle generation"},
]

TASKS = [
    {"id": "T-1", "task": "Review AI contour with uncertainty overlay",
     "profile": "UP-2", "critical": True, "risk": "R-101"},
    {"id": "T-2", "task": "Approve or reject plan (interlock)",
     "profile": "UP-1", "critical": True, "risk": "R-102"},
    {"id": "T-3", "task": "Explore what-if dose",
     "profile": "UP-3", "critical": False, "risk": "R-108"},
    {"id": "T-4", "task": "Verify model card parity",
     "profile": "UP-1", "critical": False, "risk": "R-105"},
    {"id": "T-5", "task": "Review PMS drift wall",
     "profile": "UP-4", "critical": True, "risk": "R-103"},
    {"id": "T-6", "task": "Generate regulatory bundle",
     "profile": "UP-4", "critical": False, "risk": "R-107"},
]

FORMATIVE = {"participants": 6, "sessions": 2,
             "success": "first-use task success > 95%",
             "method": "think-aloud + System Usability Scale (SUS)"}


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    risk_ids = {r["id"] for r in RISKS}
    profile_ids = {p["id"] for p in USER_PROFILES}
    for t in TASKS:
        if t["risk"] not in risk_ids:
            raise SystemExit(f"task links unknown risk: {t['risk']}")
        if t["profile"] not in profile_ids:
            raise SystemExit(f"task links unknown profile: {t['profile']}")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# USP-001: Use Specification & Usability Engineering "
             "(IEC 62366-1)", "",
             "## Document Control",
             "| ID | Version | Generated | Generator commit | Status |",
             "|---|---|---|---|---|",
             f"| USP-001 | 1.0 | {now} | {git_commit()} | EFFECTIVE |", "",
             "## 1. Intended Use",
             "Review, triage and approval assistance for AI-generated "
             "proton-therapy contours; not a treatment planning system.", "",
             "## 2. User Profiles",
             "| ID | Role | Expertise | Primary tasks |",
             "|---|---|---|---|"]
    for p in USER_PROFILES:
        lines.append(f"| {p['id']} | {p['role']} | {p['expertise']} | "
                     f"{p['tasks']} |")
    lines += ["", "## 3. Tasks & Criticality (linked to PRM-001)",
              "| ID | Task | Profile | Critical | Linked risk |",
              "|---|---|---|---|---|"]
    for t in TASKS:
        lines.append(f"| {t['id']} | {t['task']} | {t['profile']} | "
                     f"{t['critical']} | {t['risk']} |")
    lines += ["", "## 4. Formative Evaluation Plan",
              f"- Participants: {FORMATIVE['participants']} (all profiles); "
              f"sessions: {FORMATIVE['sessions']}.",
              f"- Method: {FORMATIVE['method']}.",
              f"- Success criterion: {FORMATIVE['success']} "
              "(matches NEXUS-PRD-001 KPI).", "",
              "## 5. Summative Evaluation Plan",
              "- Pre-approval simulated-use study on de-identified cases; "
              "zero critical use errors tolerated.", "",
              "## 6. User Interface Characteristics",
              "Dark reading-room default; color-blind-safe palette; "
              "Arabic/English i18n; response <100ms; approval interlock "
              "visible and explained.", "",
              "## 7. Traceability",
              "IEC 62366-1, PRM-001 (R-101..R-108), NEXUS-PRD-001, "
              "CLIN-001, CLIN-002.", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    crit = sum(1 for t in TASKS if t["critical"])
    print(f"USP-001: profiles={len(USER_PROFILES)} tasks={len(TASKS)} "
          f"critical={crit}")
    print("Saved -> docs/quality_system/iso_13485/USP-001_USE_SPECIFICATION.md")


if __name__ == "__main__":
    main()
