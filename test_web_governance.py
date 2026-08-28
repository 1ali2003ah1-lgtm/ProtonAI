"""
ProtonAI - Test Governance Dashboard
"""

import pytest
from web_governance import UI


class TestHtml:
    def test_rtl(self):
        assert 'dir="rtl"' in UI

    def test_markers(self):
        assert "posture" in UI and "alerts" in UI and "التنبيهات" in UI

    def test_a11y(self):
        assert "aria-live" in UI


class TestApi:
    def _client(self):
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")
        from fastapi.testclient import TestClient
        from web_governance import app
        return TestClient(app)

    def test_governance(self):
        g = self._client().get("/api/governance").json()
        assert g["posture"] in ("GREEN", "AMBER", "RED")
        assert isinstance(g["alerts"], list)
        assert "الوضعية العامة" in g["summary"]
