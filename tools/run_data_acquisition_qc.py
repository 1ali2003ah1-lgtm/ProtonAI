"""P4-S3: executable acquisition QC gate (DATA-ACQ-001).

Usage: python tools/run_data_acquisition_qc.py SERIES_DIR [DATASET_ID]
Checks: de-id gate, completeness, HU air calibration (conditional on
air presence), contour presence. Writes acquisition_qc_<id>.json and
appends one row per id to DATASET_REGISTER.md (controlled ledger).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from real_data_adapter import (PrivacyGateError, ingest_real_series,  # noqa: E402
                               scan_dicom_dir)

REGISTER = ROOT / "docs" / "quality_system" / "iso_13485" / \
    "DATASET_REGISTER.md"
MIN_SLICES = 8
REGISTER_HEADER = ("# DATASET REGISTER (controlled ledger)\n"
                   "| Dataset ID | Date | Source | DeID | Complete | HU | "
                   "Contours | Decision |\n|---|---|---|---|---|---|---|---|\n")


def hu_air_check(hu):
    air = hu[hu < -500]
    if air.size / hu.size < 0.01:
        return "N/A (no air region)", True
    mean_air = float(air.mean())
    return f"air mean={mean_air:.1f}", abs(mean_air + 1000) <= 150


def contour_presence(series_dir):
    gt = series_dir / "ground_truth" / "masks.npy"
    rt = list(series_dir.glob("*RTSTRUCT*"))
    return gt.exists() or len(rt) > 0


def run_checks(series_dir):
    series_dir = Path(series_dir)
    checks = {}
    try:
        ingest_real_series(series_dir, allow_phi=False)
        checks["deid_gate"] = "PASS"
    except PrivacyGateError:
        checks["deid_gate"] = "FAIL"
    except FileNotFoundError:
        checks["deid_gate"] = "FAIL(no slices)"
    slices = scan_dicom_dir(series_dir) if series_dir.is_dir() else []
    checks["completeness"] = ("PASS" if len(slices) >= MIN_SLICES
                              else f"FAIL({len(slices)}<{MIN_SLICES})")
    hu_note, hu_ok = "N/A (no slices)", True
    if slices:
        from dicom_reader import DicomReader
        reader = DicomReader(metadata_keys=["PatientID"])
        hu = np.stack([np.asarray(reader.read(p)["pixels"], dtype=float)
                       for p in slices])
        hu_note, hu_ok = hu_air_check(hu)
    checks["hu_air_calibration"] = ("PASS" if hu_ok else "FAIL") + f" [{hu_note}]"
    checks["contour_presence"] = ("PASS" if (slices and contour_presence(series_dir))
                                  else "FAIL")
    decision = ("REJECT" if any(c.startswith("FAIL") for c in checks.values())
                else "ACCEPT")
    return checks, decision


def main(series_arg, dataset_id):
    series_dir = Path(series_arg)
    checks, decision = run_checks(series_dir)
    report = {"dataset_id": dataset_id, "source_dir": str(series_dir),
              "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
              "checks": checks, "decision": decision}
    out = ROOT / f"acquisition_qc_{dataset_id}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    reg = REGISTER.read_text(encoding="utf-8") if REGISTER.exists() \
        else REGISTER_HEADER
    if f"| {dataset_id} |" not in reg:
        reg += (f"| {dataset_id} | {report['generated']} | {series_dir.name} | "
                f"{checks['deid_gate']} | {checks['completeness']} | "
                f"{checks['hu_air_calibration']} | {checks['contour_presence']} | "
                f"{decision} |\n")
        REGISTER.parent.mkdir(parents=True, exist_ok=True)
        REGISTER.write_text(reg, encoding="utf-8")
    print(f"QC {dataset_id}: {decision} | "
          + "; ".join(f"{k}={v}" for k, v in checks.items()))
    print(f"Saved -> {out.name}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else Path(sys.argv[1]).name)
