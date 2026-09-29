"""P5-S4: append Phase-5 section to EXPERIMENT_REPORT.md, bump to v4.0."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "EXPERIMENT_REPORT.md"
MARK11 = "## 11. Phase 5: Clinical Confidence & Real-Data Readiness"


def load(n):
    return json.loads((ROOT / n).read_text(encoding="utf-8"))


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    conf = load("confidence_analysis_results.json")
    io = load("inter_observer_study.json")
    rv = load("registered_validation_results.json")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit = git_commit()
    text = REPORT.read_text(encoding="utf-8")
    text, n = re.subn(r"\| RPT-001 \|[^|]*\|[^|]*\|[^|]*\|[^|]*\|",
                      f"| RPT-001 | 4.0 | {now} | {commit} | EFFECTIVE |",
                      text, count=1)
    if n != 1:
        raise SystemExit("Document Control row not found - refused")
    if "| 4.0 |" not in text:
        lines = text.split("\n")
        out = []
        for ln in lines:
            out.append(ln)
            if ln.startswith("| 3.0 |"):
                out.append(f"| 4.0 | {now} | {commit} | Phase-5 confidence "
                           f"+ registered validation |")
        text = "\n".join(out)
    rows = []
    for r in rv["datasets"]:
        wp = r.get("wilcoxon_p")
        rows.append(f"- {r['id']}: resident={r['resident']} "
                    f"seal={r['seal_intact']}"
                    + (f" exp Dice={r['mean_dice_experiment']:.4f} "
                       f"wilcoxon_p={wp:.4f} "
                       f"concordance={r['seed_concordance']:.2f}"
                       if r.get("mean_dice_experiment") else " (seal-only)"))
    section = "\n".join([
        MARK11, "",
        "### 11.1 Unified clinical confidence (ADR-007)",
        f"- Physics confidence: {conf['physics_confidence']:.6f}",
        f"- Threshold C (min in-domain): {conf['threshold_C']:.6f}",
        f"- Cross-domain failures captured: {conf['failures_captured']}",
        f"- Verdict: {conf['verdict']}", "",
        "### 11.2 Inter-observer agreement suite (DATA-ACQ-001 s6)",
        f"- Primary mean Dice: {io['mean_dice']:.4f} "
          f"(CI95 {io['ci95_dice'][0]:.4f}-{io['ci95_dice'][1]:.4f})",
        f"- Mean HD95: {io['mean_hd95']:.2f} mm; verdict: {io['verdict']}", "",
        "### 11.3 Intake infrastructure & power progress",
        "- Manifest-driven intake with selective sealing, audit trail,",
        "  dry-run (P5-S3). Power: n_min=19, target=30 paired volumes.", "",
        "### 11.4 Registered validation readiness",
        f"- Readiness: {rv['readiness']}",
    ] + rows + [""])
    if MARK11 in text:
        text = text.split(MARK11)[0].rstrip() + "\n\n" + section
    else:
        text = text.rstrip() + "\n\n" + section
    REPORT.write_text(text, encoding="utf-8")
    print("Phase-5 section appended; RPT-001 bumped to v4.0")


if __name__ == "__main__":
    main()
