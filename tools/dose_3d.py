from __future__ import annotations
import numpy as np
from scipy.ndimage import gaussian_filter
def bragg_curve(wed, r, sig=2.0):
    x = np.asarray(wed, float)
    pre = 0.25 + 0.75 * np.clip(x / max(r, 1e-6), 0, 1)
    g = np.exp(-0.5 * ((x - r) / sig) ** 2)
    post = np.exp(-np.clip(x - r, 0, None) / (sig * 1.5))
    return np.where(x <= r, pre * (0.3 + 0.7 * g), g * post)
def depth_curve(wed, R, mod=6.0):
    x = np.asarray(wed, float)
    start = R - mod
    return (np.where(x < start, 0.35, 0.0)
            + np.where((x >= start) & (x <= R), 1.0, 0.0)
            + np.where(x > R, np.exp(-(x - R) / 1.5), 0.0))
def compute_dose_3d(spr, R, field, mod=6.0, dz=1.0, sigma0=1.0):
    spr = np.asarray(spr, float); field = np.asarray(field, float)
    wed = np.cumsum(spr * dz, axis=0)
    c = depth_curve(wed, R, mod)
    axis_wed = wed.mean(axis=(1, 2))
    dose = np.empty_like(wed)
    for z in range(wed.shape[0]):
        sig = sigma0 * np.sqrt(max(axis_wed[z], 0)) / 4 + 0.3
        dose[z] = c[z] * gaussian_filter(field, sig)
    return dose
def wepl(spr, dz=1.0):
    return float(np.mean(np.sum(np.asarray(spr, float) * dz, axis=0)))
