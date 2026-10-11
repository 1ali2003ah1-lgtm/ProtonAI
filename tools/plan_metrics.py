from __future__ import annotations
import numpy as np
def _tv(dose, mask):
    return np.asarray(dose, float)[np.asarray(mask, float) > 0.5]
def dvh(dose, mask, bins=32):
    v = _tv(dose, mask)
    h, e = np.histogram(v, bins=bins, range=(0, float(np.max(dose)) + 1e-9))
    frac = np.cumsum(h[::-1])[::-1] / max(v.size, 1)
    return 0.5 * (e[1:] + e[:-1]), frac
def pct(dose, mask, p):
    return float(np.percentile(_tv(dose, mask), p))
def d95(dose, mask):
    return pct(dose, mask, 5)
def dmean(dose, mask):
    return float(np.mean(_tv(dose, mask)))
def conformity(dose, target, presc=1.0):
    tv = (np.asarray(target, float) > 0.5).sum()
    vref = (np.asarray(dose, float) >= 0.95 * presc).sum()
    tvref = ((np.asarray(target, float) > 0.5) & (np.asarray(dose, float) >= 0.95 * presc)).sum()
    return float(tvref ** 2 / (tv * vref)) if vref else 0.0
def homogeneity(dose, target, presc=1.0):
    return (pct(dose, target, 95) - pct(dose, target, 5)) / presc
def r80(profile):
    p = np.asarray(profile, float); i = int(np.argmax(p))
    after = p[i:]
    j = np.argmax(after <= 0.8 * p[i]) if (after <= 0.8 * p[i]).any() else 0
    return i + int(j)
def oar_vlevel(dose, oar, level=0.2, presc=1.0):
    v = _tv(dose, oar)
    return float(np.mean(v > level * presc)) if v.size else 0.0
def tcp_from_dose(dose, target, presc_gy=60.0, d50=60.0, k=5.0):
    dm = dmean(dose, target) * presc_gy
    return float(1 / (1 + np.exp(-(dm - d50) / k)))
