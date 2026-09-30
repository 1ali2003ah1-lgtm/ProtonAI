"""A5: scientific validation plan as code (SVP-001).

Three papers; each linked to concrete evidence artifacts or documented
prerequisites. Integrity section enforces preregistration culture.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "product" / "SVP-001_SCIENTIFIC_VALIDATION.md"

PAPERS = [
    {"id": "PAP-1",
     "title": "Content-hash sealing for reproducible medical AI evidence",
     "journal": "Medical Physics / IEEE JBHI",
     "status": "evidence complete - write now",
     "evidence": ["PROVENANCE_phase2/3", "REPRO_BUNDLE.json",
                  "release_gate"],
     "stats": ["hash verification", "bootstrap CI"]},
    {"id": "PAP-2",
     "title": "Unified clinical confidence from AI and physics uncertainty "
              "for proton therapy segmentation",
     "journal": "Physics in Medicine & Biology",
     "status": "evidence complete - write now",
     "evidence": ["confidence_analysis_results.json",
                  "uq_analysis_results.json", "inter_observer_study.json"],
     "stats": ["Wilcoxon", "bootstrap CI", "Dice/HD95"]},
    {"id": "PAP-3",
     "title": "Clinical validation and dose impact of AI proton "
              "segmentation: a real-data study",
     "journal": "Radiotherapy & Oncology",
     "status": "protocol - needs dose bridge (B) + real data (D)",
     "evidence": ["dose_bridge (stage B)", "real-data playbook runs "
                  "(stage D)"],
     "stats": ["paired DVH deltas", "TCP/NTCP"]},
]


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# SVP-001: Scientific Validation Plan", "",
             "## Document Control",
             "| ID | Version | Generated | Generator commit | Status |",
             "|---|---|---|---|---|",
             f"| SVP-001 | 1.0 | {now} | {git_commit()} | EFFECTIVE |", "",
             "## 1. Purpose",
             "Convert platform evidence into peer-reviewed credibility; "
             "order: PAP-1 and PAP-2 in parallel now, PAP-3 after stages "
             "B and D.", ""]
    for p in PAPERS:
        lines += [f"## {p['id']}: {p['title']}",
                  f"- Target: {p['journal']}", f"- Status: {p['status']}",
                  "- Evidence: " + ", ".join(p["evidence"]),
                  "- Statistics: " + ", ".join(p["stats"]), ""]
    lines += ["## 4. Integrity (non-negotiable)",
              "- Preregister PAP-3 protocol before first real-data run.",
              "- No p-hacking: primary endpoints fixed (Dice/HD95, paired "
              "DVH deltas).",
              "- Negative results published as deviations, never hidden.",
              "", "## 5. Traceability",
              "NEXUS-PRD-001, PRM-001 (R-106), MSS-001, ADR-006, ADR-007, "
              "RPT-001 v4.0.", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    ready = sum(1 for p in PAPERS if "write now" in p["status"])
    print(f"SVP-001: papers={len(PAPERS)} ready_to_write={ready}")
    print("Saved -> docs/product/SVP-001_SCIENTIFIC_VALIDATION.md")


if __name__ == "__main__":
    main()
