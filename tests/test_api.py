"""API contract tests."""
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    b = r.json()
    assert b["developer"] == "Ali Hussein Thajil"
    assert b["status"] in ("healthy", "degraded")


def test_live():
    assert client.get("/live").json()["live"] is True


def test_metrics_format():
    t = client.get("/metrics").text
    assert "protonai_requests_total" in t
    assert "# TYPE" in t


def test_run_completed():
    r = client.post("/api/run", json={"image_shape": [2, 32, 32],
                                      "seed": 42, "nz": 8})
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "completed"
    assert len(b["audit_hash"]) == 64
    assert len(b["chain_hash"]) == 64


def test_run_idempotent():
    p = {"image_shape": [2, 32, 32], "seed": 7, "nz": 8}
    h = {"Idempotency-Key": "k1"}
    a = client.post("/api/run", json=p, headers=h).json()
    b = client.post("/api/run", json=p, headers=h).json()
    assert a["case_id"] == b["case_id"]


def test_run_invalid_shape():
    r = client.post("/api/run", json={"image_shape": [-1, 8, 8],
                                      "seed": 1, "nz": 8})
    assert r.status_code == 422


def test_batch():
    r = client.post("/api/batch", json={
        "cases": [{"image_shape": [2, 16, 16], "seed": i, "nz": 8}
                  for i in range(2)], "parallelism": 2})
    assert r.status_code == 200
    assert r.json()["count"] == 2


def test_audit():
    r = client.get("/api/audit/CASE-1")
    assert r.status_code == 200
    assert r.json()["tamper_evident"] is True


def test_security_headers():
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "X-Request-ID" in r.headers
