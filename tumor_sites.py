"""
ProtonAI - Oncology: Tumor Site Registry (خطة توسعة منهجية)
سجل مواقع الأورام مع أولوية توسعة العلاج بالبروتون:
- priority 1 = أعلى فائدة/دليل (أطفال، CNS، قاعدة جمجمة، ساركوما، عين).
- priority 2 = متوسطة (صدر/كبد/هضمي/بروستاتا/لمفوما).
- priority 3 = منخفضة/نادرة الموضعية.
البروتون للآفات الموضعية؛ الجهازية تُستثنى غالباً.
يربط كل موقع بأدوات sample_size و range_margin الموجودة.
"""

from sample_size import sample_size
from range_margin import suggested_margin

# السلوك: BENIGN / MALIGNANT / IN_SITU / UNCERTAIN
SITES = {
    "CNS_brain_spine":   {"behavior": "MALIGNANT", "priority": 1, "motion": 0, "range": 100},
    "head_neck":         {"behavior": "MALIGNANT", "priority": 1, "motion": 2, "range": 100},
    "pediatric_embryonal":{"behavior": "MALIGNANT","priority": 1, "motion": 0, "range": 80},
    "ocular":            {"behavior": "MALIGNANT", "priority": 1, "motion": 1, "range": 40},
    "sarcoma_soft":      {"behavior": "MALIGNANT", "priority": 1, "motion": 1, "range": 120},
    "benign_skull_base": {"behavior": "BENIGN",    "priority": 1, "motion": 0, "range": 100},
    "lung_pleura":       {"behavior": "MALIGNANT", "priority": 2, "motion": 5, "range": 150},
    "liver_biliary":     {"behavior": "MALIGNANT", "priority": 2, "motion": 3, "range": 120},
    "gi":                {"behavior": "MALIGNANT", "priority": 2, "motion": 3, "range": 150},
    "prostate":          {"behavior": "MALIGNANT", "priority": 2, "motion": 1, "range": 150},
    "gynecologic":       {"behavior": "MALIGNANT", "priority": 2, "motion": 2, "range": 130},
    "breast":            {"behavior": "MALIGNANT", "priority": 2, "motion": 2, "range": 60},
    "lymphoma":          {"behavior": "MALIGNANT", "priority": 2, "motion": 1, "range": 120},
    "gu_kidney":         {"behavior": "MALIGNANT", "priority": 3, "motion": 2, "range": 130},
    "germ_cell":         {"behavior": "MALIGNANT", "priority": 3, "motion": 1, "range": 120},
    "skin_melanoma":     {"behavior": "MALIGNANT", "priority": 3, "motion": 0, "range": 40},
    "endocrine":         {"behavior": "MALIGNANT", "priority": 3, "motion": 1, "range": 100},
    "neuroendocrine":    {"behavior": "MALIGNANT", "priority": 3, "motion": 2, "range": 120},
    "in_situ_uncertain": {"behavior": "UNCERTAIN", "priority": 3, "motion": 0, "range": 60},
}


def site_profile(name: str) -> dict:
    if name not in SITES:
        raise KeyError(f"موقع غير معروف: {name}")
    return dict(SITES[name], site=name)


def expansion_order() -> list:
    """ترتيب التوسعة: أولوية ثم اسم"""
    return [n for n, _ in sorted(SITES.items(), key=lambda kv: (kv[1]["priority"], kv[0]))]


def by_priority(p: int) -> list:
    return [n for n in SITES if SITES[n]["priority"] == p]


def site_readiness(name: str, sd: float = 0.08, half_width: float = 0.02) -> dict:
    """لكل موقع: حجم عينة + هامش مدى مقترح (يربط الأدوات الموجودة)"""
    s = site_profile(name)
    return {"site": name, "n": sample_size(sd, half_width),
            "margin_mm": suggested_margin(s["range"], motion_mm=s["motion"])}
