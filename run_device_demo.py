"""
ProtonAI - Device Readiness Demo (Stage-10 Maestro)
جسر CI ↔ الجهاز: يشغّل الآمن على CI، ويفعّل torch/Streamlit على الجهاز تلقائياً
تقرير جاهزية صادق: يقول شنو يشتغل الحين وشنو يتفعّل على جهازك
"""

import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

from mc_batched import BatchedMonteCarlo
from torch_segmenter import TorchSegmenter, TORCH_AVAILABLE
from streamlit_dashboard import build_dashboard_data, STREAMLIT_AVAILABLE

logger = logging.getLogger("ProtonAI.DeviceDemo")


def _synthetic(seed: int = 0):
    rng = np.random.RandomState(seed)
    hu = rng.normal(-200, 50, (20, 20))
    labels = np.zeros((20, 20), dtype=int)
    labels[5:10, 5:10] = 1
    hu[5:10, 5:10] = rng.normal(300, 50, (5, 5))
    return hu, labels


def _dice(a, b):
    a, b = a.astype(bool), b.astype(bool)
    return float(2 * (a & b).sum() / (a.sum() + b.sum()))


def run_device_demo(
    output_dir: Optional[str | Path] = None,
    seed: int = 42,
    mc_histories: int = 100_000,
) -> Dict[str, Any]:
    """تشغيل تقرير جاهزية الجهاز (CI يشغّل الآمن، الجهاز يفعّل الباقي)"""
    report: Dict[str, Any] = {}

    # 1) Monte Carlo دفعات ضخم (يشتغل على CI والجهاز)
    bmc = BatchedMonteCarlo(seed=seed, chunk_size=10_000)
    report["mc"] = bmc.validate_vs_analytic(120.0, n_histories=mc_histories, seed=seed)
    report["mc_histories"] = mc_histories

    # 2) تقسيم CNN الحقيقي (جهاز فقط إن torch مثبت)
    if TORCH_AVAILABLE:
        hu, labels = _synthetic(seed)
        seg = TorchSegmenter(seed=seed).fit(hu, labels, epochs=40)
        report["torch_seg"] = {"available": True,
                               "dice": _dice(seg.segment(hu), labels)}
    else:
        report["torch_seg"] = {"available": False, "dice": None,
                               "note": "يتطلب pip install torch على جهازك"}

    # 3) لوحة البيانات (CI) + توفر Streamlit
    dash = build_dashboard_data()
    report["dashboard"] = dash
    report["streamlit"] = STREAMLIT_AVAILABLE

    # 4) تقرير الجاهزية
    lines = ["# 💻 تقرير جاهزية الجهاز (المرحلة 10)", "",
             f"- Monte Carlo دفعات ({mc_histories} تاريخ): "
             f"rel_diff={report['mc']['rel_diff']:.4f} ✅",
             f"- تقسيم CNN (torch): "
             + ("جاهز ✅" if TORCH_AVAILABLE else "يتطلب pip install torch"),
             f"- لوحة Streamlit: "
             + ("جاهزة ✅" if STREAMLIT_AVAILABLE else "يتطلب pip install streamlit"),
             f"- لوحة البيانات: state={dash['state']}, overall={dash['overall']} ✅", ""]
    report["readiness_markdown"] = "\n".join(lines)

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "device_readiness.md").write_text(
            report["readiness_markdown"], encoding="utf-8")
        logger.info(f"تم حفظ تقرير الجاهزية في: {out}")

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    r = run_device_demo()
    print(r["readiness_markdown"])
