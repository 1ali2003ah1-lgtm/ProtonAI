"""
ProtonAI - Test Premium UI
"""

import pytest
from web_ui_premium import UI


class TestHtml:
    def test_rtl(self):
        assert 'dir="rtl"' in UI

    def test_a11y(self):
        assert "aria-live" in UI and "skip" in UI

    def test_premium_markers(self):
        assert "hero" in UI and "kpis" in UI and "timeline" in UI

    def test_safety(self):
        assert "أُقرّ" in UI and "ackChk" in UI and "سجل سليم" in UI


class TestApi:
    def _client(self):
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")
        from fastapi.testclient import TestClient
        from web_ui_premium import app
        return TestClient(app)

    def test_cases(self):
        assert len(self._client().get("/api/cases").json()) == 3

    def test_cohort(self):
        c = self._client().get("/api/cohort").json()
        assert c["total"] == 3

    def test_verify(self):
        assert self._client().get("/api/verify/P-001").json()["valid"] is True
