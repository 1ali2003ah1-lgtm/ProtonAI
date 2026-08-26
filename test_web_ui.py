"""
ProtonAI - Test Web UI
"""

import pytest
from web_ui import UI_HTML


class TestHtml:
    def test_rtl(self):
        assert 'dir="rtl"' in UI_HTML

    def test_a11y(self):
        assert "aria-live" in UI_HTML and "skip" in UI_HTML

    def test_ack_forced(self):
        assert "أُقرّ" in UI_HTML and "ackChk" in UI_HTML


class TestApi:
    def _client(self):
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")
        from fastapi.testclient import TestClient
        from web_ui import app
        return TestClient(app)

    def test_cases(self):
        assert len(self._client().get("/api/cases").json()) == 3

    def test_stop_case(self):
        assert self._client().get("/api/case/P-003").json()["decision"] == "STOP"

    def test_ack(self):
        r = self._client().post("/api/ack", json={"case_id": "P-001", "name": "د. X"})
        assert r.json()["ok"] is True
