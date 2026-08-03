"""
ProtonAI - Grand Demo (نقطة الدخول الشاملة)
استدعاء واحد يشغّل المنصة من أولها لآخرها ويطلّع dossier نهائي:
سريري ← بحثي ← تحسين ← مؤسسي ← تكرار ← إصدار ← تقرير علمي
عرض تكامل خفيف (لا يعيد تدريب نماذج)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from plan_orchestrator import PlanOrchestrator
from retrospective_validation import RetrospectiveValidator
from external_test_sets import ExternalTestEvaluator
from improvement_loop import ImprovementLoop
from run_enterprise_demo import run_enterprise_demo
from reproducibility_package import ReproducibilityPackage
from release_versioning import ReleaseManager, DEFAULT_CHECKLIST
from scientific_reporting import ScientificReporting

logger = logging.getLogger("ProtonAI.GrandDemo")

_GOOD_PHYS = {"gamma_pass_rate": 0.97, "range_in_target": True,
              "coverage_drop": 0.02, "benchmark_passed": True}


def _providers() -> Dict[str, Callable]:
    return {
        "imaging": lambda p: {"modality": "CT", "slices": 120},
        "physics": lambda p: dict(_GOOD_PHYS),
        "ai": lambda p: {"predicted": "M", "confidence": 0.91},
        "reviews": lambda p: {"signed": True},
    }


def _lists(n, n_correct):
    y_true = ["A"] * n
    return y_true, ["A"] * n_correct + ["B"] * (n - n_correct)


# بيانات بحثية اصطناعية خفيفة للعرض
_RETRO = [
    {"predicted": "M", "actual": "M", "confidence": 0.9},
    {"predicted": "M", "actual": "M", "confidence": 0.85},
    {"predicted": "M", "actual": "M", "confidence": 0.8},
    {"predicted": "B", "actual": "B", "confidence": 0.8},
    {"predicted": "M", "actual": "B", "confidence": 0.4},
]


def run_grand_demo(output_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    """تشغيل المنصة كاملة وإرجاع dossier نهائي شامل"""
    # 1) سريري
    clin = PlanOrchestrator().run(
        providers=_providers(), physician_signed=True, physics_signed=True,
        specialist_decision="approve", specialist_id="dr_grand")

    # 2) بحثي
    retro = RetrospectiveValidator("M", "B").validate(_RETRO)
    it, ip = _lists(50, 45)
    et, ep = _lists(50, 44)
    ext = ExternalTestEvaluator().evaluate(it, ip, et, ep)

    # 3) تحسين
    loop = ImprovementLoop()
    issues = loop.diagnose(retro, ext)
    version_iter = loop.record_iteration(issues)

    # 4) مؤسسي
    ent = run_enterprise_demo()

    # 5) تكرار
    pkg = ReproducibilityPackage(seeds=[42])
    pkg.record_versions()

    # 6) إصدار (checklist كامل خضر)
    rm = ReleaseManager("1.0.0")
    rm.add_change("إطلاق المنصة المتكاملة (8 مراحل + قمة تصوير)", "feature")
    for item in DEFAULT_CHECKLIST:
        rm.set_check(item, True)
    rel = rm.release()

    # 7) تقرير علمي نهائي يجمع الكل
    sr = ScientificReporting()
    sr.add_stage("سريري", {"state": clin["state"],
                           "overall": clin["evaluation"]["overall"].name})
    sr.add_stage("بحثي", {"retro_accuracy": retro["accuracy"],
                          "external_accuracy": ext["external_accuracy"],
                          "generalization_gap": ext["generalization_gap"],
                          "publication_ready": ext["publication_ready"]})
    sr.add_stage("مؤسسي", {"denied_access": ent["denied_count"],
                           "gate_status": ent["gate"]["status"]})
    report_md = sr.to_markdown()

    result = {
        "clinical": {"state": clin["state"],
                     "overall": clin["evaluation"]["overall"].name},
        "research": {"retro_accuracy": retro["accuracy"],
                     "external_accuracy": ext["external_accuracy"],
                     "generalization_gap": ext["generalization_gap"],
                     "publication_ready": ext["publication_ready"]},
        "improvement": {"issues": len(issues), "iteration": version_iter},
        "enterprise": {"denied": ent["denied_count"],
                       "gate": ent["gate"]["status"]},
        "reproducibility": {"seeds": pkg.seeds,
                            "python": pkg.versions.get("python")},
        "release": {"version": rel["version"],
                    "ready_to_launch": rel["ready_to_launch"]},
        "report_markdown": report_md,
    }

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "grand_report.md").write_text(report_md, encoding="utf-8")
        pkg.save(out / "reproducibility.json")
        logger.info(f"حُفظ الـ dossier في: {out}")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    r = run_grand_demo()
    print("سريري:", r["clinical"])
    print("بحثي:", r["research"])
    print("مؤسسي:", r["enterprise"])
    print("إصدار:", r["release"])
