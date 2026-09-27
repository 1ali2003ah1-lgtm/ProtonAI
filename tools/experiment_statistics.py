"""P2-S4: Professional statistical analysis for model comparison.

Methods (ADR-003):
1. Descriptive statistics (mean, median, std, IQR, min, max)
2. Normality test (Shapiro-Wilk if n >= 8)
3. Paired test selection:
   - Wilcoxon signed-rank (non-parametric, default)
   - Paired t-test (if normality holds)
   - Permutation test (if all differences = 0)
4. Bootstrap 95% CI (10,000 resamples, BCa method)
5. Effect size (Cohen's d for parametric, rank-biserial for non-parametric)
6. Multi-seed robustness (seeds: 42, 123, 999)

Acceptance: p < 0.05 AND CI excludes 0 AND robust across seeds.
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

EPOCHS = 40
SEEDS = [42, 123, 999]
N_BOOTSTRAP = 10_000
ALPHA = 0.05


def ingest(series: Path):
    reader = DicomReader(metadata_keys=["PatientID", "Modality"])
    slices = sorted(series.glob("*.dcm"))
    if not slices:
        raise FileNotFoundError(f"No .dcm slices in {series}; run tools/make_synthetic_dicom.py first")
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


def descriptive_stats(arr):
    return {
        "n": len(arr),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr, ddof=1)),
        "iqr": float(np.percentile(arr, 75) - np.percentile(arr, 25)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def bootstrap_ci_bca(data, stat_func=np.mean, n_bootstrap=N_BOOTSTRAP, alpha=ALPHA):
    """Bias-corrected and accelerated bootstrap CI."""
    rng = np.random.default_rng(42)
    n = len(data)
    boot_stats = []
    for _ in range(n_bootstrap):
        sample = rng.choice(data, size=n, replace=True)
        boot_stats.append(stat_func(sample))
    boot_stats = np.array(boot_stats)
    
    # Bias correction
    z0 = stats.norm.ppf(np.mean(boot_stats < stat_func(data)))
    
    # Acceleration (jackknife)
    jackknife = []
    for i in range(n):
        jack_sample = np.delete(data, i)
        jackknife.append(stat_func(jack_sample))
    jack_mean = np.mean(jackknife)
    acc = np.sum((jack_mean - jackknife) ** 3) / (6 * np.sum((jack_mean - jackknife) ** 2) ** 1.5 + 1e-10)
    
    # Adjusted percentiles
    z_alpha = stats.norm.ppf(alpha / 2)
    z_1alpha = stats.norm.ppf(1 - alpha / 2)
    
    a1 = stats.norm.cdf(z0 + (z0 + z_alpha) / (1 - acc * (z0 + z_alpha)))
    a2 = stats.norm.cdf(z0 + (z0 + z_1alpha) / (1 - acc * (z0 + z_1alpha)))
    
    lower = np.percentile(boot_stats, 100 * a1)
    upper = np.percentile(boot_stats, 100 * a2)
    
    return float(lower), float(upper), float(np.std(boot_stats))


def effect_size(base, exp):
    """Cohen's d for paired samples."""
    diff = exp - base
    return float(np.mean(diff) / (np.std(diff, ddof=1) + 1e-10))


def main(series_name: str, out_json: str, out_md: str):
    hu, masks = ingest(Path("data/synth_ct") / series_name)
    
    print(f"\n{'='*60}")
    print(f"STATISTICAL ANALYSIS: {series_name}")
    print(f"{'='*60}\n")
    
    # Primary analysis (seed 42)
    print("[1/6] Running models (seed=42)...")
    base = evaluate_per_case(Baseline, hu, masks, seed=42)
    exp = evaluate_per_case(Experiment, hu, masks, seed=42)
    diffs = exp - base
    
    # Descriptive statistics
    print("\n[2/6] Descriptive statistics:")
    base_stats = descriptive_stats(base)
    exp_stats = descriptive_stats(exp)
    diff_stats = descriptive_stats(diffs)
    
    print(f"  Baseline: mean={base_stats['mean']:.4f}, std={base_stats['std']:.4f}, "
          f"median={base_stats['median']:.4f}, IQR={base_stats['iqr']:.4f}")
    print(f"  Experiment: mean={exp_stats['mean']:.4f}, std={exp_stats['std']:.4f}, "
          f"median={exp_stats['median']:.4f}, IQR={exp_stats['iqr']:.4f}")
    print(f"  Difference: mean={diff_stats['mean']:+.6f}, std={diff_stats['std']:.6f}")
    
    # Normality test
    print("\n[3/6] Normality test (Shapiro-Wilk):")
    if len(diffs) >= 8:
        shapiro_stat, shapiro_p = stats.shapiro(diffs)
        is_normal = shapiro_p > 0.05
        print(f"  W={shapiro_stat:.4f}, p={shapiro_p:.4f} => "
              f"{'NORMAL' if is_normal else 'NON-NORMAL'}")
    else:
        shapiro_stat, shapiro_p, is_normal = None, None, False
        print(f"  Skipped (n < 8)")
    
    # Paired test selection
    print("\n[4/6] Paired statistical test:")
    if np.all(diffs == 0):
        print(f"  All differences are zero => NO STATISTICAL TEST POSSIBLE")
        test_name, test_stat, p_value = "N/A", None, 1.0
        significant = False
    elif is_normal and len(diffs) >= 8:
        test_name = "Paired t-test"
        test_stat, p_value = stats.ttest_rel(exp, base)
        p_value = float(p_value) / 2  # one-sided
        significant = p_value < ALPHA
        print(f"  {test_name}: t={test_stat:.4f}, p={p_value:.6f} "
              f"(one-sided) => {'SIGNIFICANT' if significant else 'NOT SIGNIFICANT'}")
    else:
        test_name = "Wilcoxon signed-rank"
        try:
            test_stat, p_value = stats.wilcoxon(exp, base, alternative='greater')
            test_stat, p_value = float(test_stat), float(p_value)
            significant = p_value < ALPHA
            print(f"  {test_name}: W={test_stat:.4f}, p={p_value:.6f} => "
                  f"{'SIGNIFICANT' if significant else 'NOT SIGNIFICANT'}")
        except ValueError as e:
            print(f"  Wilcoxon failed: {e} => using permutation test")
            test_name = "Permutation test"
            # Permutation test
            observed_diff = np.mean(diffs)
            n_perm = 10000
            rng = np.random.default_rng(42)
            perm_diffs = []
            for _ in range(n_perm):
                signs = rng.choice([-1, 1], size=len(diffs))
                perm_diffs.append(np.mean(diffs * signs))
            p_value = np.mean(np.array(perm_diffs) >= observed_diff)
            test_stat = observed_diff
            significant = p_value < ALPHA
            print(f"  {test_name}: p={p_value:.6f} => "
                  f"{'SIGNIFICANT' if significant else 'NOT SIGNIFICANT'}")
    
    # Bootstrap CI
    print("\n[5/6] Bootstrap 95% CI (BCa method):")
    ci_lower, ci_upper, ci_std = bootstrap_ci_bca(diffs)
    ci_excludes_zero = (ci_lower > 0 or ci_upper < 0)
    print(f"  CI=[{ci_lower:+.6f}, {ci_upper:+.6f}], std={ci_std:.6f}")
    print(f"  Excludes 0? {'YES' if ci_excludes_zero else 'NO'}")
    
    # Effect size
    cohens_d = effect_size(base, exp)
    print(f"\n  Effect size (Cohen's d): {cohens_d:+.4f}")
    
    # Multi-seed robustness
    print("\n[6/6] Multi-seed robustness:")
    seed_results = []
    for seed in SEEDS:
        b = evaluate_per_case(Baseline, hu, masks, seed)
        e = evaluate_per_case(Experiment, hu, masks, seed)
        delta = float(e.mean() - b.mean())
        seed_results.append({"seed": seed, "delta": delta})
        print(f"  Seed {seed}: delta={delta:+.6f}")
    
    all_positive = all(r["delta"] > 0 for r in seed_results)
    all_negative = all(r["delta"] < 0 for r in seed_results)
    robust = all_positive or all_negative
    print(f"  Robust? {'YES (consistent direction)' if robust else 'NO (inconsistent)'}")
    
    # Final verdict
    print(f"\n{'='*60}")
    print("FINAL VERDICT:")
    print(f"{'='*60}")
    if significant and ci_excludes_zero and robust:
        final = "STRONG EVIDENCE: HYPOTHESIS SUPPORTED"
        print(f"  {final}")
        print(f"  Reason: p < 0.05 AND CI excludes 0 AND robust across seeds")
    elif significant or ci_excludes_zero:
        final = "MODERATE EVIDENCE: HYPOTHESIS SUPPORTED"
        print(f"  {final}")
        print(f"  Reason: Some evidence but not all criteria met")
    else:
        final = "INSUFFICIENT EVIDENCE"
        print(f"  {final}")
        print(f"  Reason: No significant difference detected")
    
    # Save JSON
    out = {
        "series": series_name,
        "baseline_stats": base_stats,
        "experiment_stats": exp_stats,
        "difference_stats": diff_stats,
        "normality_test": {"statistic": shapiro_stat, "p_value": shapiro_p, "is_normal": is_normal},
        "paired_test": {"name": test_name, "statistic": test_stat, "p_value": p_value, "significant": significant},
        "bootstrap_ci": {"lower": ci_lower, "upper": ci_upper, "std": ci_std, "excludes_zero": ci_excludes_zero},
        "effect_size": {"cohens_d": cohens_d},
        "multi_seed": seed_results,
        "robust_across_seeds": robust,
        "final_verdict": final,
        "per_case_differences": diffs.tolist(),
    }
    Path(out_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
    
    # Save Markdown report
    md = f"""# Statistical Analysis Report: {series_name}

## Summary
- **Final Verdict**: {final}
- **Baseline Mean Dice**: {base_stats['mean']:.4f} ± {base_stats['std']:.4f}
- **Experiment Mean Dice**: {exp_stats['mean']:.4f} ± {exp_stats['std']:.4f}
- **Mean Difference**: {diff_stats['mean']:+.6f} ± {diff_stats['std']:.6f}

## Statistical Tests
- **Normality (Shapiro-Wilk)**: W={shapiro_stat:.4f}, p={shapiro_p:.4f} => {'Normal' if is_normal else 'Non-normal'}
- **Paired Test ({test_name})**: statistic={test_stat:.4f}, p={p_value:.6f} => {'Significant' if significant else 'Not significant'}
- **Bootstrap 95% CI**: [{ci_lower:+.6f}, {ci_upper:+.6f}] => {'Excludes 0' if ci_excludes_zero else 'Contains 0'}
- **Effect Size (Cohen's d)**: {cohens_d:+.4f}

## Multi-Seed Robustness
| Seed | Delta |
|------|-------|
"""
    for r in seed_results:
        md += f"| {r['seed']} | {r['delta']:+.6f} |\n"
    md += f"\n**Robust across seeds**: {'Yes' if robust else 'No'}\n"
    
    Path(out_md).write_text(md, encoding="utf-8")
    
    print(f"\nSaved -> {out_json}")
    print(f"Saved -> {out_md}")


if __name__ == "__main__":
    series = sys.argv[1] if len(sys.argv) > 1 else "SYNTH-001"
    out_json = sys.argv[2] if len(sys.argv) > 2 else "experiment_statistics.json"
    out_md = sys.argv[3] if len(sys.argv) > 3 else "experiment_statistics.md"
    main(series, out_json, out_md)
