"""
ProtonAI - Test Web UI
"""

from fastapi.testclient import TestClient
from web_ui import app

client = TestClient(app)


class TestUI:
    def test_index(self):
        r = client.get("/")
        assert r.status_code == 200
        assert 'dir="rtl"' in r.text
        assert "aria-live" in r.text
        assert "أُقرّ" in r.text

    def test_cases(self):
        r = client.get("/api/cases")
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_case_detail(self):
        r = client.get("/api/case/P-003")
        assert r.json()["decision"] == "STOP"

    def test_ack(self):
        r = client.post("/api/ack", json={"case_id": "P-001", "name": "د. X"})
        assert r.json()["ok"] is True
