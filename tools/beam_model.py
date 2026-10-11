from __future__ import annotations
import numpy as np
from scipy.optimize import nnls
from tools.dose_3d import bragg_curve
def range_to_energy(R_mm):
    R_cm = R_mm / 10.0
    return float((R_cm / 0.0022) ** (1 / 1.77))
def spot_lattice(ny, nx, n=4):
    ys = np.linspace(2, ny - 3, n).astype(int); xs = np.linspace(2, nx - 3, n).astype(int)
    return [(int(y), int(x)) for y in ys for x in xs]
def spot_dose(shape, y, x, r, sig_lat=1.5):
    nz, ny, nx = shape
    depth = bragg_curve(np.arange(nz, dtype=float), r)
    Y, X = np.mgrid[0:ny, 0:nx]
    lat = np.exp(-0.5 * ((Y - y) ** 2 + (X - x) ** 2) / sig_lat ** 2)
    return depth[:, None, None] * lat[None, :, :]
def default_layers(target, dz=1.0, L=8):
    prof = np.asarray(target, float).mean(axis=(1, 2))
    depths = np.nonzero(prof > 0.05)[0]
    if depths.size == 0:
        depths = np.array([0])
    return np.linspace(depths[0] * dz, depths[-1] * dz, L)
def optimize_spots(shape, spots, target, layers=None, presc=1.0):
    if layers is None:
        layers = default_layers(target)
    cols = [spot_dose(shape, y, x, r).ravel() for y, x in spots for r in layers]
    A = np.stack(cols, 1)
    m = np.asarray(target, float).ravel() > 0.5
    w, _ = nnls(A[m], np.full(int(m.sum()), presc))
    return w, (A @ w).reshape(shape)
