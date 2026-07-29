"""
ProtonAI - Clinical Data Loader
جسر استقبال بيانات المستشفى الحقيقية
يقرأ ملفات CSV/JSON بأسماء أعمدة مختلفة ويطابقها بذكاء على حقول المنصة
"""

import csv
import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from contracts import PatientData
from validators import validate_patient_record, CrossFieldValidator

logger = logging.getLogger("ProtonAI.ClinicalLoader")


# أسماء الأعمدة الشائعة في المستشفيات لكل حقل (مطابقة ذكية)
DEFAULT_MAPPING: Dict[str, List[str]] = {
    "patient_id": ["patient_id", "id", "patientid", "mrn", "record_id"],
    "age": ["age", "age_years", "ageyears", "patient_age"],
    "gender": ["gender", "sex", "gender_sex", "patient_sex"],
    "tumor_type": ["tumor_type", "tumortype", "tumor", "diagnosis", "site"],
}


def _normalize(name: Any) -> str:
    """توحيد اسم العمود: حروف صغيرة + حذف المسافات والرموز"""
    return re.sub(r"[^a-z0-9]", "", str(name).strip().lower())


def _to_int(value: Any) -> Optional[int]:
    """تحويل آمن للعمر إلى عدد صحيح"""
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


class ClinicalDataLoader:
    """مستقبل بيانات المستشفى الذكي"""

    def __init__(self, mapping: Optional[Dict[str, List[str]]] = None):
        # ندمج mapping المستخدم مع الافتراضي (الأولوية للمستخدم)
        self.mapping: Dict[str, List[str]] = {k: list(v) for k, v in DEFAULT_MAPPING.items()}
        if mapping:
            for key, candidates in mapping.items():
                self.mapping[key] = list(candidates) + self.mapping.get(key, [])
        logger.info("تم تهيئة مستقبل البيانات السريرية")

    def _apply_mapping(self, raw_row: Dict[str, Any]) -> Dict[str, Any]:
        """تحويل صف بأسماء غريبة إلى صف بأسماء المنصة القياسية"""
        # فهرس: الاسم الموحد -> الاسم الأصلي في الملف
        norm_index = {_normalize(k): k for k in raw_row.keys()}

        clean: Dict[str, Any] = {}
        for target, candidates in self.mapping.items():
            value = None
            for candidate in candidates:
                if _normalize(candidate) in norm_index:
                    value = raw_row[norm_index[_normalize(candidate)]]
                    break

            # تنظيف القيمة حسب نوع الحقل
            if target == "age":
                value = _to_int(value)
            elif value is not None:
                value = str(value).strip()
                if target == "tumor_type":
                    value = value.lower()

            clean[target] = value
        return clean

    def load(self, file_path: str | Path) -> List[Dict[str, Any]]:
        """قراءة ملف (CSV أو JSON) وإرجاع صفوف قياسية"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"الملف غير موجود: {path}")

        raw_rows: List[Dict[str, Any]] = []
        if path.suffix.lower() == ".csv":
            with open(path, "r", encoding="utf-8", newline="") as f:
                raw_rows = list(csv.DictReader(f))
        elif path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw_rows = data if isinstance(data, list) else [data]
        else:
            raise ValueError(f"صيغة غير مدعومة: {path.suffix} (استخدم .csv أو .json)")

        clean_rows = [self._apply_mapping(row) for row in raw_rows]
        logger.info(f"تمت قراءة {len(clean_rows)} صف من {path.name}")
        return clean_rows

    def _diagnose(self, record: Dict[str, Any]) -> Optional[str]:
        """إيجاد سبب رفض السجل (للتقرير)"""
        try:
            PatientData(**record)
        except Exception as e:
            return str(e)[:200]
        if not CrossFieldValidator.validate_age_tumor(
            record.get("age"), record.get("tumor_type")
        ):
            return "العمر لا يتناسب مع نوع الورم (مثلاً prostate تحت 40)"
        return None

    def load_and_validate(self, file_path: str | Path) -> Dict[str, Any]:
        """قراءة + تحقق + تقرير مفصّل"""
        rows = self.load(file_path)
        valid, invalid = [], []

        for row in rows:
            if validate_patient_record(row):
                valid.append(row)
            else:
                invalid.append({"record": row, "reason": self._diagnose(row)})

        total = len(rows)
        report = {
            "total": total,
            "valid_count": len(valid),
            "invalid_count": len(invalid),
            "acceptance_rate": f"{(len(valid) / total * 100):.1f}%" if total else "0.0%",
            "valid": valid,
            "invalid": invalid,
        }
        logger.info(f"التحقق: {len(valid)} مقبول / {len(invalid)} مرفوض من {total}")
        return report
