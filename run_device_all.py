"""
ProtonAI - Run All (Device Capstone)
يشغّل كل الديموهات (سريري + مؤسسي + تطور + جاهزية) ويجمعها بتقرير واحد
على CI يشغّل الآمن؛ على الجهاز يفعّل torch/Streamlit تلقائياً
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from run_clinical_demo import run_clinical_demo
from run_enterprise_demo import run_enterprise_demo
from run_evolution_demo import run_evolution_demo
from run_device_demo import run_device_demo

logger = logging.getLogger("ProtonAI.RunAll")


def run_device_all(output_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    """تشغيل كل المنصة وجمع ملخصاتها بتقرير موحد"""
    summaries: Dict[str, Any] = {}

    # 1) سريري (مرحلة 6)
    clin = run_clinical_demo("approve")["result"]
    summaries["clinical"] = {
        "state": clin["state"],
        "overall": clin["evaluation"]["overall"].name,
    }

    # 2) مؤسسي (مرحلة 7)
    ent = run_enterprise_demo()
    summaries["enterprise"] = {
        "denied": ent["denied_count"],
        "gate": ent["gate"]["status"],
        "fhir_acks": list(ent["fhir"]["acks"].keys()),
    }

    # 3) تطور عميق (مرحلة 9)
    evo = run_evolution_demo()
    summaries["evolution"] = {
        "mc_rel_diff": evo["physics_mc"]["rel_diff"],
        "segmentation_dice": evo["segmentation_dice"],
        "fhir_status": evo["fhir"]["status"],
    }

    # 4) جاهزية الجهاز (مرحلة 10)
    dev = run_device_demo()
    summaries["device"] = {
        "torch_available": dev["torch_seg"]["available"],
        "streamlit_available": dev["streamlit"],
        "mc_rel_diff": dev["mc"]["rel_diff"],
    }

    # التقرير الموحد
    lines = ["# 🚀 ProtonAI — تقرير التشغيل الكامل", "",
             f"- سريري: state={summaries['clinical']['state']}, "
             f"overall={summaries['clinical']['overall']}",
             f"- مؤسسي: denied={summaries['enterprise']['denied']}, "
             f"gate={summaries['enterprise']['gate']}",
             f"- تطور: MC rel_diff={summaries['evolution']['mc_rel_diff']:.4f}, "
             f"Dice={summaries['evolution']['segmentation_dice']:.2f}",
             f"- جهاز: torch={summaries['device']['torch_available']}, "
             f"streamlit={summaries['device']['streamlit_available']}", ""]
    markdown = "\n".join(lines)

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "run_all_report.md").write_text(markdown, encoding="utf-8")
        logger.info(f"تم حفظ التقرير الموحد في: {out}")

    return {"summaries": summaries, "markdown": markdown}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_device_all(output_dir="out_device")["markdown"])
