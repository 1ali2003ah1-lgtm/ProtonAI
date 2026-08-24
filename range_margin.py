"""
ProtonAI - Physics/Clinical: Range Uncertainty Budget
حساب عدم يقين المدى من مصادره (setup/معايرة/كثافة/حركة) بجمع تربيعي،
واقتراح هامش مدى = k × عدم اليقين (مدوّر لأقرب 0.5 مم).
يربط معايرة HU→RSP وrobustness بالقرار السريري.
"""

import math


def components(range_mm: float, rsp_unc: float = 0.03,
               setup_mm: float = 3.0, motion_mm: float = 0.0,
               density_pct: float = 0.03) -> dict:
    """مكونات عدم اليقين (مم)"""
    return {
        "setup": setup_mm,
        "motion": motion_mm,
        "calibration": rsp_unc * range_mm,
        "density": density_pct * range_mm,
    }


def total_uncertainty(range_mm: float, **kw) -> float:
    """الجمع التربيعي للمكونات"""
    c = components(range_mm, **kw)
    return math.sqrt(sum(v ** 2 for v in c.values()))


def suggested_margin(range_mm: float, k: float = 2.0, **kw) -> float:
    """هامش مقترح = k × عدم اليقين، مدوّر لأعلى لأقرب 0.5 مم"""
    raw = k * total_uncertainty(range_mm, **kw)
    return math.ceil(raw * 2) / 2
