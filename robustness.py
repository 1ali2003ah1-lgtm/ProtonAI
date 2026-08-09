"""
ProtonAI - Physics: Robustness Evaluation (4D / setup / density)
تقييم متانة الخطة تحت سيناريوهات إزاحة setup، اضطراب كثافة، وحركة تنفسية.
- worst_case: أدنى تغطية هدف عبر كل السيناريوهات.
- status: GREEN/AMBER/RED حسب مقدار التدهور (RED عند >5%).
"""

COST_PER_FULL_DEVIATION = 0.02  # كل انحراف كامل بالهامش يكلف 2% تغطية


def default_scenarios():
    """سيناريوهات قياسية: اسم + setup_mm + density_pct + motion_mm"""
    return [
        {"name": "nominal", "setup_mm": 0, "density_pct": 0, "motion_mm": 0},
        {"name": "setup+3", "setup_mm": 3, "density_pct": 0, "motion_mm": 0},
        {"name": "setup-3", "setup_mm": -3, "density_pct": 0, "motion_mm": 0},
        {"name": "density+3", "setup_mm": 0, "density_pct": 3, "motion_mm": 0},
        {"name": "density-3", "setup_mm": 0, "density_pct": -3, "motion_mm": 0},
        {"name": "motion+5", "setup_mm": 0, "density_pct": 0, "motion_mm": 5},
        {"name": "combined", "setup_mm": 3, "density_pct": 3, "motion_mm": 5},
    ]


def coverage_under(nominal: float, sc: dict,
                   setup_margin: float = 3.0, motion_margin: float = 5.0) -> float:
    """التغطية المتوقعة تحت سيناريو (نموذج عقوبات خطي بسيط)"""
    pen = (abs(sc["setup_mm"]) / setup_margin) * COST_PER_FULL_DEVIATION \
        + (abs(sc["density_pct"]) / 3.0) * COST_PER_FULL_DEVIATION \
        + (abs(sc["motion_mm"]) / motion_margin) * COST_PER_FULL_DEVIATION
    return max(0.0, nominal - pen)


def worst_case(nominal: float, setup_margin: float = 3.0,
               motion_margin: float = 5.0) -> dict:
    """أدنى تغطية عبر السيناريوهات + اسم أسوأ سيناريو"""
    results = [
        {"name": sc["name"],
         "coverage": coverage_under(nominal, sc, setup_margin, motion_margin)}
        for sc in default_scenarios()
    ]
    worst = min(results, key=lambda r: r["coverage"])
    return {"nominal": nominal, "worst_coverage": worst["coverage"],
            "worst_scenario": worst["name"], "all": results}


def status(nominal: float, worst_coverage: float) -> str:
    """GREEN ≤2% تدهور، AMBER ≤5%، RED >5%"""
    deg = nominal - worst_coverage
    if deg <= 0.02:
        return "GREEN"
    if deg <= 0.05:
        return "AMBER"
    return "RED"
