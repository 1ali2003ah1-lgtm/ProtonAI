"""W2 TEAM: PBS multi-layer plan + clinical metrics guard (10 tests)."""
from __future__ import annotations
import json
import numpy as np
from fastapi.testclient import TestClient
from tools import beam_model, plan_metrics
ROOT = __import__("pathlib").Path(__file__).resolve().parent
client = TestClient(__import__("server").app)
SHAPE = (16, 8, 8)
def _plan():
    t = np.zeros(SHAPE); t[6:13, 2:6, 2:6] = 1
    spots = beam_model.spot_lattice(8, 8)
    w, dose = beam_model.optimize_spots(SHAPE, spots, t)
    return t, dose
def test_nnls_uniformity():
    t, dose = _plan()
    tv = plan_metrics._tv(dose, t)
    assert float(np.std(tv) / max(np.mean(tv), 1e-9)) < 0.25
def test_energy_mapping():
    e1, e2 = beam_model.range_to_energy(100), beam_model.range_to_energy(200)
    assert e1 < e2 and 100 < e2 < 250
def test_dvh_monotonic():
    t, dose = _plan()
    _, frac = plan_metrics.dvh(dose, t)
    assert np.all(np.diff(frac) <= 1e-9)
def test_ci_range():
    t, dose = _plan()
    assert 0.0 < plan_metrics.conformity(dose, t) <= 1.0
def test_hi_small():
    t, dose = _plan()
    assert plan_metrics.homogeneity(dose, t) < 0.7
def test_r80_near_distal():
    t, dose = _plan()
    r_ref = float(beam_model.default_layers(t)[-1])
    assert abs(plan_metrics.r80(dose.mean((1, 2))) - r_ref) <= 3
def test_oar_sparing():
    t, dose = _plan()
    oar = np.zeros(SHAPE); oar[15:16] = 1
    assert plan_metrics.oar_vlevel(dose, oar) < 0.2
def test_tcp_valid():
    t, dose = _plan()
    assert 0.2 < plan_metrics.tcp_from_dose(dose, t) < 1.0
def test_qa_all_pass():
    q = json.loads((ROOT / "physics_qa.json").read_text(encoding="utf-8"))
    assert q["all_pass"] is True
def test_api_physics_team():
    r = client.get("/api/physics").json()
    assert {"ci", "hi", "r80", "tcp", "uniformity"} <= set(r)
