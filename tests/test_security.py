"""Security tests."""
from fastapi.testclient import TestClient

from server import app, limiter

client = TestClient(app)


def test_invalid_json():
    r = client.post("/api/run", content=b"bad",
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_nz_bounds():
    r = client.post("/api/run", json={"image_shape": [2, 8, 8],
                                      "seed": 1, "nz": 999})
    assert r.status_code == 422


def test_rate_limiter_blocks():
    limiter.buckets.clear()
    for _ in range(15):
        limiter.allow("tk")
    assert not limiter.allow("tk")


def test_headers_everywhere():
    for p in ("/health", "/live", "/metrics", "/"):
        r = client.get(p)
        assert "X-Content-Type-Options" in r.headers
