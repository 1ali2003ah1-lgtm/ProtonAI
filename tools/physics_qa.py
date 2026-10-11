from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from tools import beam_model, dose_3d, gamma, hu_to_spr, plan_metrics, robust
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "physics_qa.json"
def build_qa():
    shape = (16, 8, 8)
    spr = np.ones(shape); field = np.ones((8, 8))
    target = np.zeros(shape); target[6:13, 2:6, 2:6] = 1
    oar = np.zeros(shape); oar[15:16] = 1
    spots = beam_model.spot_lattice(8, 8)
    layers = beam_model.default_layers(target)
    w, dose = beam_model.optimize_spots(shape, spots, target, layers)
    r_ref = float(layers[-1])
    prof = dose.mean((1, 2))
    rb = robust.robust_eval(spr, field, r_ref, target)
    tv = plan_metrics._tv(dose, target)
    cal = hu_to_spr.calibration_report()
    uni = float(np.std(tv) / max(np.mean(tv), 1e-9))
    checks = [
        ("spr_water", hu_to_spr.hu_to_spr(0.0), "==1.0", abs(hu_to_spr.hu_to_spr(0.0) - 1) < 1e-6, "Schneider 1996"),
        ("calibration_max_err", cal["max_err"], "<0.02", cal["max_err"] < 0.02, "Schneider 1996"),
        ("plan_uniformity", uni, "<0.25", uni < 0.25, "ICRU 78"),
        ("r80_err_mm", abs(plan_metrics.r80(prof) - r_ref), "<=3", abs(plan_metrics.r80(prof) - r_ref) <= 3, "IAEA TR-398"),
        ("homogeneity", plan_metrics.homogeneity(dose, target), "<0.7", plan_metrics.homogeneity(dose, target) < 0.7, "ICRU 78"),
        ("conformity", plan_metrics.conformity(dose, target), ">0.5", plan_metrics.conformity(dose, target) > 0.5, "ICRU 78"),
        ("oar_v20", plan_metrics.oar_vlevel(dose, oar), "<0.2", plan_metrics.oar_vlevel(dose, oar) < 0.2, "QUANTEC"),
        ("gamma_identical", gamma.gamma_3d(dose, dose), "==1.0", gamma.gamma_3d(dose, dose) == 1.0, "Low 1998"),
        ("robust_worst<=nom", rb["worst"] - rb["nominal"], "<=0", rb["worst"] <= rb["nominal"] + 1e-9, "ASTRO 2022"),
    ]
    qa = [{"metric": m, "value": v, "tolerance": t, "pass": bool(p), "reference": ref} for m, v, t, p, ref in checks]
    return {"checks": qa, "all_pass": all(c["pass"] for c in qa), "tcp": plan_metrics.tcp_from_dose(dose, target)}
def main():
    q = build_qa()
    OUT.write_text(json.dumps(q, indent=2), encoding="utf-8")
    print(f"W2 TEAM: physics QA all_pass={q['all_pass']} tcp={q['tcp']:.3f}")
if __name__ == "__main__":
    main()
