"""B1 v2 FINAL: calibrated, weight-optimized proton dose bridge.

HU->RSP piecewise (Schneider-like); water-equivalent depth; SOBP via
Bragg superposition with EM weight optimization (flat plateau); clinical
proximal/distal margins; range-uncertainty worst case; DVH metrics
(D95/D2/HI/coverage) + OAR V20. Surrogate for method development;
superseded by TOPAS/MC for clinical dose. numpy-only, additive.
"""
from __future__ import annotations

import numpy as np

VOXEL_MM = 2.0
RANGE_UNC = 0.035
PRESCRIPTION = 0.95
PROX_MARGIN_MM = 8.0
DIST_MARGIN_MM = 6.0

HU_PTS = np.array([-1000, -500, -100, 0, 100, 300, 700, 1000, 2000])
RSP_PTS = np.array([0.001, 0.30, 0.95, 1.00, 1.04, 1.12, 1.28, 1.40, 1.75])


def hu_to_rsp(hu):
    return np.clip(np.interp(np.asarray(hu, float), HU_PTS, RSP_PTS), 0.0, 2.5)


def water_equivalent_depth(rsp, voxel_mm=VOXEL_MM):
    return np.cumsum(rsp, axis=0) * voxel_mm


def _bragg(wed, r, sigma_d=1.5, sigma_p=3.0, entrance=0.05):
    distal = 1.0 / (1.0 + np.exp((wed - r) / sigma_d))
    bump = np.exp(-(((r - wed) / sigma_p) ** 2))
    return entrance * distal + bump * distal


def sobp_dose(wed, d_min, d_max, n_peaks=24, iters=60):
    """Weight-optimized SOBP: EM updates flatten the plateau."""
    ranges = np.linspace(d_min, d_max, n_peaks)
    grid = np.linspace(d_min + 2.0, d_max - 2.0, 40)
    A = np.stack([_bragg(grid, r) for r in ranges], axis=1)   # (40, peaks)
    w = np.ones(n_peaks)
    for _ in range(iters):
        dose_g = A @ w
        corr = (A.T @ (1.0 / np.maximum(dose_g, 1e-6))) / \
            np.maximum(A.sum(axis=0), 1e-6)
        w = w * np.clip(corr, 0.25, 4.0)
    peaks = np.stack([_bragg(wed, r) for r in ranges], axis=-1)  # (H,W,peaks)
    dose = peaks @ w
    norm = float(np.interp(0.5 * (d_min + d_max), grid, A @ w))
    return dose / norm


def compute_dose(ct, mask, wed_scale=1.0):
    wed = water_equivalent_depth(hu_to_rsp(ct)) * wed_scale
    m = np.asarray(mask) > 0
    if m.sum() == 0:
        raise ValueError("empty mask")
    return sobp_dose(wed, max(wed[m].min() - PROX_MARGIN_MM, 0.0),
                     wed[m].max() + DIST_MARGIN_MM)


def dvh(dose, mask, n=101):
    vals = np.asarray(dose)[np.asarray(mask) > 0]
    if vals.size == 0:
        return np.zeros(n), np.zeros(n)
    bins = np.linspace(0, np.asarray(dose).max() + 1e-9, n)
    cum = np.cumsum(np.histogram(vals, bins)[0][::-1])[::-1] / vals.size
    return bins, cum


def _dose_at(bins, cum, f):
    idx = np.where(cum >= f)[0]
    return float(bins[idx[-1]]) if len(idx) else 0.0


def dvh_metrics(dose, mask, prescription=PRESCRIPTION):
    bins, cum = dvh(dose, mask)
    vals = np.asarray(dose)[np.asarray(mask) > 0]
    d95, d2 = _dose_at(bins, cum, .95), _dose_at(bins, cum, .02)
    mean = float(vals.mean())
    return {"D95": d95, "D2": d2, "Dmax": float(vals.max()), "mean": mean,
            "HI": (d2 - d95) / mean if mean else 0.0,
            "coverage": float((vals >= prescription).mean())}


def oar_v20(dose, oar):
    vals = np.asarray(dose)[np.asarray(oar) > 0]
    return float((vals > 0.2 * np.asarray(dose).max()).mean()) if vals.size else 0.0


def robust_d95(ct, mask, unc=RANGE_UNC):
    return min(dvh_metrics(compute_dose(ct, mask, 1.0 + s * unc), mask)["D95"]
               for s in (-1.0, 0.0, 1.0))
