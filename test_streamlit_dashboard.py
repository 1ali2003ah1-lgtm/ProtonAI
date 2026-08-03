"""
ProtonAI - Test Streamlit Dashboard
دالة البيانات تُختبر على CI؛ العرض يُفعّل على الجهاز بعد pip install streamlit
"""

import pytest
from streamlit_dashboard import (
    build_dashboard_data, render_dashboard, STREAMLIT_AVAILABLE,
)


class TestBuildData:
    def test_keys(self):
        d = build_dashboard_data()
        for k in ["patient", "state", "overall", "overall_symbol",
                  "indicators", "recommendation", "can_deliver", "alerts"]:
            assert k in d

    def test_six_indicators(self):
        d = build_dashboard_data()
        assert len(d["indicators"]) == 6

    def test_delivered_green(self):
        d = build_dashboard_data()
        assert d["state"] == "delivered"
        assert d["overall"] == "GREEN"
        assert d["can_deliver"] is True

    def test_indicator_fields(self):
        d = build_dashboard_data()
        for i in d["indicators"]:
            assert {"name", "label", "symbol", "status"} <= set(i.keys())

    def test_custom_patient(self):
        assert build_dashboard_data("X1")["patient"] == "X1"

    def test_no_alerts_when_green(self):
        assert build_dashboard_data()["alerts"] == []


class TestRender:
    @pytest.mark.skipif(STREAMLIT_AVAILABLE, reason="streamlit مثبت")
    def test_raises_without_streamlit(self):
        # على CI بدون streamlit → RuntimeError واضح
        with pytest.raises(RuntimeError):
            render_dashboard()

    @pytest.mark.skipif(not STREAMLIT_AVAILABLE, reason="streamlit غير مثبت")
    def test_available_on_device(self):
        # على الجهاز: العرض قابل للاستدعاء
        assert callable(render_dashboard)
