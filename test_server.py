"""C2 FINAL: NEXUS Enterprise API guard (8 tests)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_summary_keys():
    assert {"kpis", "dose_impact", "d95_verdict"} <= set(
        client.get("/api/summary").json())


def test_presets():
    assert "mediastinum" in client.get("/api/presets").json()


def test_dose_impact():
    assert client.get("/api/dose-impact").status_code == 200


def test_whatif_sensitivity():
    a = client.post("/api/whatif", json={"shift": 0}).json()["d95"]
    b = client.post("/api/whatif", json={"shift": 6}).json()["d95"]
    assert a > 0.9 and a - b > 0.2


def test_dvh_shape():
    r = client.get("/api/dvh?shift=0").json()
    assert len(r["bins"]) == len(r["cum"]) and r["cum"][0] >= r["cum"][-1]


def test_slice_shape():
    r = client.get("/api/slice?z=0").json()
    assert len(r["gray"]) == 60 and len(r["gray"][0]) == 40


def test_index_serves_react():
    r = client.get("/")
    assert r.status_code == 200 and "react" in r.text.lower()
