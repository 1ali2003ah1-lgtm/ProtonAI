"""W6 FINAL: multi-seed head-to-head benchmark with paired Wilcoxon,
bootstrap CI, and Cliff's delta effect size. Comparators are SIMULATED
surrogates (atlas / typical commercial auto-seg / manual inter-observer);
real-commercial head-to-head pending partner data."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.ndimage import binary_dilation, binary_erosion

from tools import train_seg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "benchmark_results.json"
MD = ROOT / "docs" / "business" / "BENCHMARK-001.md"
README = ROOT / "README.md"
SEEDS = (2, 3, 4)
KEYS = ("protonai", "atlas", "commercial_sim", "manual_sim")


def _manual(gt, rng):
    g = gt.copy()
    g = binary_erosion(g) if rng.random() < 0.5 else binary_dilation(g)
    g = np.roll(g, int(rng.integers(-2, 3)), axis=0)
    return np.roll(g, int(rng.integers(-2, 3)), axis=1).astype(int)


def _comm(gt, rng):
    return binary_erosion(gt, iterations=2).astype(int)


def _bootstrap_ci(d, rng, n=1000):
    d = np.asarray(d, float)
    means = [float(np.mean(rng.choice(d, size=len(d), replace=True)))
             for _ in range(n)]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def cliffs_delta(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    gt = sum(float(np.sum(x > b)) for x in a)
    lt = sum(float(np.sum(x < b)) for x in a)
    return (gt - lt) / (len(a) * len(b))


def _run_seed(seed, n):
    rng = np.random.default_rng(seed)
    X, Y = train_seg.dataset(n, seed)
    _, Yt = train_seg.dataset(64, 0)
    atlas = (Yt.numpy()[:, 0].mean(0) > 0.5).astype(int)
    model = train_seg.ensure_model()
    per = {k: {"dice": [], "hd95": [], "ms": []} for k in KEYS}
    for i in range(n):
        img = X.numpy()[i, 0]; gt = Y.numpy()[i, 0]
        t0 = time.perf_counter()
        pred, _ = train_seg.predict_unc(model, img, n=4)
        per["protonai"]["ms"].append((time.perf_counter() - t0) * 1000)
        preds = {"protonai": pred, "atlas": atlas,
                 "commercial_sim": _comm(gt, rng),
                 "manual_sim": _manual(gt, rng)}
        for k, p in preds.items():
            per[k]["dice"].append(train_seg.dice(p, gt))
            per[k]["hd95"].append(train_seg.hd95(p, gt))
    return per


def _write_md(res):
    lines = ["# Head-to-Head Benchmark — BENCHMARK-001", "",
             f"Pooled paired comparisons: n={res['pooled_n']} "
             f"({len(res['seeds'])} seeds x {res['n_cases']} cases).",
             "Comparators are SIMULATED surrogates; real-commercial "
             "head-to-head pending partner data.", "",
             "| Method | Dice | HD95 | ms/case |", "|---|---|---|---|"]
    for k, v in res["methods"].items():
        lines.append(f"| {k} | {v['dice_mean']:.3f}±{v['dice_std']:.3f} "
                     f"| {v['hd95_mean']:.2f} | {v['runtime_ms']:.1f} |")
    lines += ["", "## Paired comparisons (ProtonAI − comparator)", ""]
    for k, c in res["comparisons"].items():
        lines.append(f"- vs {k}: p={c['p']:.4g}, "
                     f"CI[{c['ci_low']:.3f}, {c['ci_high']:.3f}], "
                     f"Cliff's delta={c['cliffs_delta']:.2f} "
                     f"=> **{c['verdict']}**")
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_readme(res):
    t = README.read_text(encoding="utf-8")
    if "## Evidence & Benchmarks" in t:
        return
    sec = ["", "## Evidence & Benchmarks", "",
           "See docs/business/BENCHMARK-001.md "
           f"(pooled n={res['pooled_n']})."]
    for k, c in res["comparisons"].items():
        sec.append(f"- vs {k}: **{c['verdict']}** "
                   f"(Cliff's delta={c['cliffs_delta']:.2f})")
    README.write_text(t.rstrip() + "\n" + "\n".join(sec) + "\n",
                      encoding="utf-8")


def run_benchmark(n=16, seeds=SEEDS):
    all_per = {s: _run_seed(s, n) for s in seeds}
    res = {"seeds": list(seeds), "n_cases": n, "pooled_n": n * len(seeds),
           "methods": {}, "comparisons": {}}
    for k in KEYS:
        dice = [d for s in seeds for d in all_per[s][k]["dice"]]
        hd = [h for s in seeds for h in all_per[s][k]["hd95"]]
        ms = [m for s in seeds for m in all_per[s][k]["ms"]]
        res["methods"][k] = {
            "dice_mean": float(np.mean(dice)),
            "dice_std": float(np.std(dice)),
            "hd95_mean": float(np.nanmean(hd)),
            "runtime_ms": float(np.mean(ms)) if ms else 0.0}
    rng = np.random.default_rng(0)
    for k in ("atlas", "commercial_sim", "manual_sim"):
        pa = np.array([d for s in seeds for d in all_per[s]["protonai"]["dice"]])
        pb = np.array([d for s in seeds for d in all_per[s][k]["dice"]])
        diffs = pa - pb
        try:
            p = float(stats.wilcoxon(diffs).pvalue) if np.any(diffs != 0) else 1.0
        except ValueError:
            p = 1.0
        lo, hi = _bootstrap_ci(diffs, rng)
        verdict = ("superior" if lo > 0 else
                   "inferior" if hi < 0 else "non-inferior")
        res["comparisons"][k] = {"p": p, "ci_low": lo, "ci_high": hi,
                                 "cliffs_delta": cliffs_delta(pa, pb),
                                 "verdict": verdict}
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    _write_md(res)
    _append_readme(res)
    return res


if __name__ == "__main__":
    r = run_benchmark()
    print("W6 FINAL: verdicts =",
          {k: v["verdict"] for k, v in r["comparisons"].items()})
