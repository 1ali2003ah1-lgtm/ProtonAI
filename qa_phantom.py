"""
ProtonAI - QA: Phantom Analysis
مقارنة الجرعة المقاسة بالمخططة نقطة‑نقطة (نسبة فرق):
- pass_rate: نسبة النقاط ضمن التسامح (±3% افتراضياً).
- الحالة: GREEN ≥95% • AMBER ≥90% • RED أدنى.
يكمل شاشة الفيزيائي بدليل قياس فعلي.
"""

TOL_PCT = 3.0


def point_diff(measured: float, planned: float) -> float:
    if not planned:
        raise ValueError("الجرعة المخططة صفر/فارغة")
    return 100 * (measured - planned) / planned


def phantom_qa(measured: list, planned: list, tol: float = TOL_PCT) -> dict:
    if not measured or len(measured) != len(planned):
        raise ValueError("قوائم فارغة/غير متطابقة")
    diffs = [round(abs(point_diff(m, p)), 2) for m, p in zip(measured, planned)]
    within = [d <= tol for d in diffs]
    rate = sum(within) / len(within)
    status = ("GREEN" if rate >= 0.95
              else "AMBER" if rate >= 0.90 else "RED")
    return {"diffs": diffs, "pass_rate": round(rate, 3), "status": status}
