"""
ProtonAI - Physics: PSTAR Validation
مقارنة مدى البروتون بالماء (نموذجنا) بقيم PSTAR المنشورة (NIST).
يكمل شرط "مقارنة مراجع منشورة" من المرحلة B — بدون GPU.
"""

# قيم PSTAR (NIST) لمدى البروتون بالماء بالسنتيمتر
PSTAR_WATER_CM = {
    50: 2.20,
    100: 7.72,
    150: 15.8,
    200: 25.9,
    250: 37.9,
}

TOLERANCE = 0.03  # 3%


def our_range_cm(energy: float) -> float:
    """نموذج المدى التحليلي عندنا"""
    return 0.0022 * (energy ** 1.77)


def validate(tol: float = TOLERANCE) -> dict:
    """مقارنة بكل طاقة + أقصى انحراف؛ وهل ضمن التسامح"""
    rows = []
    max_rel = 0.0
    for e, ref in sorted(PSTAR_WATER_CM.items()):
        ours = our_range_cm(e)
        rel = abs(ours - ref) / ref
        max_rel = max(max_rel, rel)
        rows.append({"energy": e, "pstar": ref, "ours": round(ours, 2),
                     "rel_diff": round(rel, 4)})
    return {"rows": rows, "max_rel_diff": round(max_rel, 4),
            "within_tolerance": max_rel <= tol}
