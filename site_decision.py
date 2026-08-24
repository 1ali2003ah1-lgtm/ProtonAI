"""
ProtonAI - Oncology: Site-aware Decision
عتبات قرار مخصصة لكل موقع ورم:
- priority 1 (أطفال/CNS/قاعدة جمجمة): أشد صرامة (Dice≥0.90، ECE≤0.03).
- الباقي: الأهداف القياسية (Dice≥0.85، ECE≤0.05).
يربط سجل الأورام ببوابة القرار بمبدأ CDSS (إقرار بشري إجباري).
"""

from tumor_sites import site_profile


def site_thresholds(site: str) -> dict:
    """عتبات لكل موقع حسب أولويته/خطورته"""
    p = site_profile(site)
    if p["priority"] == 1:
        return {"dice": 0.90, "ece": 0.03}
    return {"dice": 0.85, "ece": 0.05}


def site_evaluate(site: str, status: str = "GREEN",
                  dice: float = 0.95, ece: float = 0.02) -> dict:
    """قرار موحّد بعتبات الموقع"""
    th = site_thresholds(site)
    stop, review = [], []
    if status == "RED":
        stop.append("حالة RED: إيقاف ومراجعة إجبارية")
    if status == "AMBER":
        review.append("حالة AMBER")
    if dice < th["dice"]:
        review.append(f"Dice ({dice:.2f}) < هدف الموقع ({th['dice']})")
    if ece > th["ece"]:
        review.append(f"ECE ({ece:.2f}) > هدف الموقع ({th['ece']})")
    decision = "STOP" if stop else ("REVIEW" if review else "PROCEED")
    return {"site": site, "thresholds": th, "decision": decision,
            "reasons": stop + review, "requires_human_ack": True}
