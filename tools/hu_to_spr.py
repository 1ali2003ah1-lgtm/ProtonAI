from __future__ import annotations
import numpy as np
_HU = np.array([-1000, -500, -100, 0, 100, 300, 1000, 3000], float)
_SPR = np.array([0.001, 0.30, 0.95, 1.000, 1.03, 1.10, 1.35, 1.70], float)
_TISSUE = {"air": -1000, "lung": -500, "fat": -100, "water": 0, "muscle": 40, "bone": 1000}
_REF = {"air": 0.001, "lung": 0.30, "fat": 0.95, "water": 1.0, "muscle": 1.02, "bone": 1.35}
def hu_to_spr(hu):
    return float(np.interp(hu, _HU, _SPR))
def calibration_report():
    errs = {k: abs(hu_to_spr(v) - _REF[k]) for k, v in _TISSUE.items()}
    return {"tissues": _TISSUE, "reference": _REF, "abs_err": errs, "max_err": max(errs.values())}
