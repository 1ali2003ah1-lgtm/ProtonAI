"""
ProtonAI - Data Ingestion Module
وحدة استيعاب ومعالجة البيانات الطبية بشكل احترافي وآمن
"""

import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

from contracts import PatientData
from validators import validate_patient_record

# إعداد نظام التسجيل (Logging) لمتابعة عمليات الاستيعاب
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ProtonAI.Ingestion")


class DataIngestion:
    """فئة مسؤولة عن استيعاب، تنظيف، والتحقق من البيانات الطبية"""

    def __init__(self, data_dir: str | Path):
        """
        تهيئة وحدة الاستيعاب.
        
        Args:
            data_dir: المسار إلى المجلد الذي يحتوي على ملفات البيانات
        """
        self.data_dir = Path(data_dir)
        self.valid_records: List[Dict[str, Any]] = []
        self.invalid_records: List[Dict[str, Any]] = []
        self.ingestion_stats = {
            "total_processed": 0,
            "valid_count": 0,
            "invalid_count": 0
        }

    def load_json(self, file_name: str) -> List[Dict[str, Any]]:
        """تحميل البيانات من ملف JSON"""
        file_path = self.data_dir / file_name
        if not file_path.exists():
            logger.error(f"ملف غير موجود: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"تم تحميل {len(data)} سجل من {file_name}")
                return data if isinstance(data, list) else [data]
        except json.JSONDecodeError as e:
            logger.error(f"خطأ في قراءة ملف JSON {file_name}: {e}")
            raise

    def load_csv(self, file_name: str) -> List[Dict[str, Any]]:
        """تحميل البيانات من ملف CSV"""
        file_path = self.data_dir / file_name
        if not file_path.exists():
            logger.error(f"ملف غير موجود: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
                logger.info(f"تم تحميل {len(data)} سجل من {file_name}")
                return data
        except Exception as e:
            logger.error(f"خطأ في قراءة ملف CSV {file_name}: {e}")
            raise

    def validate_and_clean(self, raw_data: List[Dict[str, Any]]) -> None:
        """
        التحقق من صحة البيانات وتنظيفها.
        يفصل السجلات الصحيحة عن الفاسدة لضمان عدم تلوث بيانات التدريب.
        """
        logger.info("بدء عملية التحقق من صحة البيانات...")
        
        for record in raw_data:
            self.ingestion_stats["total_processed"] += 1
            
            # محاولة تحويل أنواع البيانات الأساسية (مثل العمر من نص إلى رقم)
            try:
                if "age" in record:
                    record["age"] = int(record["age"])
                if "total_dose_gy" in record:
                    record["total_dose_gy"] = float(record["total_dose_gy"])
                if "fractions" in record:
                    record["fractions"] = int(record["fractions"])
            except (ValueError, TypeError):
                logger.warning(f"فشل تحويل أنواع البيانات للسجل: {record.get('patient_id', 'Unknown')}")
                self.invalid_records.append(record)
                self.ingestion_stats["invalid_count"] += 1
                continue

            # التحقق من صحة السجل باستخدام validators.py
            if validate_patient_record(record):
                self.valid_records.append(record)
                self.ingestion_stats["valid_count"] += 1
            else:
                self.invalid_records.append(record)
                self.ingestion_stats["invalid_count"] += 1
                logger.warning(f"سجل مرفوض بسبب فشل التحقق: {record.get('patient_id', 'Unknown')}")

        logger.info(f"انتهت المعالجة. صحيح: {self.ingestion_stats['valid_count']}, مرفوض: {self.ingestion_stats['invalid_count']}")

    def get_valid_data(self) -> List[Dict[str, Any]]:
        """إرجاع البيانات الصحيحة والجاهزة للنمذجة"""
        return self.valid_records

    def save_invalid_records(self, output_file: str = "invalid_records.json") -> None:
        """حفظ السجلات المرفوضة في ملف منفصل للمراجعة اليدوية"""
        output_path = self.data_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.invalid_records, f, indent=2, ensure_ascii=False)
        logger.info(f"تم حفظ {len(self.invalid_records)} سجل مرفوض في {output_path}")

    def get_report(self) -> Dict[str, Any]:
        """إرجاع تقرير شامل عن عملية الاستيعاب"""
        total = self.ingestion_stats["total_processed"]
        valid = self.ingestion_stats["valid_count"]
        pass_rate = (valid / total * 100) if total > 0 else 0.0
        
        return {
            "total_processed": total,
            "valid_count": valid,
            "invalid_count": self.ingestion_stats["invalid_count"],
            "validation_pass_rate": f"{pass_rate:.2f}%"
      }
