"""P3-S3: rigorous external validation with cross-domain symmetry.

Protocol (ADR-005):
- In-domain: train & evaluate per slice within each series.
- Cross-domain both directions:
    S1->S2 (easy->hard): model must generalize to harder distribution
    S2->S1 (hard->easy): model must not collapse on simpler distribution
- Multi-seed (42, 123, 999) for robustness.
- Permutation test on paired gap differences (paired by slice).
- Bootstrap 95% CI on gap differences (resampling slices).
- Generalization gap = in_domain(target) - cross(train->target).
  Smaller gap = better generalizer (understands, not memorizes).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np

from dicom_reader import DicomReader  # noqa: E402
from torch_segmenter import TorchSegmenter as Baseline  # noqa: E402
from experimental_segmenter import TorchSegmenter as Experiment  # noqa: E402
import seg_metrics  # noqa: E402

EPOCHS = 40
SEEDS = [42, 123, 999]
SERIES = ["SYNTH-001", "SYNTH-002"]
N_PERM = 10_000
N_BOOT = 1000


def ingest(name):
    d = ROOT / "data" / "synth_ct" / name
    reader = DicomReader(metadata_keys=["PatientID", "Modality"])
    slices = sorted(d.glob("*.dcm"))
    if not slices:
        raise FileNotFoundError(f"no .dcm in {d}; run make_synthetic_dicom.py")
    hu = np.stack([np.asarray(reader.read(p)["pixels"], dtype=float)
                   for p in slices])
    masks = np.load(d / "ground_truth" / "masks.npy").astype(float)
    return hu, masks


def per_slice_eval(Cls, hu_tr, m_tr, hu_te, m_te, seed):
    dices = []
    for z in range(hu_tr.shape[0]):
        model = Cls(seed=seed)
        model.fit(hu_tr[z], m_tr[z], epochs=EPOCHS)
        pred = model.segment(hu_te[z])
        dices.append(seg_metrics.dice(pred, m_te[z]))
    return np.array(dices)


def full_eval(Cls, data):
    """Returns dict of directions -> {seed -> per-slice dices}."""
    out = {}
    for src in SERIES:
        for tgt in SERIES:
            key = f"{'in_domain' if src == tgt else f'cross_{src}_to_{tgt}'}"
            out[key] = {}
            hu_s, m_s = data[src]
            hu_t, m_t = data[tgt]
            for seed in SEEDS:
                out[key][seed] = per_slice_eval(
                    Cls, hu_s, m_s, hu_t, m_t, seed).tolist()
    return out


def summarize(directions):
    r = {}
    for k, by_seed in directions.items():
        per_seed_means = [np.mean(by_seed[s]) for s in SEEDS]
        r[k] = {"mean": float(np.mean(per_seed_means)),
                "std": float(np.std(per_seed_means)),
                "per_seed": per_seed_means}
    r["gap_S1_to_S2"] = r["in_domain_SYNTH-002"]["mean"] - r["cross_SYNTH-001_to_SYNTH-002"]["mean"]
    r["gap_S2_to_S1"] = r["in_domain_SYNTH-001"]["mean"] - r["cross_SYNTH-002_to_SYNTH-001"]["mean"]
    return r


def paired_permutation_test(base_gaps, exp_gaps, n_perm=N_PERM):
    """Paired permutation test: H0 = models have same mean gap.
    base_gaps, exp_gaps are per-slice gap arrays of same length.
    Returns p-value (two-sided)."""
    observed = np.mean(exp_gaps - base_gaps)
    diffs = exp_gaps - base_gaps
    rng = np.random.default_rng(42)
    count = 0
    for _ in range(n_perm):
        signs = rng.choice([-1, 1], size=len(diffs))
        perm_stat = np.mean(diffs * signs)
        if abs(perm_stat) >= abs(observed):
            count += 1
    return float(count / n_perm), float(observed)


def bootstrap_ci(gap_diffs, n_boot=N_BOOT, alpha=0.05):
    rng = np.random.default_rng(42)
    stats = [np.mean(rng.choice(gap_diffs, size=len(gap_diffs), replace=True))
             for _ in range(n_boot)]
    return (float(np.percentile(stats, 100 * alpha / 2)),
            float(np.percentile(stats, 100 * (1 - alpha / 2))))


def main():
    data = {n: ingest(n) for n in SERIES}
    print("Running baseline across all directions and seeds...")
    base_dirs = full_eval(Baseline, data)
    print("Running experiment across all directions and seeds...")
    exp_dirs = full_eval(Experiment, data)
    base = summarize(base_dirs)
    exp = summarize(exp_dirs)

    # Per-slice paired analysis on seed 42 (primary)
    base_gaps_S1toS2 = (np.array(base_dirs["in_domain_SYNTH-002"][42])
                        - np.array(base_dirs["cross_SYNTH-001_to_SYNTH-002"][42]))
    exp_gaps_S1toS2 = (np.array(exp_dirs["in_domain_SYNTH-002"][42])
                       - np.array(exp_dirs["cross_SYNTH-001_to_SYNTH-002"][42]))
    base_gaps_S2toS1 = (np.array(base_dirs["in_domain_SYNTH-001"][42])
                        - np.array(base_dirs["cross_SYNTH-002_to_SYNTH-001"][42]))
    exp_gaps_S2toS1 = (np.array(exp_dirs["in_domain_SYNTH-001"][42])
                       - np.array(exp_dirs["cross_SYNTH-002_to_SYNTH-001"][42]))

    diff_S1toS2 = exp_gaps_S1toS2 - base_gaps_S1toS2
    diff_S2toS1 = exp_gaps_S2toS1 - base_gaps_S2toS1
    p_S1toS2, stat_S1toS2 = paired_permutation_test(base_gaps_S1toS2, exp_gaps_S1toS2)
    p_S2toS1, stat_S2toS1 = paired_permutation_test(base_gaps_S2toS1, exp_gaps_S2toS1)
    ci_S1toS2 = bootstrap_ci(diff_S1toS2)
    ci_S2toS1 = bootstrap_ci(diff_S2toS1)

    print("\n===== EXTERNAL VALIDATION (ADR-005) =====")
    for name, r in [("baseline", base), ("experiment", exp)]:
        print(f"\n[{name}]")
        for k in ("in_domain_SYNTH-001", "in_domain_SYNTH-002",
                  "cross_SYNTH-001_to_SYNTH-002", "cross_SYNTH-002_to_SYNTH-001"):
            print(f"  {k}: mean={r[k]['mean']:.4f} "
                  f"std={r[k]['std']:.4f} seeds={r[k]['per_seed']}")
        print(f"  gap S1->S2: {r['gap_S1_to_S2']:+.6f}")
        print(f"  gap S2->S1: {r['gap_S2_to_S1']:+.6f}")

    print(f"\n[Paired gap difference (experiment - baseline)]")
    print(f"  S1->S2: stat={stat_S1toS2:+.6f} p={p_S1toS2:.4f} "
          f"CI95=[{ci_S1toS2[0]:+.6f}, {ci_S1toS2[1]:+.6f}]")
    print(f"  S2->S1: stat={stat_S2toS1:+.6f} p={p_S2toS1:.4f} "
          f"CI95=[{ci_S2toS1[0]:+.6f}, {ci_S2toS1[1]:+.6f}]")

    # Verdict: experiment generalizes better if BOTH directions show
    # smaller gap AND at least one is statistically significant
    exp_better_S1toS2 = exp["gap_S1_to_S2"] < base["gap_S1_to_S2"]
    exp_better_S2toS1 = exp["gap_S2_to_S1"] < base["gap_S2_to_S1"]
    sig_S1toS2 = p_S1toS2 < 0.05
    sig_S2toS1 = p_S2toS1 < 0.05
    if exp_better_S1toS2 and exp_better_S2toS1 and (sig_S1toS2 or sig_S2toS1):
        verdict = "STRONG: experiment generalizes better (both directions)"
    elif exp_better_S1toS2 and exp_better_S2toS1:
        verdict = "MODERATE: experiment generalizes better (consistent, not significant)"
    elif exp_better_S1toS2 or exp_better_S2toS1:
        verdict = "MIXED: advantage in one direction only"
    else:
        verdict = "NO GENERALIZATION ADVANTAGE"
    print(f"\nVERDICT: {verdict}")

    artifact = {
        "protocol": "in-domain + cross-domain (both directions); paired by slice; "
                    "multi-seed; permutation + bootstrap",
        "seeds": SEEDS, "epochs": EPOCHS,
        "baseline": base, "experiment": exp,
        "statistics": {
            "gap_diff_S1toS2": float(stat_S1toS2),
            "gap_diff_S2toS1": float(stat_S2toS1),
            "permutation_p_S1toS2": p_S1toS2,
            "permutation_p_S2toS1": p_S2toS1,
            "significant_p_S1toS2": sig_S1toS2,
            "significant_p_S2toS1": sig_S2toS1,
            "bootstrap_ci_S1toS2": list(ci_S1toS2),
            "bootstrap_ci_S2toS1": list(ci_S2toS1),
        },
        "verdict": verdict,
    }
    (ROOT / "external_validation_results.json").write_text(
        json.dumps(artifact, indent=2), encoding="utf-8")
    print("Saved -> external_validation_results.json")


if __name__ == "__main__":
    main()
