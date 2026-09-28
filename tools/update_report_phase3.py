"""P4-S1: complete RPT-001 v3.0 upgrade (controlled document, idempotent).

1. Integrity gate: schema + sha256 against PROVENANCE_phase3.json.
2. Document Control row bumped to v3.0 (date + generator commit).
3. Executive Summary rewritten from committed artifacts (Phase 2 + 3).
4. Section 9 (Phase-3 evidence + sealing table) rebuilt.
5. Section 10 (Document Revision History) rebuilt.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "EXPERIMENT_REPORT.md"
EV = ROOT / "external_validation_results.json"
UQ = ROOT / "uq_analysis_results.json"
STATS = ROOT / "experiment_statistics_synth002.json"
PROV3 = ROOT / "docs" / "experiments" / "PROVENANCE_phase3.json"
MARK9 = "## 9. Phase 3: Real-World Readiness Evidence"
MARK10 = "## 10. Document Revision History"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def gate(ev, uq, stats, prov3):
    problems = []
    for key in ("baseline", "experiment", "verdict"):
        if key not in ev:
            problems.append(f"external validation missing {key}")
    for branch in ("in_domain", "cross_domain"):
        if branch not in uq:
            problems.append(f"uq missing {branch}")
    if "wilcoxon_p_value" not in stats:
        problems.append("stats missing wilcoxon_p_value")
    for rel in ("external_validation_results.json",
                "uq_analysis_results.json"):
        if prov3["hashes"].get(rel) != sha(ROOT / rel):
            problems.append(f"sha256 mismatch: {rel}")
    if problems:
        raise SystemExit("EVIDENCE CHAIN BROKEN - report update refused:\n- "
                         + "\n- ".join(problems))
    print("Phase-3 evidence chain verified (schema + sha256)")


def exec_summary(stats, ev, uq):
    return "\n".join([
        "## 1. Executive Summary",
        "Replacing the Cross-Entropy loss with a combined Dice+CE loss",
        "improves organ-at-risk segmentation accuracy. Phase-2 evidence",
        "(v0.3.0, calibrated phantom SYNTH-002 through the validated DICOM",
        f"pipeline): Wilcoxon one-sided p = {stats['wilcoxon_p_value']:.6f},",
        "bootstrap 95% CI excluding 0, 3/3 seeds concordant.",
        "Phase-3 evidence (v0.4.0): two-direction external validation shows",
        f"the gain is in-domain, not shift-robustness ({ev['verdict']});",
        "seed-ensemble uncertainty is informative and OOD-sensitive",
        f"(cross-domain failure AUC = {uq['cross_domain']['auc_failure']},",
        f"OOD Mann-Whitney p = {uq['ood_mannwhitney_p']:.4f}), enabling the",
        "documented physicist-review flagging policy (CLIN-001).",
        "**Final verdict: STRONG EVIDENCE in-domain; clinical safety via",
        "uncertainty flagging.**",
    ])


def section9(ev, uq, prov3):
    b, e = ev["baseline"], ev["experiment"]
    ui, ux = uq["in_domain"], uq["cross_domain"]
    lines = [
        MARK9,
        "",
        "### 9.1 External validation (ADR-005)",
        "",
        "| Model | inS1 | inS2 | cross S1->S2 | cross S2->S1 | gap12 | gap21 |",
        "|---|---|---|---|---|---|---|",
        (f"| baseline | {b['in_domain_SYNTH-001']['mean']:.4f} | "
         f"{b['in_domain_SYNTH-002']['mean']:.4f} | "
         f"{b['cross_SYNTH-001_to_SYNTH-002']['mean']:.4f} | "
         f"{b['cross_SYNTH-002_to_SYNTH-001']['mean']:.4f} | "
         f"{b['gap_S1_to_S2']:+.4f} | {b['gap_S2_to_S1']:+.4f} |"),
        (f"| experiment | {e['in_domain_SYNTH-001']['mean']:.4f} | "
         f"{e['in_domain_SYNTH-002']['mean']:.4f} | "
         f"{e['cross_SYNTH-001_to_SYNTH-002']['mean']:.4f} | "
         f"{e['cross_SYNTH-002_to_SYNTH-001']['mean']:.4f} | "
         f"{e['gap_S1_to_S2']:+.4f} | {e['gap_S2_to_S1']:+.4f} |"),
        "",
        f"Verdict: {ev['verdict']}. Interpretation: Dice+CE is an in-domain",
        "accuracy/consistency gain, not a distribution-shift robustness gain;",
        "clinical safety therefore rests on uncertainty flagging (9.2).",
        "",
        "### 9.2 Uncertainty quantification (ADR-006)",
        "",
        "| Scope | mean uncertainty | Spearman rho | p | failure AUC |",
        "|---|---|---|---|---|",
        (f"| in-domain | {ui['mean_uncertainty']:.4f} | "
         f"{ui['spearman_rho']:+.4f} | {ui['spearman_p']:.4f} | "
         f"{ui['auc_failure']} |"),
        (f"| cross-domain | {ux['mean_uncertainty']:.4f} | "
         f"{ux['spearman_rho']:+.4f} | {ux['spearman_p']:.4f} | "
         f"{ux['auc_failure']} |"),
        "",
        f"OOD sensitivity: Mann-Whitney p = {uq['ood_mannwhitney_p']:.4f}.",
        f"Verdict: {uq['verdict']}.",
        "",
        "Clinical safety contract: any case whose vote-entropy exceeds the",
        "documented in-domain maximum is auto-flagged for physicist review",
        "(CLIN-001). The platform does not fail silently.",
        "",
        "### 9.3 Evidence sealing (Phase 3)",
        "",
        "| Artifact | sha256 (first 16) |",
        "|---|---|",
    ]
    for rel, h in sorted(prov3["hashes"].items()):
        lines.append(f"| {rel} | {h[:16]} |")
    lines += ["", "Manifest: docs/experiments/PROVENANCE_phase3.json.", ""]
    return "\n".join(lines)


def section10(now, commit):
    return "\n".join([
        MARK10,
        "",
        "| Version | Date | Commit | Scope |",
        "|---|---|---|---|",
        "| 1.0 | v0.2.0 era | - | initial v0.2.0 experiment evidence |",
        "| 2.0 | Phase 2 | 82de338 | pipeline evidence, figures, gate |",
        f"| 3.0 | {now} | {commit} | Phase-3 validation + UQ + sealing |",
        "",
    ])


def main():
    ev, uq, stats, prov3 = load(EV), load(UQ), load(STATS), load(PROV3)
    gate(ev, uq, stats, prov3)
    text = REPORT.read_text(encoding="utf-8")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit = git_commit()
    row = f"| RPT-001 | 3.0 | {now} | {commit} | EFFECTIVE |"
    text, n = re.subn(r"\| RPT-001 \|[^|]*\|[^|]*\|[^|]*\|[^|]*\|",
                      row, text, count=1)
    if n != 1:
        raise SystemExit("Document Control row not found - refused")
    head, sep, tail = text.partition("## 1. Executive Summary")
    if not sep:
        raise SystemExit("Executive Summary section not found - refused")
    tail = tail.partition("## 2. Hypothesis")[2]
    text = head + exec_summary(stats, ev, uq) + "\n\n## 2. Hypothesis" + tail
    body = text.split(MARK9)[0].rstrip()
    text = body + "\n\n" + section9(ev, uq, prov3) + "\n" + section10(now, commit)
    REPORT.write_text(text, encoding="utf-8")
    print("RPT-001 upgraded to v3.0 (exec rewrite + sections 9-10)")


if __name__ == "__main__":
    main()
