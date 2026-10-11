from __future__ import annotations
import numpy as np
from scipy.spatial.distance import cdist
def gamma_3d(a, b, spacing=(1.0, 1.0, 1.0), dc=0.03, dt=3.0):
    a = np.asarray(a, float); b = np.asarray(b, float)
    gmax = max(float(a.max()), 1e-9)
    coords = (np.array(np.indices(a.shape)).reshape(a.ndim, -1).T * np.asarray(spacing, float))
    D = cdist(coords, coords)
    dd = np.abs(a.ravel()[:, None] - b.ravel()[None, :]) / (dc * gmax)
    G = np.sqrt(dd ** 2 + (D / dt) ** 2)
    return float((G.min(axis=1) <= 1.0).mean())
def gamma_1d(a, b, dc=0.03, dt=3.0):
    return gamma_3d(np.asarray(a, float)[None, None, :], np.asarray(b, float)[None, None, :], dc=dc, dt=dt)
