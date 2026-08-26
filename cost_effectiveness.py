"""
ProtonAI - Health Economics (QALY / ICER)
مقارنة اقتصادية برتوتون vs فوتون:
- qaly: سنوات حياة معدلة بالجودة.
- icer: كلفة إضافية لكل QALY مكتسب.
- proton_value: هل ضمن عتبة الاستعداد للدفع (WTP)؟
يدعم ملفات التمويل/التأمين واللجان.
"""


def qaly(utility: float, years: float) -> float:
    if not (0 <= utility <= 1):
        raise ValueError("utility لازم بين 0 و1")
    return utility * years


def icer(delta_cost: float, delta_qaly: float) -> float:
    if delta_qaly <= 0:
        raise ValueError("لا فائدة صحية إضافية (ΔQALY ≤ 0)")
    return delta_cost / delta_qaly


def proton_value(cost_p: float, cost_f: float,
                 qaly_p: float, qaly_f: float,
                 wtp: float = 50000) -> dict:
    dq = qaly_p - qaly_f
    if dq <= 0:
        return {"icer": None, "cost_effective": False,
                "note": "لا فائدة صحية إضافية"}
    i = icer(cost_p - cost_f, dq)
    return {"icer": round(i, 1), "cost_effective": i <= wtp,
            "note": f"كلفة/QALY = {i:,.0f} مقابل عتبة {wtp:,.0f}"}
