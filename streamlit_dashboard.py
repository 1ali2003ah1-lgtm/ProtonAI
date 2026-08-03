"""
ProtonAI - Streamlit Dashboard (Device Phase)
لوحة حية تفاعلية على الجهاز. فصل البيانات عن العرض:
build_dashboard_data (نقية، تُختبر على CI) ← render_dashboard (Streamlit على الجهاز)
pip install streamlit  ←  يفعّل العرض على جهازك
"""

import logging
from typing import Dict, Any, List, Optional

from plan_orchestrator import PlanOrchestrator
from monitoring import Monitoring

logger = logging.getLogger("ProtonAI.StreamlitDashboard")

try:  # استيراد محروس — لا يكسر CI بدون streamlit
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except Exception:  # pragma: no cover
    st = None
    STREAMLIT_AVAILABLE = False

_GOOD_PHYSICS = {"gamma_pass_rate": 0.97, "range_in_target": True,
                 "coverage_drop": 0.02, "benchmark_passed": True}


def _providers():
    return {
        "imaging": lambda p: {"modality": "CT", "slices": 120},
        "physics": lambda p: dict(_GOOD_PHYSICS),
        "ai": lambda p: {"predicted": "M", "confidence": 0.91},
        "reviews": lambda p: {"signed": True},
    }


def build_dashboard_data(patient_id: str = "DEMO_DASH") -> Dict[str, Any]:
    """تجميع بيانات اللوحة (نقية، بدون streamlit) — تُختبر على CI"""
    clin = PlanOrchestrator().run(
        providers=_providers(), patient_id=patient_id,
        physician_signed=True, physics_signed=True,
        specialist_decision="approve", specialist_id="dr_dash")
    overall = clin["evaluation"]["overall"].name
    mon = Monitoring()
    mon.add_overalls([overall])
    indicators: List[Dict[str, Any]] = [
        {"name": i["name"], "label": i["label"], "symbol": i["symbol"],
         "status": i["status"]}
        for i in clin["dashboard"]["indicators"]
    ]
    return {
        "patient": patient_id,
        "state": clin["state"],
        "overall": overall,
        "overall_symbol": clin["dashboard"]["overall_symbol"],
        "indicators": indicators,
        "recommendation": clin["decision"].recommendation.value,
        "can_deliver": clin["decision"].can_deliver,
        "alerts": mon.alerts(),
    }


def render_dashboard(data: Optional[Dict[str, Any]] = None) -> None:
    """عرض اللوحة بـ Streamlit (على الجهاز فقط)"""
    if not STREAMLIT_AVAILABLE:
        raise RuntimeError(
            "streamlit غير مثبت — ثبّته على جهازك (pip install streamlit)")
    data = data or build_dashboard_data()
    st.set_page_config(page_title="ProtonAI Dashboard", layout="wide")
    st.title(f"{data['overall_symbol']} ProtonAI — لوحة دعم القرار")
    c1, c2, c3 = st.columns(3)
    c1.metric("المريض (مخفي)", data["patient"])
    c2.metric("الحالة", data["state"])
    c3.metric("التوصية", data["recommendation"])
    st.subheader("مؤشرات الجودة")
    st.table(data["indicators"])
    st.subheader("التنبيهات")
    if data["alerts"]:
        for a in data["alerts"]:
            st.warning(a["message"])
    else:
        st.success("لا تنبيهات — النظام سليم")


def main():  # pragma: no cover
    render_dashboard()


if __name__ == "__main__":  # pragma: no cover
    main()
