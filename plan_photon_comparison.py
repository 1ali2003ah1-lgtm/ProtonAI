"""
ProtonAI - Proton vs Photon Comparison
يكمّم ميزة البروتون مقابل مرجع الفوتون المعياري:
- oar_sparings: وفورات لكل عضو حساس (Gy).
- integral_reduction: انخفاض الجرعة المتكاملة (%).
- favors_proton: قرار منطقي مبني على الوفرات.
يُستخدم كطبقة فوق PlanComparison (لا يستبدله).
"""

from photon_benchmark import photon_ref_for, integral_dose_photon


def oar_sparings(site: str, achieved_proton: dict) -> dict:
    ref = photon_ref_for(site)
    return {metric: round(ref[metric] - achieved_proton.get(metric, 0), 2)
            for metric in ref}


def integral_reduction(site: str, integral_proton: float) -> float:
    ref = integral_dose_photon(site)
    if ref == 0:
        return 0.0
    return round(100 * (ref - integral_proton) / ref, 1)


def favors_proton(site: str, achieved_proton: dict,
                  integral_proton: float) -> dict:
    sparings = oar_sparings(site, achieved_proton)
    red = integral_reduction(site, integral_proton)
    all_non_neg = all(v >= 0 for v in sparings.values())
    verdict = red > 0 and all_non_neg
    return {"sparings": sparings, "integral_reduction_pct": red,
            "favors_proton": verdict}
