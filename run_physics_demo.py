"""
ProtonAI - Stage-5 Physics Demo
المايسترو النهائي: يربط كل وحدات المرحلة 5 بتقرير واحد موثّق
محرك ← مدى (ماء+مادة من HU) ← SOBP ← عدم يقين ← Gamma ← benchmark ← adaptive ← review
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from proton_physics import ProtonPhysics
from range_uncertainty import RangeUncertainty
from dose_uncertainty import DoseUncertainty
from gamma_index import GammaIndex
from physics_benchmark import PhysicsBenchmark
from adaptive_physics import AdaptivePhysics
from physics_review import PhysicsReviewLoop
from scientific_report import ScientificReport

logger = logging.getLogger("ProtonAI.PhysicsStage5")


def run_physics_demo(
    energy_mev: Optional[float] = None,
    target_start_mm: float = 40.0,
    target_end_mm: float = 60.0,
    rbe: float = 1.1,
    hu_profile_1d: Any = None,
    voxel_mm: float = 1.0,
    evaluated_curve: Any = None,
    plan_profile: Any = None,
    current_profile: Any = None,
    depths: Any = None,
    uncertainty: float = 0.035,
    dd_percent: float = 3.0,
    dta_mm: float = 3.0,
    distal_depth: Optional[float] = None,
    sample_id: str = "physics_demo",
    physics: Optional[ProtonPhysics] = None,
    review_loop: Optional[PhysicsReviewLoop] = None,
    output_dir: Optional[str | Path] = None,
    n_peaks: int = 5,
    sigma_mm: float = 2.0,
    dose_threshold_frac: float = 0.95,
) -> Dict[str, Any]:
    """
    تشغيل تحليل المرحلة 5 الكامل، يرجع قاموساً شاملاً + يحفظ التقارير إن طُلب.
    dose_threshold_frac: عتبة "الجرعة الفعّالة" للتقييم التكيّفي (مرونة للسيناريوهات).
    """
    if target_end_mm <= target_start_mm:
        raise ValueError("target_end_mm يجب أن يكون > target_start_mm")

    phys = physics if physics is not None else ProtonPhysics()

    # 1) الطاقة: مُمرَّرة أو محسوبة عكسياً من حافة الهدف (SOBP يوقف هناك)
    if energy_mev is None:
        energy_mev = phys.energy_from_range_mm(target_end_mm)
    if energy_mev <= 0:
        raise ValueError("energy_mev يجب أن يكون > 0")

    # 2) المدى: ماء + مادة (الجسر مع التصوير إن مُرّر HU)
    water_range = phys.water_range_mm(energy_mev)
    medium_range = (phys.proton_range_in_medium(energy_mev, hu_profile_1d, voxel_mm)
                    if hu_profile_1d is not None else None)

    # 3) أعماق التقييم + منحنى SOBP الاسمي
    if depths is None:
        depths = np.arange(0.0, target_end_mm + 40.0, 1.0)
    z = np.asarray(depths, dtype=float)
    nominal = phys.sobp(z, target_start_mm, target_end_mm,
                        n_peaks=n_peaks, sigma_mm=sigma_mm)
    evaluated = (np.asarray(evaluated_curve, dtype=float)
                 if evaluated_curve is not None else nominal.copy())

    # 4) Gamma (nominal vs evaluated)
    gamma = GammaIndex(dd_percent=dd_percent, dta_mm=dta_mm).evaluate(nominal, evaluated, z)

    # 5) عدم يقين المدى + تغطية الهدف
    range_unc = RangeUncertainty(phys, default_uncertainty=uncertainty)
    band = range_unc.range_band(water_range)
    cov_info = range_unc.target_coverage(water_range, target_start_mm, target_end_mm)
    range_in_target = bool(cov_info["covers_target"])

    # 6) عدم يقين الجرعة (robustness + distal)
    dose_unc = DoseUncertainty(phys, default_uncertainty=uncertainty,
                               n_peaks=n_peaks, sigma_mm=sigma_mm)
    robust = dose_unc.target_dose_robustness(z, target_start_mm, target_end_mm)
    dd = target_end_mm + 10.0 if distal_depth is None else float(distal_depth)
    distal = dose_unc.distal_dose_worst(z, target_start_mm, target_end_mm, dd)

    # 7) المعايير الفيزيائية
    benchmark = PhysicsBenchmark(phys).summary()

    # 8) التكيّف (حركة الورم vs تغطية الجرعة) — بعتبة تغطية قابلة للضبط
    plan = (np.asarray(plan_profile).astype(bool) if plan_profile is not None
            else (z >= target_start_mm) & (z <= target_end_mm))
    current = (np.asarray(current_profile).astype(bool) if current_profile is not None
               else plan.copy())
    adaptive = AdaptivePhysics().evaluate(
        plan, current, nominal, dose_threshold_frac=dose_threshold_frac)
    coverage_drop = float(adaptive["coverage_drop"])

    # 9) حلقة مراجعة الفيزيائي الطبي
    review = review_loop if review_loop is not None else PhysicsReviewLoop()
    req = review.flag_physics(
        sample_id, water_range,
        gamma_pass_rate=gamma["pass_rate"], coverage_drop=coverage_drop,
        range_in_target=range_in_target, rbe=rbe)
    review_stats = review.physics_stats()

    # 10) جرعة RBE-weighted (مثال سريري)
    rbe_dose_example = float(phys.rbe_dose(robust["nominal_mean"], rbe))

    # 11) التقرير (نستبعد مصفوفة gamma الكبيرة من العرض)
    gamma_view = {k: v for k, v in gamma.items() if k != "gamma"}
    report = ScientificReport(
        title="ProtonAI Stage-5 Physics Report", dataset_name="physics demo")
    report.add_section("Physics Core", {"type": "raw", "data": {
        "energy_mev": energy_mev, "water_range_mm": water_range,
        "medium_range_mm": medium_range, "rbe": rbe,
        "rbe_dose_example": rbe_dose_example}})
    report.add_section("Range Uncertainty", {"type": "raw", "data": {
        "band": band, "target_coverage": cov_info}})
    report.add_section("Dose Uncertainty", {"type": "raw", "data": {
        "robustness": robust, "distal": distal}})
    report.add_section("Gamma Index", {"type": "raw", "data": gamma_view})
    report.add_section("Physics Benchmark", {"type": "raw", "data": benchmark})
    report.add_section("Adaptive Evaluation", {"type": "raw", "data": adaptive})
    report.add_section("Physics Review", {"type": "raw", "data": {
        "flagged_request_id": (req.request_id if req else None),
        "stats": review_stats}})

    result = {
        "energy_mev": energy_mev, "water_range_mm": water_range,
        "medium_range_mm": medium_range, "rbe": rbe,
        "rbe_dose_example": rbe_dose_example,
        "range_uncertainty": {"band": band, "target_coverage": cov_info},
        "dose_uncertainty": {"robustness": robust, "distal": distal},
        "gamma": gamma, "benchmark": benchmark, "adaptive": adaptive,
        "physics_review": {"flagged_request_id": (req.request_id if req else None),
                           "stats": review_stats},
        "report_markdown": report.to_markdown(),
    }

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        report.save_markdown(out / "physics_report.md")
        report.save_json(out / "physics_report.json")
        review.save(out / "physics_review.json")
        logger.info(f"تم حفظ تحليل المرحلة 5 في: {out}")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = run_physics_demo()
    print("المدى بالماء (mm):", round(res["water_range_mm"], 2))
    print("Gamma pass_rate  :", round(res["gamma"]["pass_rate"], 3))
    print("المعايير passed  :", res["benchmark"]["all_passed"])
    print("محال للمراجعة    :", res["physics_review"]["stats"]["total_flagged"])
