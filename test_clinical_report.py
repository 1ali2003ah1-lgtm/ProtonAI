"""
ProtonAI - Test Clinical Report
"""

from clinical_report import build_report, render_text


class TestReport:
    def test_proceed(self):
        r = build_report("P-001", "prostate", 0.9, 0.02)
        assert r["decision"] == "PROCEED"
        assert r["requires_human_ack"] is True

    def test_red_stops(self):
        r = build_report("P-002", "CNS_brain_spine", 0.9, 0.02, status="RED")
        assert r["decision"] == "STOP"

    def test_margin_positive(self):
        r = build_report("P-003", "lung_pleura", 0.9, 0.02)
        assert r["range_margin_mm"] > 0

    def test_stricter_site(self):
        r = build_report("P-004", "CNS_brain_spine", 0.88, 0.02)
        assert r["decision"] == "REVIEW"


class TestRender:
    def test_contains_key_info(self):
        r = build_report("P-005", "head_neck", 0.9, 0.02)
        txt = render_text(r)
        assert "P-005" in txt and "head_neck" in txt
        assert "يتطلب إقراراً بشرياً" in txt
