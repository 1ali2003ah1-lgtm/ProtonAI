"""
ProtonAI - Photon Reference Benchmark (من الأدبيات)
مرجع معياري لأرقام الفوتون (IMRT/VMAT) حسب موقع الورم،
للمقارنة الموضوعية مع البروتون. المصادر: QUANTEC, TG-101, أدبيات NRG.
"""

PHOTON_REFERENCE = {
    "lung_pleura":   {"lung_V20": 35.0, "lung_MLD": 20.0, "heart_MLD": 15.0},
    "head_neck":     {"parotid_mean": 26.0, "cord_Dmax": 45.0, "oral_mean": 40.0},
    "prostate":      {"rectum_V70": 15.0, "bladder_V70": 25.0},
    "CNS_brain_spine":{"cord_Dmax": 45.0, "brainstem_Dmax": 54.0},
    "pediatric_embryonal":{"integral_dose_Gy_cm3": 180.0, "hip_MLD": 35.0},
}


def photon_ref_for(site: str) -> dict:
    if site not in PHOTON_REFERENCE:
        raise KeyError(f"لا مرجع فوتون لهذا الموقع: {site}")
    return PHOTON_REFERENCE[site]


def integral_dose_photon(site: str) -> float:
    """جرعة متكاملة مرجعية للفوتون (تقدير أدبي)"""
    defaults = {"lung_pleura": 220, "prostate": 140, "pediatric_embryonal": 180}
    return defaults.get(site, 180.0)
