"""P6-S3: one-command real-data evidence pipeline (PLAYBOOK-001).

Flow: manifest -> intake (QC + selective seal + audit) -> if ACCEPT and
not dry-run: registered validation with the new dataset's path.
REJECT halts the evidence chain (the gate doing its job).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from run_data_acquisition_qc import REGISTER  # noqa: E402
from run_registered_validation import run as registered_run  # noqa: E402
from run_tcia_intake import process_manifest  # noqa: E402


NI_MARGIN = 0.05


def feedback_verdict(exp_dice, baseline_ref, margin=NI_MARGIN):
    if exp_dice is None or baseline_ref is None:
        return "N/A"
    return ("WITHIN_BASELINE" if exp_dice >= baseline_ref - margin
            else "BELOW_BASELINE")


def _baseline_ref():
    p = ROOT / "registered_validation_results.json"
    if not p.exists():
        return None
    rv = json.loads(p.read_text(encoding="utf-8"))
    for r in rv.get("datasets", []):
        if r.get("id") == "DATASET-000-SYNTH-REF":
            return r.get("mean_dice_experiment")
    return None


def _append_feedback(dataset_id, decision, validation, ledger_path=None):
    from datetime import datetime, timezone
    ledger = Path(ledger_path) if ledger_path else ROOT / "pms_ledger.json"
    rows = json.loads(ledger.read_text(encoding="utf-8")) \
        if ledger.exists() else []
    ref = _baseline_ref()
    exp = (validation or {}).get("mean_dice_experiment")
    rows.append({"kind": "playbook",
                 "generated": datetime.now(timezone.utc)
                 .strftime("%Y-%m-%d %H:%M UTC"),
                 "dataset_id": dataset_id,
                 "intake_decision": decision,
                 "exp_dice": exp,
                 "wilcoxon_p": (validation or {}).get("wilcoxon_p"),
                 "baseline_ref": ref, "ni_margin": NI_MARGIN,
                 "verdict": ("N/A (rejected at intake)"
                             if decision != "ACCEPT"
                             else feedback_verdict(exp, ref))})
    ledger.write_text(json.dumps(rows[-100:], indent=2),
                      encoding="utf-8")


def run_playbook(series_dir, dataset_id, dry_run=False, register=REGISTER,
                 report_dir=None, seal_dir=None, audit_path=None,
                 summary_path=None, out_path=None,
                 feedback_ledger=None):
    series_dir = Path(series_dir)
    report_dir = Path(report_dir or ROOT)
    seal_dir = Path(seal_dir or ROOT / "docs" / "experiments")
    audit_path = Path(audit_path or ROOT / "intake_audit.json")
    summary_path = Path(summary_path or ROOT / "intake_summary.json")
    out_path = Path(out_path or ROOT / f"real_data_playbook_{dataset_id}.json")
    mpath = report_dir / f"_manifest_{dataset_id}.json"
    mpath.write_text(json.dumps({"entries": [
        {"dataset_id": dataset_id, "path": str(series_dir),
         "source": "playbook"}]}), encoding="utf-8")
    s = process_manifest(mpath, register=register, report_dir=report_dir,
                         summary_path=summary_path, seal_dir=seal_dir,
                         audit_path=audit_path, dry_run=dry_run)
    decision = s["entries"][0]["decision"]
    validation = None
    if decision == "ACCEPT" and not dry_run:
        full = registered_run(extra_paths={dataset_id: series_dir},
                              write=False, seal_dir=seal_dir,
                              report_dir=report_dir)
        validation = {r["id"]: r for r in full["datasets"]}.get(dataset_id)
    result = {"dataset_id": dataset_id, "dry_run": dry_run,
              "intake_decision": decision, "validation": validation}
    if not dry_run:
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        _append_feedback(dataset_id, decision, validation, feedback_ledger)
    print(f"PLAYBOOK {dataset_id}: intake={decision}"
          + (f" exp Dice={validation['mean_dice_experiment']:.4f} "
             f"wilcoxon_p={validation['wilcoxon_p']} "
             f"concord={validation['seed_concordance']}"
             if validation else " (evidence chain halted)"))
    if not dry_run:
        print(f"Saved -> {out_path.name}")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("series_dir")
    ap.add_argument("dataset_id")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    run_playbook(a.series_dir, a.dataset_id, dry_run=a.dry_run)
