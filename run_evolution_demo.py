"""
ProtonAI - Stage-9 Evolution Demo
مايسترو التطور العميق: Monte Carlo + عدم يقين مدموج + تقسيم متعلّم + FHIR حي
بتقرير علمي موحد قابل للتكرار (seed موحّد)
"""

import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

from monte_carlo_physics import MonteCarloPhysics
from mc_uncertainty import MCUncertainty
from learned_segmentation import LearnedSegmenter
from fhir_http_client import FHIRClient, start_mock_server, _MockFHIRHandler
from integration_adapters import FHIRMapper
from treatment_plan import TreatmentPlan
from scientific_reporting import ScientificReporting

logger = logging.getLogger("ProtonAI.EvolutionDemo")


def _synthetic(seed: int = 0):
    """صورة HU معنونة: خلفية + ورم [5:10,5:10] (فهرسة شرائح)"""
    rng = np.random.RandomState(seed)
    hu = rng.normal(-200, 50, (20, 20))
    labels = np.zeros((20, 20), dtype=int)
    labels[5:10, 5:10] = 1
    hu[5:10, 5:10] = rng.normal(300, 50, (5, 5))
    return hu, labels


def _dice(a, b):
    a, b = a.astype(bool), b.astype(bool)
    return float(2 * (a & b).sum() / (a.sum() + b.sum()))


def _plan() -> TreatmentPlan:
    p = TreatmentPlan("plan_evo", "anon_evo")
    p.set_section("imaging", {"modality": "CT", "slices": 120})
    p.set_section("physics", {"gamma_pass_rate": 0.97, "coverage_drop": 0.02})
    return p


def run_evolution_demo(
    output_dir: Optional[str | Path] = None,
    energy_mev: float = 120.0,
    seed: int = 42,
) -> Dict[str, Any]:
    """تشغيل كل تطورات المرحلة 9، يرجع قاموساً شاملاً + يحفظ إن طُلب"""
    # 1) فيزياء Monte Carlo تتحقق من التحليلي
    mc = MonteCarloPhysics(seed=seed)
    val = mc.validate_vs_analytic(energy_mev, n_histories=2000, seed=seed)

    # 2) عدم يقين مدموج + اختيار N تاريخ
    u = MCUncertainty(mc=mc)
    n_target = MCUncertainty.n_histories_for_target(0.01)
    band = u.range_band(energy_mev, n_target)

    # 3) تقسيم متعلّم
    hu, labels = _synthetic(seed)
    seg = LearnedSegmenter(seed=seed).fit(hu, labels)
    dice = _dice(seg.segment(hu), labels)

    # 4) تكامل FHIR حي (خادم وهمي محلي، يُغلق بـ finally)
    _MockFHIRHandler.store = {}
    server, url = start_mock_server()
    try:
        client = FHIRClient(url)
        status, ack = client.post_bundle(FHIRMapper().plan_to_bundle(_plan()))
        reachable = client.is_reachable()
    finally:
        server.shutdown()
        server.server_close()

    # 5) تقرير علمي موحد
    sr = ScientificReporting(title="ProtonAI — تقرير التطور العميق (المرحلة 9)")
    sr.add_stage("فيزياء Monte Carlo", {
        "mc_range": val["mc_range"], "analytic_range": val["analytic_range"],
        "rel_diff": val["rel_diff"]})
    sr.add_stage("عدم اليقين المدموج", {
        "clinical": band["components"]["clinical"],
        "mc_statistical": band["components"]["mc_statistical"],
        "combined": band["components"]["combined"],
        "n_histories_target": n_target})
    sr.add_stage("التقسيم المتعلّم", {"dice": dice})
    sr.add_stage("التكامل الحي", {"fhir_post_status": status,
                                   "reachable": reachable})
    markdown = sr.to_markdown()

    result = {
        "physics_mc": val,
        "uncertainty": band,
        "n_histories_target": n_target,
        "segmentation_dice": dice,
        "fhir": {"status": status, "reachable": reachable},
        "report_markdown": markdown,
    }

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "evolution_report.md").write_text(markdown, encoding="utf-8")
        logger.info(f"تم حفظ تقرير التطور في: {out}")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    r = run_evolution_demo()
    print("MC rel_diff :", round(r["physics_mc"]["rel_diff"], 4))
    print("Seg Dice    :", round(r["segmentation_dice"], 3))
    print("FHIR status :", r["fhir"]["status"], "| reachable:", r["fhir"]["reachable"])
