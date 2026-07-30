"""
ProtonAI - UCI Training Runner
تشغيل خط المعالجة على بيانات UCI Breast Cancer المعتمدة
أول تدريب حقيقي للمنصة على بيانات طبية معتمدة عالمياً
"""

import json
import sys
import logging
from pathlib import Path

from data_pipeline import DataPipeline, PipelineConfig
from dataset_contracts import UCI_CANCER

logger = logging.getLogger("ProtonAI.UCIRunner")

# الأعمدة المستخدمة للتدريب (من عقد UCI المعتمد)
UCI_FEATURES = ["radius_mean", "texture_mean", "perimeter_mean", "area_mean", "smoothness_mean"]
UCI_TARGET = "diagnosis"


def run_uci(csv_path, output_dir="uci_output", train_ratio=0.8):
    """تشغيل الخط الكامل على ملف UCI، يرجع التقرير ويحفظ النموذج"""
    cfg = PipelineConfig(
        feature_columns=UCI_FEATURES,
        target_column=UCI_TARGET,
        task="classification",
        acceptance_threshold=0.95,
        train_ratio=train_ratio,
        random_seed=42,
    )
    pipe = DataPipeline(cfg, contract=UCI_CANCER)
    report = pipe.run(csv_path)

    # حفظ التقرير
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "uci_report.json", "w", encoding="utf-8") as f:
        json.dump(report.summary(), f, indent=2, ensure_ascii=False, default=str)

    # حفظ النموذج إذا نجح الخط
    if report.succeeded:
        pipe.model.save(out / "uci_model.pkl")
        logger.info("تم حفظ نموذج UCI")

    return report


def _print_report(report):
    """طباعة تقرير مقروء على الشاشة"""
    print("=" * 55)
    print("تقرير تدريب UCI Breast Cancer")
    print("=" * 55)
    print(f"الحالة         : {report.status}")
    print(f"الرسالة        : {report.message}")
    print(f"السجلات المحملة : {report.loaded}")
    print(f"تدريب / اختبار : {report.train_samples} / {report.test_samples}")
    if report.contract:
        print(f"نسبة القبول    : {report.contract['acceptance_rate']}")
    if report.evaluation:
        ev = report.evaluation
        if ev["task"] == "classification":
            print(f"الدقة          : {ev['accuracy'] * 100:.1f}%")
        else:
            print(f"MAE            : {ev['mae']:.3f}")
            print(f"R²             : {ev['r2']:.3f}")
    print("=" * 55)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = sys.argv[1] if len(sys.argv) > 1 else "data/uci_cancer.csv"
    rep = run_uci(path)
    _print_report(rep)
