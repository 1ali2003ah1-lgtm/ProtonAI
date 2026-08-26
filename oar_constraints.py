"""
ProtonAI - Clinical: OAR Constraints (QUANTEC-style)
كتالوج حدود الأعضاء الحساسة لكل موقع ورم + تقييم خطة:
- GREEN: كل الحدود مريحة. AMBER: اقتربنا (≥95% من الحد). RED: تجاوز.
يربط tumor_sites بشاشة المخطط/الفيزيائي.
"""

OAR_CONSTRAINTS = {
    "CNS_brain_spine": [
        {"oar": "SpinalCord", "metric": "cord_Dmax", "limit": 45.0},
        {"oar": "Brainstem", "metric": "bs_Dmax", "limit": 54.0},
    ],
    "head_neck": [
        {"oar": "Parotid", "metric": "parotid_mean", "limit": 26.0},
        {"oar": "SpinalCord", "metric": "cord_Dmax", "limit": 45.0},
    ],
    "lung_pleura": [
        {"oar": "Lung", "metric": "lung_V20", "limit": 35.0},
        {"oar": "Lung", "metric": "lung_MLD", "limit": 20.0},
    ],
    "prostate": [
        {"oar": "Rectum", "metric": "rectum_V70", "limit": 15.0},
        {"oar": "Bladder", "metric": "bladder_V70", "limit": 25.0},
    ],
}

WARN = 0.95


def constraints_for(site: str) -> list:
    if site not in OAR_CONSTRAINTS:
        raise KeyError(f"موقع بدون كتالوج: {site}")
    return OAR_CONSTRAINTS[site]


def evaluate(site: str, achieved: dict) -> dict:
    rows, status = [], "GREEN"
    for c in constraints_for(site):
        if c["metric"] not in achieved:
            continue
        v = achieved[c["metric"]]
        viol = v > c["limit"]
        close = (not viol) and v >= WARN * c["limit"]
        rows.append({**c, "value": v, "violated": viol, "close": close})
        if viol:
            status = "RED"
        elif close and status != "RED":
            status = "AMBER"
    return {"rows": rows, "status": status}
