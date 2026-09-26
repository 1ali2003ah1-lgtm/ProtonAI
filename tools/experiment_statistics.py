"""P2-S2/P2-S4: statistical significance for pipeline experiments.

Usage: python tools/experiment_statistics.py [SERIES] [OUT_JSON]

Methods (ADR-003):
1. Wilcoxon signed-rank test (non-parametric, paired, one-sided greater)
2. Bootstrap 95% confidence interval (10,000 resamples, seed-fixed)
3. Multi-seed robustness check (seeds: 42, 123, 999)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from scipy import stats

from dicom_reader import DicomReader  # noqa: E402
from torch_segmenter import TorchSegmenter as Baseline  # noqa: E402
from experimental_segmenter import TorchSegmenter as Experiment  # noqa: E402
import seg_metrics  # noqa: E402

EPOCHS = 40
SEEDS = [42, 123, 999]
N_BOOTSTRAP = 10_000


def ingest(series: Path):
    reader = DicomReader(metadata_keys=["PatientID", "Modality"])
    slices = sorted(series.glob("*.dcm"))
    hu = np.stack([np.asarray(reader.read(p)["pixels"], dtype=float) for p in slices])
    masks = np.load(series / "ground_truth" / "masks.npy").astype(float)
    assert hu.shape == masks.shape, f"ingestion/ground-truth mismatch"
    return hu, masks


def evaluate_per_case(Cls, hu, masks, seed):
    dices = []
    for z in range(hu.shape[0]):
        model = Cls(seed=seed)
        model.fit(hu[z], masks[z], epochs=EPOCHS)
        pred = model.segment(hu[z])
        dices.append(seg_metrics.dice(pred, masks[z]))
    return np.array(dices)


def bootstrap_ci(differences, n_bootstrap=N_BOOTSTRAP, alpha=0.05):
    rng = np.random.default_rng(42)
    means = [rng.choice(differences, size=len(differences), replace=True).mean()
             for _ in range(n_bootstrap)]
    return (float(np.percentile(means, 100 * alpha / 2)),
            float(np.percentile(means, 100 * (1 - alpha / 2))))


def main(series_name: str, out_name: str):
    hu, masks = ingest(Path("data/synth_ct") / series_name)
    print(f"===== STATISTICAL ANALYSIS ({series_name}) - ADR-003 =====")
    base = evaluate_per_case(Baseline, hu, masks, seed=42)
    exp = evaluate_per_case(Experiment, hu, masks, seed=42)
    diffs = exp - base
    stat, p = stats.wilcoxon(exp, base, alternative="greater")
    ci_lo, ci_hi = bootstrap_ci(diffs)
    print(f"Wilcoxon stat={stat:.4f} p={p:.6f} "
          f"significant(p<0.05)={'YES' if p < 0.05 else 'NO'}")
    print(f"Bootstrap 95% CI=[{ci_lo:+.6f}, {ci_hi:+.6f}] "
          f"excludes0={'YES' if (ci_lo > 0 or ci_hi < 0) else 'NO'}")
    verdicts = []
    for seed in SEEDS:
        b = evaluate_per_case(Baseline, hu, masks, seed)
        e = evaluate_per_case(Experiment, hu, masks, seed)
        d = float(e.mean() - b.mean())
        v = "SUPPORTED" if d > 0 else "NO IMPROVEMENT"
        verdicts.append(v)
        print(f"seed {seed}: delta={d:+.6f} => {v}")
    robust = len(set(verdicts)) == 1
    if p < 0.05 and (ci_lo > 0 or ci_hi < 0) and robust:
        final = "STRONG EVIDENCE: HYPOTHESIS SUPPORTED"
    elif p < 0.05 or (ci_lo > 0 or ci_hi < 0):
        final = "MODERATE EVIDENCE: HYPOTHESIS SUPPORTED"
    else:
        final = "INSUFFICIENT EVIDENCE"
    print(f"FINAL: {final}")
    out = {"series": series_name,
           "wilcoxon_statistic": float(stat),
           "wilcoxon_p_value": float(p),
           "significant_p": bool(p < 0.05),
           "bootstrap_ci_lower": ci_lo,
           "bootstrap_ci_upper": ci_hi,
           "ci_excludes_zero": bool(ci_lo > 0 or ci_hi < 0),
           "multi_seed_verdicts": verdicts,
           "robust_across_seeds": robust,
           "final_verdict": final,
           "per_case_differences": diffs.tolist()}
    Path(out_name).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Saved -> {out_name}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "SYNTH-001",
         sys.argv[2] if len(sys.argv) > 2 else "experiment_statistics.json")
