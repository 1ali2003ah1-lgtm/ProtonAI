"""B3 v2: radiobiology models - TCP (logistic) + NTCP (Lyman-Kutcher-Burman).

Translates dose deltas into clinical impact: tumor control probability
and normal-tissue complication probability. Parameters are planning
values from literature (documented); surrogate dose scaled to Gy by Rx.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from dose_bridge import compute_dose, dvh_metrics

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "tcp_ntcp_results.json"

RX_GY = 60.0
TCP_D50_GY = 60.0
TCP_GAMMA50 = 2.0
LUNG_TD50 = 30.0     # planning values (literature)
LUNG_M = 0.45
LUNG_N = 0.87


def tcp_logistic(d_gy, d50=TCP_D50_GY, gamma50=TCP_GAMMA50):
    d = np.asarray(d_gy, float)
    safe = np.maximum(d, 1e-9)
    return np.where(d > 0, 1.0 / (1.0 + (d50 / safe) ** (4 * gamma50)), 0.0)


def geud(dose_gy, mask, n=LUNG_N):
    vals = np.asarray(dose_gy)[np.asarray(mask) > 0]
    if vals.size == 0:
        return 0.0
    return float(np.mean(vals ** (1.0 / n)) ** n)


def ntcp_lkb(dose_gy, mask, td50=LUNG_TD50, m=LUNG_M, n=LUNG_N):
    g = geud(dose_gy, mask, n)
    if g <= 0:
        return 0.0
    t = (g - td50) / (m * td50)
    return 0.5 * (1.0 + math.erf(t / math.sqrt(2)))


def clinical_impact(ct, truth, oar, ai, base):
    td, nd = [], []
    for c, t, o, a, b in zip(ct, truth, oar, ai, base):
        da = compute_dose(c, a) * RX_GY
        db = compute_dose(c, b) * RX_GY
        d95a = dvh_metrics(da, t)["D95"]
        d95b = dvh_metrics(db, t)["D95"]
        td.append(float(tcp_logistic(d95a) - tcp_logistic(d95b)))
        nd.append(float(ntcp_lkb(db, o) - ntcp_lkb(da, o)))
    return {"tcp_delta": np.asarray(td), "ntcp_delta": np.asarray(nd)}


def main():
    ct, truth, oar, ai, base = [], [], [], [], []
    for i in range(8):
        c = np.zeros((60, 40)); t = np.zeros((60, 40)); o = np.zeros((60, 40))
        r0 = 20 + i
        t[r0:r0 + 10, 10:30] = 1
        o[r0 + 11:r0 + 18, :] = 1
        ct.append(c); truth.append(t); oar.append(o)
        ai.append(np.roll(t, 1, axis=0)); base.append(np.roll(t, 4, axis=0))
    res = clinical_impact(ct, truth, oar, ai, base)
    out = {"rx_gy": RX_GY, "tcp_d50": TCP_D50_GY, "lung_td50": LUNG_TD50,
           "tcp_delta_mean": float(res["tcp_delta"].mean()),
           "ntcp_delta_mean": float(res["ntcp_delta"].mean())}
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"RADIOBIOLOGY: dTCP={out['tcp_delta_mean']:.3f} "
          f"dNTCP(sparing)={out['ntcp_delta_mean']:.4f}")
    print("Saved -> tcp_ntcp_results.json")


if __name__ == "__main__":
    main()
