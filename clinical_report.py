"""
ProtonAI - Clinical Report (تقرير الحالة الموحّد)
يجمع كل الطبقات بمخرَج واحد يقرأه الطبيب:
مقاييس AI + هامش مدى + قرار بوابـة الموقع + أسباب + إقرار بشري.
لا يستقبل إلا pseudonym — صفر PHI بالتصميم.
"""

from site_decision import site_evaluate
from range_margin import suggested_margin
from tumor_sites import site_profile

REPORT_VERSION = "1.0"


def build_report(case_id: str, site: str, dice: float, ece: float,
                 status: str = "GREEN", range_mm: float = None,
                 uncertainty: float = 0.1) -> dict:
    """تقرير حالة موحّد لكل مريض (pseudonym فقط)"""
    prof = site_profile(site)
    margin = suggested_margin(range_mm or prof["range"],
                              motion_mm=prof["motion"])
    dec = site_evaluate(site, status=status, dice=dice, ece=ece)
    return {
        "case_id": case_id,
        "site": site,
        "metrics": {"dice": dice, "ece": ece, "uncertainty": uncertainty},
        "range_margin_mm": margin,
        "decision": dec["decision"],
        "reasons": dec["reasons"],
        "requires_human_ack": True,
        "version": REPORT_VERSION,
    }


def render_text(r: dict) -> str:
    """نسخة مقروءة للطبيب"""
    lines = [
        f"تقرير حالة: {r['case_id']}",
        f"الموقع: {r['site']}",
        f"Dice: {r['metrics']['dice']:.2f} | ECE: {r['metrics']['ece']:.2f}",
        f"هامش المدى المقترح: {r['range_margin_mm']:.1f} مم",
        f"القرار: {r['decision']}",
    ]
    if r["reasons"]:
        lines.append("الأسباب: " + "؛ ".join(r["reasons"]))
    lines.append("يتطلب إقراراً بشرياً: نعم")
    return "\n".join(lines)
