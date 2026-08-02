"""
ProtonAI - Stage-6 Clinical Demo
المايسترو النهائي: مريض وهمي يمرّ بسير العمل الكامل بأربع سيناريوهات
approve / reject / review / compare — كل واحد يطلّع لوحة Markdown + HTML
يبني مزوّدين وهميين واقعيين (بدون بيانات خارجية) ليعمل end-to-end
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from treatment_plan import TreatmentPlan
from plan_orchestrator import PlanOrchestrator
from plan_comparison import PlanComparison
from quality_indicators import QualityIndicators

logger = logging.getLogger("ProtonAI.ClinicalDemo")

VALID_SCENARIOS = ("approve", "reject", "review", "compare")

# بيانات وهمية واقعية (شكلها سريري، قيمها للعرض فقط)
_IMAGING = {"slices": 156, "modality": "CT", "tumor_volume_cc": 12.4,
            "oar_segmented": 3, "hu_range": [-1000, 1200]}
_AI_GOOD = {"predicted": "M", "confidence": 0.91,
            "top_factors": ["radius_mean", "perimeter_mean", "texture_mean"]}
_REVIEWS_SIGNED = {"signed": True, "physician": "dr_ahmed",
                   "physicist": "phys_sara", "consensus": "yes"}
_REVIEWS_UNSIGNED = {"signed": False, "physician": None, "physicist": None}

_PHYS_GOOD = {"gamma_pass_rate": 0.97, "range_in_target": True,
              "coverage_drop": 0.02, "benchmark_passed": True}
_PHYS_BAD = {"gamma_pass_rate": 0.78, "range_in_target": False,
             "coverage_drop": 0.35, "benchmark_passed": False}
_PHYS_AMBER = {"gamma_pass_rate": 0.91, "range_in_target": True,
               "coverage_drop": 0.02, "benchmark_passed": True}


def _providers(physics: Dict[str, Any], reviews: Dict[str, Any],
               ai: Optional[Dict[str, Any]] = None) -> Dict[str, Callable]:
    """مزوّدون وهميون واقعيون (كل fn(plan)->dict)"""
    return {
        "imaging": lambda p: dict(_IMAGING),
        "physics": lambda p: dict(physics),
        "ai": lambda p: dict(ai if ai is not None else _AI_GOOD),
        "reviews": lambda p: dict(reviews),
    }


def _save(result: Dict[str, Any], out: Path, tag: str) -> None:
    """حفظ لوحة سيناريو واحد (md + html + json)"""
    out.mkdir(parents=True, exist_ok=True)
    md = out / f"clinical_{tag}.md"
    html = out / f"clinical_{tag}.html"
    js = out / f"clinical_{tag}.json"
    with open(md, "w", encoding="utf-8") as f:
        f.write(result["report_markdown"])
    with open(html, "w", encoding="utf-8") as f:
        f.write(result["report_html"])
    with open(js, "w", encoding="utf-8") as f:
        json.dump(result["dashboard"], f, indent=2, ensure_ascii=False)
    logger.info(f"تم حفظ سيناريو {tag} في: {out}")


def run_clinical_demo(
    scenario: str = "approve",
    output_dir: Optional[str | Path] = None,
    orchestrator: Optional[PlanOrchestrator] = None,
    patient_id: str = "DEMO_ANON_001",
) -> Dict[str, Any]:
    """
    تشغيل سيناريو سريري كامل على مريض وهمي، يرجع قاموساً شاملاً.
    approve/reject/review: خطة وحدة. compare: خطتان + اختيار الأأمن.
    """
    if scenario not in VALID_SCENARIOS:
        raise ValueError(f"سيناريو غير معروف: {scenario}. المسموح: {VALID_SCENARIOS}")
    orch = orchestrator if orchestrator is not None else PlanOrchestrator()

    if scenario == "approve":
        result = orch.run(
            providers=_providers(_PHYS_GOOD, _REVIEWS_SIGNED),
            patient_id=patient_id, physician_signed=True, physics_signed=True,
            specialist_decision="approve", specialist_id="dr_demo",
            specialist_notes="سيناريو اعتماد نظيف")
        out = {"scenario": scenario, "result": result}

    elif scenario == "reject":
        result = orch.run(
            providers=_providers(_PHYS_BAD, _REVIEWS_UNSIGNED),
            patient_id=patient_id, physician_signed=False, physics_signed=False,
            specialist_decision="reject", specialist_id="dr_demo",
            specialist_notes="مؤشرات خطرة — مرفوض")
        out = {"scenario": scenario, "result": result}

    elif scenario == "review":
        # تحذيري + موقّع، بلا قرار متخصص → جاهزة بس التوصية review (ما تسلّم لحالها)
        result = orch.run(
            providers=_providers(_PHYS_AMBER, _REVIEWS_SIGNED),
            patient_id=patient_id, physician_signed=True, physics_signed=True)
        out = {"scenario": scenario, "result": result}

    else:  # compare
        # بناء خطتين بدون حركة (للمقارنة العادلة)، ثم تشغيل الكاملة على الأأمن
        res_good = orch.run(providers=_providers(_PHYS_GOOD, _REVIEWS_SIGNED),
                            patient_id=patient_id, auto_advance=False)
        res_bad = orch.run(providers=_providers(_PHYS_BAD, _REVIEWS_UNSIGNED),
                           patient_id=patient_id, auto_advance=False)
        comp = PlanComparison(orch.quality).compare(
            {"good": res_good["plan"], "bad": res_bad["plan"]})
        chosen = comp["recommended"] or "good"
        chosen_prov = (_providers(_PHYS_GOOD, _REVIEWS_SIGNED) if chosen == "good"
                       else _providers(_PHYS_BAD, _REVIEWS_UNSIGNED))
        result = orch.run(
            plan=res_good["plan"] if chosen == "good" else res_bad["plan"],
            providers=chosen_prov, patient_id=patient_id,
            physician_signed=True, physics_signed=True,
            specialist_decision="approve", specialist_id="dr_demo",
            comparison=comp)
        out = {"scenario": scenario, "result": result, "comparison": comp,
               "chosen": chosen,
               "good_overall": res_good["evaluation"]["overall"].name,
               "bad_overall": res_bad["evaluation"]["overall"].name}

    if output_dir:
        _save(result, Path(output_dir), scenario)

    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for sc in ("approve", "reject", "review"):
        r = run_clinical_demo(sc)
        res = r["result"]
        print(f"[{sc}] state={res['state']}, rec={res['decision'].recommendation.value}, "
              f"overall={res['evaluation']['overall'].name}")
    c = run_clinical_demo("compare")
    print(f"[compare] chosen={c['chosen']}, recommended={c['comparison']['recommended']}, "
          f"final_state={c['result']['state']}")
