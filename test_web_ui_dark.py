"""
ProtonAI - Test Dark Luxury UI
"""

import pytest
from web_ui_dark import UI


class TestHtml:
    def test_rtl(self):
        assert 'dir="rtl"' in UI

    def test_dark(self):
        assert "#0B1220" in UI and "backdrop-filter" in UI

    def test_safety(self):
        assert "أُقرّ" in UI and "ackChk" in UI and "سجل سليم" in UI


class TestApi:
    def _client(self):
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")
        from fastapi.testclient import TestClient
        from web_ui_dark import app
        return TestClient(app)

    def test_cohort(self):
        assert self._client().get("/api/cohort").json()["total"] == 3

    def test_verify(self):
        assert self._client().get("/api/verify/P-001").json()["valid"] is True
