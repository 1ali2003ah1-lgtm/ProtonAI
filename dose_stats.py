"""B2 v2: paired dose-impact statistics (clinical-grade).

Compares planning on AI vs baseline contours, evaluated on ground truth,
across two clinical endpoints (target D95, OAR V20). Bootstrap CI +
one-sided Wilcoxon + non-inferiority decision rule. numpy/scipy only.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from dose_bridge import compute_dose, dvh_metrics

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dose_impact_results.json"
NI_MARGIN = 0.02


def plan_metric(ct, plan_mask, truth_mask, metric="D95"):
    return dvh_metrics(compute_dose(ct, plan_mask), truth_mask)[metric]


def paired_deltas(ct, truth, ai, base, metric="D95"):
    """Per-case delta (AI - baseline) of the metric on ground truth.
    For OAR V20 lower is better, so we flip the sign."""
    sign = -1.0 if metric == "oar_v20" else 1.0
    out = []
    for c, t, a, b in zip(ct, truth, ai, base):
        va = _metric(c, a, t, metric)
        vb = _metric(c, b, t, metric)
        out.append(sign * (va - vb))
    return np.asarray(out, float)


def _metric(c, plan, truth, metric):
    if metric == "oar_v20":
        from dose_bridge import oar_v20
        return oar_v20(compute_dose(c, plan), truth)
    return plan_metric(c, plan, truth, metric)


def bootstrap_ci(x, n=2000, seed=0, conf=0.95):
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(x, size=len(x), replace=True).mean()
                      for _ in range(n)])
    lo, hi = np.percentile(means, [(1 - conf) / 2 * 100, (1 + conf) / 2 * 100])
    return float(lo), float(hi)


def wilcoxon_p(x):
    if np.all(x == 0):
        return 1.0
    try:
        from scipy.stats import wilcoxon
        return float(wilcoxon(x, alternative="greater").pvalue)
    except Exception:
        pos = (x > 0).sum()
        return float(0.5 ** len(x)) if pos == len(x) else 1.0


def verdict_for(lo, mean, p):
    if lo > 0 and p < 0.05:
        return "SUPERIOR"
    if lo > -NI_MARGIN:
        return "NON_INFERIOR"
    return "NOT_ESTABLISHED"


def dose_impact(ct, truth, ai, base, seed=0):
    d95 = paired_deltas(ct, truth, ai, base, "D95")
    oar = paired_deltas(ct, truth, ai, base, "oar_v20")
    res = {}
    for name, x in (("d95", d95), ("oar_v20", oar)):
        lo, hi = bootstrap_ci(x, seed=seed)
        p = wilcoxon_p(x)
        res[name] = {"mean": float(x.mean()), "ci_lo": lo, "ci_hi": hi,
                     "wilcoxon_p": p,
                     "verdict": verdict_for(lo, x.mean(), p)}
    return res


def main():
    rng = np.random.default_rng(7)
    ct, truth, ai, base = [], [], [], []
    for i in range(8):
        c = np.zeros((60, 40)); t = np.zeros((60, 40))
        r0 = 20 + i
        t[r0:r0 + 10, 10:30] = 1
        a = np.roll(t, 1, axis=0)          # AI: small error
        b = np.roll(t, 4, axis=0)          # baseline: large error
        ct.append(c); truth.append(t); ai.append(a); base.append(b)
    res = dose_impact(ct, truth, ai, base)
    out = {"ni_margin": NI_MARGIN, "n_cases": 8, **res}
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"DOSE IMPACT: d95 mean={res['d95']['mean']:.3f} "
          f"CI=[{res['d95']['ci_lo']:.3f},{res['d95']['ci_hi']:.3f}] "
          f"p={res['d95']['wilcoxon_p']:.4f} -> {res['d95']['verdict']}")
    print("Saved -> dose_impact_results.json")


if __name__ == "__main__":
    main()
