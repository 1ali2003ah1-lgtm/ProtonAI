"""P2-S2: Statistical significance analysis for pipeline experiment results.

Methods (ADR-003):
1. Wilcoxon signed-rank test (non-parametric, paired differences)
2. Bootstrap 95% confidence interval (10,000 resamples)
3. Multi-seed robustness check (seeds: 42, 123, 999)

Acceptance criteria:
- Wilcoxon p-value < 0.05 => statistically significant
- Bootstrap CI does NOT contain 0 => robust difference
- Multi-seed: all seeds show same verdict => not initialization-dependent
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from scipy import stats

from dicom_reader import DicomReader
from torch_segmenter import TorchSegmenter as Baseline
from experimental_segmenter import TorchSegmenter as Experiment
import seg_metrics

SERIES = Path("data/synth_ct/SYNTH-001")
GT = SERIES / "ground_truth"
EPOCHS = 40
SEEDS = [42, 123, 999]
N_BOOTSTRAP = 10_000


def ingest():
    reader = DicomReader(metadata_keys=["PatientID", "Modality"])
    slices = sorted(SERIES.glob("*.dcm"))
    hu = np.stack([np.asarray(reader.read(p)["pixels"], dtype=float) for p in slices])
    masks = np.load(GT / "masks.npy").astype(float)
    return hu, masks


def evaluate_per_case(Cls, hu, masks, seed):
    dices = []
    for z in range(hu.shape[0]):
        model = Cls(seed=seed)
        model.fit(hu[z], masks[z], epochs=EPOCHS)
        pred = model.segment(hu[z])
        dices.append(seg_metrics.dice(pred, masks[z]))
    return np.array(dices)


def wilcoxon_test(base_dices, exp_dices):
    stat, p_value = stats.wilcoxon(exp_dices, base_dices, alternative='greater')
    return float(stat), float(p_value)


def bootstrap_ci(differences, n_bootstrap=N_BOOTSTRAP, alpha=0.05):
    rng = np.random.default_rng(42)
    means = []
    for _ in range(n_bootstrap):
        sample = rng.choice(differences, size=len(differences), replace=True)
        means.append(sample.mean())
    lower = np.percentile(means, 100 * alpha / 2)
    upper = np.percentile(means, 100 * (1 - alpha / 2))
    return float(lower), float(upper)


def main():
    hu, masks = ingest()
    
    print("===== STATISTICAL ANALYSIS (ADR-003) =====\n")
    
    # Seed 42 (primary)
    print("[Seed 42 - Primary]")
    base_dices = evaluate_per_case(Baseline, hu, masks, seed=42)
    exp_dices = evaluate_per_case(Experiment, hu, masks, seed=42)
    differences = exp_dices - base_dices
    
    wilcoxon_stat, wilcoxon_p = wilcoxon_test(base_dices, exp_dices)
    ci_lower, ci_upper = bootstrap_ci(differences)
    
    print(f"  Wilcoxon statistic: {wilcoxon_stat:.4f}")
    print(f"  Wilcoxon p-value: {wilcoxon_p:.6f}")
    print(f"  Significant (p < 0.05)? {'YES ✓' if wilcoxon_p < 0.05 else 'NO ✗'}")
    print(f"  Bootstrap 95% CI: [{ci_lower:+.6f}, {ci_upper:+.6f}]")
    print(f"  CI excludes 0? {'YES ✓' if (ci_lower > 0 or ci_upper < 0) else 'NO ✗'}")
    
    # Multi-seed robustness
    print("\n[Multi-Seed Robustness]")
    verdicts = []
    for seed in SEEDS:
        base = evaluate_per_case(Baseline, hu, masks, seed=seed)
        exp = evaluate_per_case(Experiment, hu, masks, seed=seed)
        delta = exp.mean() - base.mean()
        verdict = "SUPPORTED" if delta > 0 else "NO IMPROVEMENT"
        verdicts.append(verdict)
        print(f"  Seed {seed}: delta = {delta:+.6f} => {verdict}")
    
    robust = len(set(verdicts)) == 1
    print(f"  Robust across seeds? {'YES ✓' if robust else 'NO ✗'}")
    
    # Final verdict
    print("\n[Final Verdict]")
    if wilcoxon_p < 0.05 and (ci_lower > 0 or ci_upper < 0) and robust:
        final = "STRONG EVIDENCE: HYPOTHESIS SUPPORTED"
    elif wilcoxon_p < 0.05 or (ci_lower > 0 or ci_upper < 0):
        final = "MODERATE EVIDENCE: HYPOTHESIS SUPPORTED"
    else:
        final = "INSUFFICIENT EVIDENCE"
    print(f"  {final}")
    
    # Save results
    out = {
        "wilcoxon_statistic": wilcoxon_stat,
        "wilcoxon_p_value": wilcoxon_p,
        "significant_p": wilcoxon_p < 0.05,
        "bootstrap_ci_lower": ci_lower,
        "bootstrap_ci_upper": ci_upper,
        "ci_excludes_zero": (ci_lower > 0 or ci_upper < 0),
        "multi_seed_verdicts": verdicts,
        "robust_across_seeds": robust,
        "final_verdict": final,
        "per_case_differences": differences.tolist(),
    }
    Path("experiment_statistics.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nSaved -> experiment_statistics.json")


if __name__ == "__main__":
    main()
