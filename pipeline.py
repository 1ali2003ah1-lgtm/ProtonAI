"""
ProtonAI - Pipeline Orchestrator
منسق الخط الاحترافي: يربط جميع الوحدات في تدفق عمل واحد متكامل
"""

import logging
import json
import random
from pathlib import Path
from typing import Dict, Any, List

from ingestion import DataIngestion
from split import DataSplitter
from baseline_model import BaselineModel
from reporters import ReportGenerator
from lineage import DataLineage

logger = logging.getLogger("ProtonAI.Pipeline")


def generate_synthetic_data(num_samples: int = 100) -> List[Dict[str, Any]]:
    """
    توليد بيانات تجريبية ذكية ومتوافقة 100% مع قواعد التحقق.
    """
    random.seed(42)
    
    data = []
    for i in range(num_samples):
        # اختيار نوع الورم أولاً
        tumor_type = random.choice(["lung", "brain", "prostate", "breast"])
        
        # تحديد العمر بشكل متوافق مع قواعد التحقق
        # (سرطان البروستاتا نادر تحت 40 سنة حسب validators.py)
        if tumor_type == "prostate":
            age = random.randint(45, 80)
        else:
            age = random.randint(20, 80)
        
        tumor_volume = random.randint(50, 300)
        # علاقة واقعية: الجرعة ترتبط بالعمر وحجم الورم
        dose_gy = 60.0 + (age * 0.1) + (tumor_volume * 0.01) + random.uniform(-2, 2)
        
        data.append({
            "patient_id": f"SYN_{i:04d}",
            "age": age,
            "gender": random.choice(["M", "F"]),
            "tumor_volume": tumor_volume,
            "dose_gy": round(dose_gy, 2),
            "tumor_type": tumor_type
        })
    
    return data


def run_proton_ai_pipeline(output_dir: str | Path = "pipeline_output") -> Dict[str, Any]:
    """تشغيل خط المعالجة الكامل لمنصة ProtonAI."""
    logger.info("=" * 50)
    logger.info("بدء تشغيل خط معالجة ProtonAI...")
    logger.info("=" * 50)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    lineage = DataLineage()
    report_gen = ReportGenerator(report_dir=output_path)
    
    try:
        # 1. توليد واستيعاب البيانات
        logger.info("1. استيعاب البيانات...")
        raw_data = generate_synthetic_data(100)
        
        ingestion = DataIngestion(output_path)
        ingestion.validate_and_clean(raw_data)
        valid_data = ingestion.get_valid_data()
        
        if not valid_data:
            raise ValueError("لا توجد بيانات صالحة بعد التحقق!")
        
        logger.info(f"   بيانات صالحة: {len(valid_data)} من {len(raw_data)}")
        
        lineage.record_transformation(
            "ingestion", "raw", "valid",
            metadata={"valid_count": len(valid_data)}
        )
        
        # 2. تقسيم البيانات
        logger.info("2. تقسيم البيانات...")
        splitter = DataSplitter(
            train_ratio=0.7, val_ratio=0.15, test_ratio=0.15,
            random_seed=42
        )
        train_data, val_data, test_data = splitter.split(valid_data)
        
        lineage.record_transformation("splitting", "valid", "train/val/test")
        
        # 3. تدريب النموذج
        logger.info("3. تدريب النموذج...")
        model = BaselineModel(learning_rate=0.001, epochs=100, random_seed=42)
        training_result = model.fit(
            train_data=train_data,
            feature_keys=["age", "tumor_volume"],
            target_key="dose_gy"
        )
        
        lineage.record_transformation(
            "training", "train", "model",
            metadata=training_result
        )
        
        # 4. التقييم
        logger.info("4. تقييم النموذج...")
        evaluation_metrics = model.evaluate(
            test_data=test_data,
            feature_keys=["age", "tumor_volume"],
            target_key="dose_gy"
        )
        
        # 5. حفظ النموذج
        model.save_model(output_path / "baseline_model.json")
        
        # 6. التقرير النهائي
        logger.info("5. إصدار التقرير النهائي...")
        final_report = report_gen.generate_comprehensive_report(
            ingestion_stats=ingestion.get_report(),
            split_summary=splitter.get_split_summary((train_data, val_data, test_data)),
            lineage_summary=lineage.get_summary()
        )
        final_report["model_metrics"] = evaluation_metrics
        
        report_gen.save_report(final_report, "final_pipeline_report.json")
        
        logger.info("اكتمل خط المعالجة بنجاح!")
        return {"status": "success", "report": final_report}
        
    except Exception as e:
        logger.error(f"فشل خط المعالجة: {e}")
        return {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_proton_ai_pipeline()
    print(json.dumps(result, indent=2, ensure_ascii=False))
