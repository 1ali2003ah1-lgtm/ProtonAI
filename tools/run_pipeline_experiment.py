"""P2-S1: scientific experiment executed through the validated ingestion path.

Data path (production-equivalent):
    DICOM slices -> DicomReader.read() -> HU pixels
    ground-truth masks -> labels
Models: baseline (CE) vs experiment (Dice+CE), trained per slice.
Metrics: seg_metrics.dice per case; mean + delta + verdict.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Repo-root on sys.path: tools/ scripts must import root modules.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from dicom_reader import DicomReader  # noqa: E402
from torch_segmenter import TorchSegmenter as Baseline  # noqa: E402
from experimental_segmenter import TorchSegmenter as Experiment  # noqa: E402
import seg_metrics  # noqa: E402

SERIES = Path("data/synth_ct/SYNTH-001")
GT = SERIES / "ground_truth"
EPOCHS = 40


def ingest():
    reader = DicomReader(metadata_keys=["PatientID", "Modality"])
    slices = sorted(SERIES.glob("*.dcm"))
    hu = np.stack([np.asarray(reader.read(p)["pixels"], dtype=float) for p in slices])
    masks = np.load(GT / "masks.npy").astype(float)
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


def main():
    hu, masks = ingest()
    base_mean, base_per = evaluate(Baseline, hu, masks)
    exp_mean, exp_per = evaluate(Experiment, hu, masks)
    delta = exp_mean - base_mean
    verdict = "HYPOTHESIS SUPPORTED" if delta > 0 else "NO IMPROVEMENT"
    print("===== PIPELINE EXPERIMENT (via v0.2.0-ingestion) =====")
    print(f"baseline   (CE)      mean Dice = {base_mean:.4f}")
    print(f"experiment (Dice+CE) mean Dice = {exp_mean:.4f}")
    print(f"delta = {delta:+.4f}   VERDICT: {verdict}")
    out = {"pipeline": "v0.2.0-ingestion",
           "baseline_mean_dice": base_mean,
           "experiment_mean_dice": exp_mean,
           "baseline_per_case": base_per,
           "experiment_per_case": exp_per,
           "delta": delta, "verdict": verdict}
    Path("pipeline_experiment_results.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print("Saved -> pipeline_experiment_results.json")


if __name__ == "__main__":
    main()
