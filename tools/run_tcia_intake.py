"""P5-S3: manifest-driven real-data intake (DATA-ACQ-001) - hardened.

ACCEPTED datasets are content-sealed (schema v2); REJECTED ones never
enter the evidence chain. Append-only audit trail; dry-run mode;
statistical-power progress tracking.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from power_analysis import paired_n  # noqa: E402
from run_data_acquisition_qc import REGISTER, ROOT as QC_ROOT, main as qc_main  # noqa: E402

POWER_TARGET = 30


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def validate_manifest(m):
    problems = []
    entries = m.get("entries")
    if not isinstance(entries, list) or not entries:
        raise SystemExit("manifest must contain non-empty 'entries'")
    ids = [e.get("dataset_id") for e in entries]
    if len(set(ids)) != len(ids):
        problems.append("dataset_id duplicated")
    if any(not i for i in ids):
        problems.append("dataset_id missing")
    problems += [f"entry {e.get('dataset_id')} missing path"
                 for e in entries if not e.get("path")]
    if problems:
        raise SystemExit("manifest invalid: " + "; ".join(problems))


def seal_dataset(series_dir, dataset_id, qc_report_path, seal_dir):
    import pydicom
    hashes = {}
    for p in sorted(Path(series_dir).glob("*.dcm")):
        hashes[f"slices/{p.name}"] = hashlib.sha256(
            pydicom.dcmread(str(p)).pixel_array.tobytes()).hexdigest()
    gt = Path(series_dir) / "ground_truth" / "masks.npy"
    if gt.exists():
        hashes["ground_truth/masks.npy"] = sha(gt)
    hashes["qc_report"] = sha(qc_report_path)
    out = Path(seal_dir) / f"PROVENANCE_{dataset_id}.json"
    out.write_text(json.dumps({"dataset_id": dataset_id, "schema": 2,
                               "hashes": hashes}, indent=2, sort_keys=True),
                   encoding="utf-8")
    return out


def process_manifest(manifest_path, register=REGISTER, report_dir=QC_ROOT,
                     summary_path=ROOT / "intake_summary.json",
                     seal_dir=ROOT / "docs" / "experiments",
                     audit_path=ROOT / "intake_audit.json",
                     dry_run=False):
    m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    validate_manifest(m)
    results = []
    audit = json.loads(audit_path.read_text(encoding="utf-8")) \
        if audit_path.exists() else []
    for e in m["entries"]:
        checks, decision = qc_main(e["path"], e["dataset_id"],
                                   register=register, report_dir=report_dir,
                                   dry_run=dry_run)
        sealed = None
        if decision == "ACCEPT" and not dry_run:
            sealed = seal_dataset(
                e["path"], e["dataset_id"],
                report_dir / f"acquisition_qc_{e['dataset_id']}.json",
                seal_dir).name
        if not dry_run:
            audit.append({
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "dataset_id": e["dataset_id"],
                "source": e.get("source", ""),
                "decision": decision,
                "qc_report_sha256": sha(report_dir /
                                        f"acquisition_qc_{e['dataset_id']}.json"),
                "sealed_manifest": sealed})
        results.append({"dataset_id": e["dataset_id"],
                        "source": e.get("source", ""),
                        "decision": decision, "sealed": sealed})
    if not dry_run:
        audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    reg_text = register.read_text(encoding="utf-8") if register.exists() else ""
    accepted_total = reg_text.count("| ACCEPT |")
    summary = {"processed": len(results),
               "accept": sum(r["decision"] == "ACCEPT" for r in results),
               "reject": sum(r["decision"] == "REJECT" for r in results),
               "dry_run": dry_run,
               "power_progress": {"accepted_total": accepted_total,
                                  "n_min": paired_n(), "target": POWER_TARGET},
               "entries": results}
    if not dry_run:
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"INTAKE{' (dry-run)' if dry_run else ''}: "
          f"processed={summary['processed']} accept={summary['accept']} "
          f"reject={summary['reject']}")
    print(f"power progress: {accepted_total} accepted / "
          f"n_min={paired_n()} / target={POWER_TARGET}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    process_manifest(a.manifest, dry_run=a.dry_run)
