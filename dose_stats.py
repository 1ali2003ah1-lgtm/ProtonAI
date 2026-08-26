"""
ProtonAI - Dosimetry: DVH Metrics
مقاييس الجرعة القياسية لتقييم تغطية الهدف وتجانسها:
- D(x): الجرعة التي يستقبلها على الأقل x% من الحجم.
- V(d): نسبة الحجم الذي يستقبل >= d.
- plan_metrics: D95/D98/D50/V100/HI نسبةً للجرعة الموصوفة.
تغذي شاشة المخطط بالواجهة (تُركّب باللابتوب).
"""

import numpy as np


def D(x: float, doses) -> float:
    """Dx — الجرعة المغطاة لـ x% من الحجم"""
    return float(np.percentile(doses, 100 - x))


def V(dose: float, doses) -> float:
    """Vd — نسبة الحجم >= dose"""
    d = np.asarray(doses)
    return float(np.mean(d >= dose))


def plan_metrics(doses, prescription: float) -> dict:
    """مقاييس الخطة نسبةً للوصفة (1.0 = مطابق تماماً)"""
    d = np.asarray(doses, float)
    d95, d98, d50, d2 = (float(np.percentile(d, q)) for q in (5, 2, 50, 98))
    hi = (d2 - d98) / d50 if d50 else 0.0
    return {
        "D95": round(d95 / prescription, 3),
        "D98": round(d98 / prescription, 3),
        "D50": round(d50 / prescription, 3),
        "V100": round(float(np.mean(d >= prescription)), 3),
        "HI": round(hi, 3),
}
