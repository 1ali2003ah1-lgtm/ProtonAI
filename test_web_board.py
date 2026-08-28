"""
ProtonAI - Test Interactive Board UI
"""

import pytest
from web_board import UI


class TestHtml:
    def test_rtl(self):
        assert 'dir="rtl"' in UI

    def test_markers(self):
        assert "meter" in UI and "dissent" in UI and "الإجماع" in UI


class TestApi:
    def _client(self):
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")
        from fastapi.testclient import TestClient
        from web_board import app, BOARDS
        return TestClient(app), BOARDS

    def test_board(self):
        c, _ = self._client()
        b = c.get("/api/board/P-001").json()
        assert len(b["participants"]) == 3

    def test_add_opinion(self):
        c, boards = self._client()
        before = len(boards["P-001"].opinions)
        c.post("/api/board/P-001/opinion", json={
            "participant": "د. جديد", "role": "surgeon",
            "recommendation": "PROCEED"})
        assert len(boards["P-001"].opinions) == before + 1
