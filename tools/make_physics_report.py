from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from tools import dose_3d, gamma, hu_to_spr, robust
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "physics_validation.json"
def main():
    spr = np.ones((32, 8, 8)); field = np.ones((8, 8))
    target = np.zeros((32, 8, 8)); target[10:25] = 1
    dose = dose_3d.compute_dose_3d(spr, 20.0, field)
    r = robust.robust_eval(spr, field, 20.0, target)
    cal = hu_to_spr.calibration_report()
    m = {"spr_water": hu_to_spr.hu_to_spr(0.0), "calibration_max_err": cal["max_err"],
         "wepl": dose_3d.wepl(spr), "bragg_peak": int(np.argmax(dose.mean((1, 2)))),
         "distal_falloff_ok": bool(dose[31].mean() < 0.1 * dose[15].mean()),
         "gamma_identical": gamma.gamma_3d(dose[:16], dose[:16]),
         "robust_worst_d95": r["worst"], "v95_nominal": r["v95_nominal"]}
    m["pass"] = bool(m["spr_water"] == 1.0 and m["calibration_max_err"] < 0.02 and m["distal_falloff_ok"]
                     and m["gamma_identical"] == 1.0 and r["worst"] <= r["nominal"] + 1e-9)
    OUT.write_text(json.dumps(m, indent=2), encoding="utf-8")
    print(f"W2 FINAL: physics validation pass={m['pass']}")
if __name__ == "__main__":
    main()
