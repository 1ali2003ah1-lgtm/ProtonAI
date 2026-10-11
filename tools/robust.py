from __future__ import annotations
import numpy as np
from tools import dose_3d
def d95(dose, target):
    vals = np.asarray(dose, float)[np.asarray(target, float) > 0.5]
    return float(np.percentile(vals, 5)) if vals.size else 0.0
def v95(dose, target, presc=1.0):
    m = np.asarray(target, float) > 0.5
    if not m.any():
        return 0.0
    return float(np.mean(np.asarray(dose, float)[m] >= 0.95 * presc))
def robust_eval(spr, field, R, target, mod=6.0, dz=1.0):
    nom = dose_3d.compute_dose_3d(spr, R, field, mod, dz)
    d95s, v95s = [], []
    for ds in (-3, 0, 3):
        for re in (-0.035, 0.0, 0.035):
            d = dose_3d.compute_dose_3d(spr, R * (1 + re), field, mod, dz)
            d = np.roll(d, ds, axis=0)
            d95s.append(d95(d, target)); v95s.append(v95(d, target))
    return {"nominal": d95(nom, target), "worst": min(d95s), "mean": float(np.mean(d95s)),
            "v95_nominal": v95(nom, target), "v95_worst": min(v95s)}
