"""
ProtonAI - API Layer (FastAPI)
طبقة تكامل مؤسسي: /quality /plan /audit.
- المنطق الأساسي دوال نقية (مختبرة بدون fastapi).
- إنشاء الـ app محمي بـ FASTAPI_AVAILABLE.
- مبدأ CDSS: كل استجابة تحمل requires_human_ack=True (القرار بشري).
"""

import logging

logger = logging.getLogger("ProtonAI.API")

try:
    from fastapi import FastAPI
    FASTAPI_AVAILABLE = True
except Exception:  # pragma: no cover
    FastAPI = None
    FASTAPI_AVAILABLE = False

from gov_audit_log import AuditLog

CDSS_NOTE = "ProtonAI نظام دعم قرار (CDSS) — القرار النهائي بشري دائماً"


def quality_response(data: dict) -> dict:
    """استجابة مؤشرات الجودة + عدم اليقين + إقرار بشري إجباري"""
    return {
        "status": data.get("status", "GREEN"),
        "indicators": data.get("indicators", {}),
        "uncertainty": data.get("uncertainty", {}),
        "requires_human_ack": True,
        "note": CDSS_NOTE,
    }


def plan_response(data: dict) -> dict:
    """استجابة خطة مقترحة (توصية فقط، غير ملزمة)"""
    return {
        "recommendation": data.get("recommendation", "review"),
        "range_margin_mm": data.get("range_margin_mm", 3.5),
        "requires_human_ack": True,
        "note": CDSS_NOTE,
    }


def audit_response(log_path) -> dict:
    """حالة سجل التدقيق + سلامته"""
    a = AuditLog(log_path)
    return {"entries": a.entries(), "intact": a.verify()}


if FASTAPI_AVAILABLE:
    app = FastAPI(title="ProtonAI", version="1.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "CDSS"}

    @app.post("/quality")
    def quality(data: dict):
        return quality_response(data)

    @app.post("/plan")
    def plan(data: dict):
        return plan_response(data)

    @app.get("/audit")
    def audit(log_path: str = "audit.log"):
        return audit_response(log_path)
