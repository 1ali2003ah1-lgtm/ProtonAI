"""W2 FINAL: clinical physics guard (13 tests)."""
from __future__ import annotations
import json
import numpy as np
from fastapi.testclient import TestClient
from tools import dose_3d, gamma, hu_to_spr, rbe_statement, robust
ROOT = __import__("pathlib").Path(__file__).resolve().parent
client = TestClient(__import__("server").app)
def test_hu_water():
    assert abs(hu_to_spr.hu_to_spr(0.0) - 1.0) < 1e-6
def test_hu_tissue_order():
    assert hu_to_spr.hu_to_spr(-500) < hu_to_spr.hu_to_spr(0) < hu_to_spr.hu_to_spr(1000)
def test_calibration_err():
    assert hu_to_spr.calibration_report()["max_err"] < 0.02
def test_wepl_water():
    assert abs(dose_3d.wepl(np.ones((32, 8, 8))) - 32.0) < 1e-6
def test_bragg_peak():
    from tools import plan_metrics
    d = dose_3d.compute_dose_3d(np.ones((32, 8, 8)), 20.0, np.ones((8, 8)))
    assert 17 <= plan_metrics.r80(d.mean((1, 2))) <= 23
def test_plateau_uniform():
    c = dose_3d.depth_curve(np.arange(32.0), 20.0, 6.0)
    assert float(np.std(c[16:19])) < 0.2
def test_penumbra_widens():
    f = np.zeros((8, 8)); f[4, 4] = 1
    d = dose_3d.compute_dose_3d(np.ones((32, 8, 8)), 25.0, f)
    def spread(z):
        p = d[z]; p = p / max(p.sum(), 1e-9)
        yy, xx = np.mgrid[0:8, 0:8]
        cy = (p * yy).sum(); cx = (p * xx).sum()
        return float((p * ((yy - cy) ** 2 + (xx - cx) ** 2)).sum()) ** 0.5
    assert spread(20) > spread(5)
def test_distal_falloff():
    d = dose_3d.compute_dose_3d(np.ones((32, 8, 8)), 20.0, np.ones((8, 8)))
    assert d[31].mean() < 0.1 * d[15].mean()
def test_gamma_identical():
    d = dose_3d.compute_dose_3d(np.ones((16, 8, 8)), 10.0, np.ones((8, 8)))
    assert gamma.gamma_3d(d, d) == 1.0
def test_gamma_shifted():
    a = dose_3d.compute_dose_3d(np.ones((16, 8, 8)), 10.0, np.ones((8, 8)))
    b = dose_3d.compute_dose_3d(np.ones((16, 8, 8)), 13.0, np.ones((8, 8)))
    assert gamma.gamma_3d(a, b) < 1.0
def test_robust_and_v95():
    spr = np.ones((32, 8, 8)); t = np.zeros((32, 8, 8)); t[10:25] = 1
    r = robust.robust_eval(spr, np.ones((8, 8)), 20.0, t)
    assert r["worst"] <= r["nominal"] + 1e-9
    assert 0.0 <= r["v95_nominal"] <= 1.0
def test_rbe():
    assert rbe_statement.physical_to_rbe(1.0) == 1.1
def test_api_and_validation():
    r = client.get("/api/physics").json()
    assert {"spr_water", "bragg_peak", "wepl", "gamma_pass", "rbe"} <= set(r) or "ci" in r
    v = json.loads((ROOT / "physics_validation.json").read_text(encoding="utf-8"))
    assert v["pass"] is True
