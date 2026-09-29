"""P5-S2: inter-observer agreement suite (DATA-ACQ-001 s6).

Per case: Dice + HD95 (95th-percentile Hausdorff, mm).
Dual acceptance: mean Dice >= 0.85 AND mean HD95 <= 5.0 mm.
Degradation operators (erode/dilate/shift/jitter) prove the suite sees
the full deviation spectrum.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import seg_metrics  # noqa: E402

THRESHOLD = 0.85
HD95_TOL_MM = 5.0
SPACING_MM = 1.0
N_BOOT = 1000


def erode(mask, iters=1):
    m = mask.astype(float)
    for _ in range(iters):
        inner = np.ones_like(m)
        inner[1:, :] = np.minimum(inner[1:, :], m[:-1, :])
        inner[:-1, :] = np.minimum(inner[:-1, :], m[1:, :])
        inner[:, 1:] = np.minimum(inner[:, 1:], m[:, :-1])
        inner[:, :-1] = np.minimum(inner[:, :-1], m[:, 1:])
        m = m * inner
    return m


def dilate(mask, iters=1):
    m = mask.astype(float)
    for _ in range(iters):
        outer = np.zeros_like(m)
        outer[1:, :] = np.maximum(outer[1:, :], m[:-1, :])
        outer[:-1, :] = np.maximum(outer[:-1, :], m[1:, :])
        outer[:, 1:] = np.maximum(outer[:, 1:], m[:, :-1])
        outer[:, :-1] = np.maximum(outer[:, :-1], m[:, 1:])
        m = np.maximum(m, outer)
    return m


def shift(mask, k=2):
    out = np.zeros_like(mask)
    out[k:, :] = mask[:-k, :]
    return out


def jitter(mask, seed=7):
    rng = np.random.default_rng(seed)
    m = mask.astype(float)
    boundary = (m > 0) & (erode(m, 1) == 0)
    return np.where(boundary & (rng.random(m.shape) < 0.5), 0.0, m)


def hd95(a, b, spacing_mm=SPACING_MM):
    a, b = a.astype(bool), b.astype(bool)
    if not a.any() and not b.any():
        return 0.0
    if a.any() != b.any():
        return float("inf")
    da = distance_transform_edt(~a)
    db = distance_transform_edt(~b)
    d = np.concatenate([da[b], db[a]]) * spacing_mm
    return float(np.percentile(d, 95))


def bootstrap_ci(values, n_boot=N_BOOT, seed=42):
    rng = np.random.default_rng(seed)
    vals = np.asarray(values)
    stats = [np.mean(rng.choice(vals, size=len(vals), replace=True))
             for _ in range(n_boot)]
    return [float(np.percentile(stats, 2.5)),
            float(np.percentile(stats, 97.5))]


def study(pairs, threshold=THRESHOLD, hd95_tol_mm=HD95_TOL_MM):
    dice = [float(seg_metrics.dice(a, b)) for a, b in pairs]
    hd = [hd95(a, b) for a, b in pairs]
    mean_d = float(np.mean(dice)) if dice else 0.0
    mean_h = float(np.mean(hd)) if hd else float("inf")
    return {"per_case_dice": dice, "per_case_hd95": hd,
            "mean_dice": mean_d, "mean_hd95": mean_h,
            "ci95_dice": bootstrap_ci(dice) if dice else [0.0, 0.0],
            "threshold": threshold, "hd95_tol_mm": hd95_tol_mm,
            "verdict": ("PASS" if (mean_d >= threshold
                                   and mean_h <= hd95_tol_mm) else "FAIL")}


def synthetic_demo():
    masks = np.load(ROOT / "data" / "synth_ct" / "SYNTH-002" /
                    "ground_truth" / "masks.npy").astype(float)
    ops = {"erode1": lambda m: erode(m, 1),
           "dilate1": lambda m: dilate(m, 1),
           "shift2": lambda m: shift(m, 2),
           "jitter": jitter}
    matrix = {name: float(np.mean([seg_metrics.dice(masks[z], fn(masks[z]))
                                   for z in range(masks.shape[0])]))
              for name, fn in ops.items()}
    primary = study([(masks[z], erode(masks[z], 1))
                     for z in range(masks.shape[0])])
    return matrix, primary


def main():
    matrix, res = synthetic_demo()
    print("===== INTER-OBSERVER AGREEMENT (DATA-ACQ-001 s6) =====")
    for name, v in matrix.items():
        print(f"operator {name}: mean Dice={v:.4f}")
    print(f"primary(erode1): Dice={res['mean_dice']:.4f} "
          f"CI95=[{res['ci95_dice'][0]:.4f}, {res['ci95_dice'][1]:.4f}] "
          f"HD95={res['mean_hd95']:.2f}mm")
    print(f"dual criteria -> verdict={res['verdict']}")
    (ROOT / "inter_observer_study.json").write_text(
        json.dumps({"operators_mean_dice": matrix, **res}, indent=2),
        encoding="utf-8")
    print("Saved -> inter_observer_study.json")


if __name__ == "__main__":
    main()
