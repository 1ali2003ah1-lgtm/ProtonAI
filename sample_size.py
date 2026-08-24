"""
ProtonAI - Statistics: Sample Size
حاسبة حجم العينة لتقدير متوسط بدقة محددة:
n = (Z × SD / half-width)²  (مدوّرة لأعلى).
- per_site_plan: حجم عينة لكل موقع/ورم.
- pilot_reestimate: إعادة الضبط بعد حساب SD الفعلي من الـ pilot.
"""

import math

Z_95 = 1.96


def sample_size(sd: float, half_width: float, z: float = Z_95) -> int:
    """حجم العينة اللازم لتقدير متوسط بنصف عرض CI محدد"""
    if half_width <= 0 or sd < 0:
        raise ValueError("قيم غير صالحة")
    return math.ceil((z * sd / half_width) ** 2)


def per_site_plan(sd_by_site: dict, half_width: float = 0.02) -> dict:
    """حجم عينة لكل موقع/ورم"""
    return {site: sample_size(sd, half_width)
            for site, sd in sd_by_site.items()}


def pilot_reestimate(pilot_sd: float, half_width: float = 0.02) -> int:
    """إعادة ضبط n بعد SD الفعلي من الـ pilot"""
    return sample_size(pilot_sd, half_width)
