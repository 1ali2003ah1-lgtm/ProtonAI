"""P2-S1/P2-S3: experiment through the validated ingestion path.

Usage: python tools/run_pipeline_experiment.py [SERIES] [OUT_JSON]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from dicom_reader import DicomReader  # noqa: E402
from torch_segmenter import TorchSegmenter as Baseline  # noqa: E402
from experimental_segmenter import TorchSegmenter as Experiment  # noqa: E402
import seg_metrics  # noqa: E402

EPOCHS = 40


def ingest(series: Path):
    reader = DicomReader(metadata_keys=["PatientID", "Modality"])
    slices = sorted(series.glob("*.dcm"))
    if not slices:
        raise FileNotFoundError(f"No .dcm slices in {series}; run tools/make_synthetic_dicom.py first")
    hu = np.stack([np.asarray(reader.read(p)["pixels"], dtype=float) for p in slices])
    masks = np.load(series / "ground_truth" / "masks.npy").astype(float)
    assert hu.shape == masks.shape, f"ingestion/ground-truth mismatch: {hu.shape} vs {masks.shape}"
    return hu, masks


def evaluate(Cls, hu, masks):
    dices = []
    for z in range(hu.shape[0]):
        model = Cls(seed=42)
        model.fit(hu[z], masks[z], epochs=EPOCHS)
        pred = model.segment(hu[z])
        dices.append(seg_metrics.dice(pred, masks[z]))
    return float(np.mean(dices)), dices


def main(series_name: str, out_name: str):
    hu, masks = ingest(Path("data/synth_ct") / series_name)
    base_mean, base_per = evaluate(Baseline, hu, masks)
    exp_mean, exp_per = evaluate(Experiment, hu, masks)
    delta = exp_mean - base_mean
    verdict = "HYPOTHESIS SUPPORTED" if delta > 0 else "NO IMPROVEMENT"
    print(f"===== PIPELINE EXPERIMENT ({series_name}) =====")
    print(f"baseline   (CE)      mean Dice = {base_mean:.4f}")
    print(f"experiment (Dice+CE) mean Dice = {exp_mean:.4f}")
    print(f"delta = {delta:+.4f}   VERDICT: {verdict}")
    out = {"series": series_name,
           "baseline_mean_dice": base_mean,
           "experiment_mean_dice": exp_mean,
           "baseline_per_case": base_per,
           "experiment_per_case": exp_per,
           "delta": delta, "verdict": verdict}
    Path(out_name).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Saved -> {out_name}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "SYNTH-001",
         sys.argv[2] if len(sys.argv) > 2 else "pipeline_experiment_results.json")
