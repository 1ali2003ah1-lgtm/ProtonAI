"""
ProtonAI - Physics QA (ضبط جودة الأسطول)
لكل سكانر: أقصى انحراف معايرة ← حالة RAG.
- GREEN: ضمن التسامح. AMBER: تجاوز حتى ضعفه. RED: ≥ ضعف التسامح.
الحالة الإجمالية = الأسوأ؛ وقائمة flagged للمتابعة.
تغذي شاشة الفيزيائي بالواجهة (تُركّب باللابتوب).
"""

TOL = 0.03


def scanner_status(max_dev: float, tol: float = TOL) -> str:
    if max_dev >= 2 * tol:
        return "RED"
    if max_dev > tol:
        return "AMBER"
    return "GREEN"


def fleet_qa(scanners: dict, tol: float = TOL) -> dict:
    rows = {}
    for name, devs in scanners.items():
        m = max(devs)
        rows[name] = {"max_dev": round(m, 4), "status": scanner_status(m, tol)}
    statuses = [r["status"] for r in rows.values()]
    overall = ("RED" if "RED" in statuses
               else "AMBER" if "AMBER" in statuses else "GREEN")
    return {"scanners": rows, "overall": overall,
            "flagged": [n for n, r in rows.items() if r["status"] != "GREEN"]}
