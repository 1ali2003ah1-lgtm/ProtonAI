"""ProtonAI University Experiment - quantitative evaluation.
Compares baseline (CE loss) vs experiment (Dice+CE loss) via seg_metrics.
"""
import json
import numpy as np

from torch_segmenter import TorchSegmenter as Baseline
from experimental_segmenter import TorchSegmenter as Experiment
import seg_metrics


def make_case(seed):
    rng = np.random.default_rng(seed)
    hu = rng.normal(0.0, 10.0, size=(64, 64)).astype(np.float32)
    yy, xx = np.mgrid[0:64, 0:64]
    cy = 32 + int(rng.integers(-8, 9))
    cx = 32 + int(rng.integers(-8, 9))
    r = int(rng.integers(8, 14))
    mask = ((yy - cy) ** 2 + (xx - cx) ** 2) <= r ** 2
    hu[mask] += 300.0
    return hu, mask.astype(np.float32)


def evaluate(Cls, cases, epochs=40):
    dices, rep = [], None
    for hu, mask in cases:
        model = Cls(seed=42)
        model.fit(hu, mask, epochs=epochs)
        pred = model.segment(hu)
        dices.append(seg_metrics.dice(pred, mask))
        rep = seg_metrics.report(pred, mask)
    return float(np.mean(dices)), rep


cases = [make_case(s) for s in range(6)]
base_dice, base_rep = evaluate(Baseline, cases)
exp_dice, exp_rep = evaluate(Experiment, cases)

delta = exp_dice - base_dice
verdict = "HYPOTHESIS SUPPORTED" if delta > 0 else "NO IMPROVEMENT"

print("\n========== EXPERIMENT EVALUATION ==========")
print(f"baseline   (CE loss)      mean Dice = {base_dice:.4f}")
print(f"experiment (Dice+CE loss) mean Dice = {exp_dice:.4f}")
print(f"delta (experiment - baseline)        = {delta:+.4f}")
print(f"baseline   full report: {base_rep}")
print(f"experiment full report: {exp_rep}")
print(f"VERDICT: {verdict}")

with open("experiment_results.json", "w") as f:
    json.dump({"baseline_mean_dice": base_dice,
               "experiment_mean_dice": exp_dice,
               "delta": delta, "verdict": verdict,
               "baseline_report": base_rep,
               "experiment_report": exp_rep}, f, indent=2, default=str)
print("Saved -> experiment_results.json")
