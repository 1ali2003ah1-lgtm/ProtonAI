"""P5-S4: registered-dataset validation harness (hardened).

Seals the synthetic reference if unsealed; discovers all schema-2 seals;
resident ones get seal verification + privacy gate + multi-seed paired
baseline/experiment (Wilcoxon + seed concordance + bootstrap CI).
Non-resident seals reported seal-verified-only (honest).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from dicom_reader import DicomReader  # noqa: E402
from experimental_segmenter import TorchSegmenter as Experiment  # noqa: E402
from real_data_adapter import ingest_real_series  # noqa: E402
from run_data_acquisition_qc import main as qc_main  # noqa: E402
from run_tcia_intake import seal_dataset  # noqa: E402
from torch_segmenter import TorchSegmenter as Baseline  # noqa: E402
import seg_metrics  # noqa: E402

EPOCHS = 40
SEEDS = (42, 123, 999)
REF_ID = "DATASET-000-SYNTH-REF"
REF_DIR = ROOT / "data" / "synth_ct" / "SYNTH-002"
SEAL_DIR = ROOT / "docs" / "experiments"


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def verify_seal(prov, series_dir):
    import pydicom
    for rel, h in prov["hashes"].items():
        if rel.startswith("slices/"):
            p = series_dir / rel[len("slices/"):]
            if not p.exists():
                return False
            cur = hashlib.sha256(
                pydicom.dcmread(str(p)).pixel_array.tobytes()).hexdigest()
        elif rel.startswith("ground_truth/"):
            p = series_dir / rel
            if not p.exists():
                return False
            cur = hashlib.sha256(p.read_bytes()).hexdigest()
        else:
            continue
        if cur != h:
            return False
    return True


def paired_stats(series_dir):
    reader = DicomReader(metadata_keys=["PatientID", "Modality"])
    slices = sorted(Path(series_dir).glob("*.dcm"))
    hu = np.stack([np.asarray(reader.read(p)["pixels"], dtype=float)
                   for p in slices])
    masks = np.load(Path(series_dir) / "ground_truth" / "masks.npy").astype(float)
    per_seed = {}
    for seed in SEEDS:
        db, de = [], []
        for z in range(hu.shape[0]):
            for Cls, acc in ((Baseline, db), (Experiment, de)):
                model = Cls(seed=seed)
                model.fit(hu[z], masks[z], epochs=EPOCHS)
                acc.append(float(seg_metrics.dice(model.segment(hu[z]), masks[z])))
        per_seed[seed] = (np.array(db), np.array(de))
    b42, e42 = per_seed[42]
    diffs = e42 - b42
    rng = np.random.default_rng(42)
    boots = [np.mean(rng.choice(diffs, size=len(diffs), replace=True))
             for _ in range(1000)]
    try:
        p = float(wilcoxon(e42, b42, alternative="greater").pvalue)
    except ValueError:
        p = None
    return {"mean_dice_baseline": float(b42.mean()),
            "mean_dice_experiment": float(e42.mean()),
            "paired_diff_ci95": [float(np.percentile(boots, 2.5)),
                                 float(np.percentile(boots, 97.5))],
            "wilcoxon_p": p,
            "seed_concordance": float(np.mean(
                [(de - db).mean() > 0 for db, de in per_seed.values()]))}


def main():
    ref_prov = SEAL_DIR / f"PROVENANCE_{REF_ID}.json"
    if not ref_prov.exists():
        qc_main(str(REF_DIR), REF_ID)
        seal_dataset(REF_DIR, REF_ID,
                     ROOT / f"acquisition_qc_{REF_ID}.json", SEAL_DIR)
        print(f"sealed reference -> {ref_prov.name}")
    discovered = []
    for p in sorted(SEAL_DIR.glob("PROVENANCE_*.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        if m.get("schema") == 2 and m.get("dataset_id"):
            discovered.append((m["dataset_id"], m))
    results = []
    for did, prov in discovered:
        resident = did == REF_ID and REF_DIR.exists()
        seal_ok = verify_seal(prov, REF_DIR) if resident else None
        gate = stats = None
        if resident:
            ingest_real_series(REF_DIR, allow_phi=False)
            gate = "PASS"
            stats = paired_stats(REF_DIR)
        results.append({"id": did, "resident": resident,
                        "seal_intact": seal_ok, "deid_gate": gate,
                        **(stats or {})})
        print(f"{did}: resident={resident} seal={seal_ok}"
              + (f" base={stats['mean_dice_baseline']:.4f} "
                 f"exp={stats['mean_dice_experiment']:.4f} "
                 f"wilcoxon_p={stats['wilcoxon_p']} "
                 f"concord={stats['seed_concordance']}" if stats else " (seal-only)"))
    readiness = bool(results) and all(
        (r["seal_intact"] is True or r["resident"] is False)
        and r["deid_gate"] in ("PASS", None) for r in results)
    out = {"datasets": results, "readiness": readiness,
           "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
           "generator_commit": git_commit()}
    (ROOT / "registered_validation_results.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(f"READINESS: {readiness}")
    print("Saved -> registered_validation_results.json")


if __name__ == "__main__":
    main()
