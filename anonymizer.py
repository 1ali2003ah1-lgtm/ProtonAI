"""
ProtonAI - Anonymizer
إخفاء هوية المريض بأسلوب HIPAA Safe Harbor
تجزئة قابلة للتكرار + حذف الحقول الحساسة + تعميم العمر
"""

import hashlib
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("ProtonAI.Anonymizer")

# حقول تُحذف تماماً إن وُجدت (معرفات مباشرة)
DEFAULT_SENSITIVE_FIELDS: List[str] = [
    "name", "first_name", "last_name", "full_name",
    "dob", "date_of_birth", "birth_date",
    "address", "city", "zip", "postcode",
    "phone", "telephone", "mobile",
    "email", "ssn", "national_id", "mrn_original",
]


@dataclass
class AnonymizationLog:
    """سجل إخفاء الهوية لسجل واحد"""
    ids_hashed: int = 0
    ages_generalized: int = 0
    fields_removed: Dict[str, int] = field(default_factory=dict)


@dataclass
class BatchReport:
    """تقرير إخفاء الهوية لمجموعة"""
    records: int = 0
    ids_hashed: int = 0
    ages_generalized: int = 0
    fields_removed: Dict[str, int] = field(default_factory=dict)

    def summary(self) -> Dict[str, Any]:
        return {
            "records": self.records,
            "ids_hashed": self.ids_hashed,
            "ages_generalized": self.ages_generalized,
            "fields_removed": dict(self.fields_removed),
        }


class Anonymizer:
    """
    مُخفي الهوية.
    - hash_id: تجزئة SHA-256 مع ملح (salt) → معرف ANON_ قابل للتكرار.
    - generalize_age: تعميم العمر (bucket نطاقات | cap حد أعلى).
    - anonymize_record / anonymize_batch: الإخفاء مع تقرير تدقيق.
    """

    def __init__(
        self,
        salt: str = "ProtonAI-default-salt-change-me",
        age_strategy: str = "bucket",
        sensitive_fields: Optional[List[str]] = None,
    ):
        if age_strategy not in ("bucket", "cap"):
            raise ValueError("age_strategy يجب أن يكون bucket أو cap")
        self.salt = salt
        self.age_strategy = age_strategy
        self.sensitive_fields = list(sensitive_fields) if sensitive_fields \
            else list(DEFAULT_SENSITIVE_FIELDS)

    def hash_id(self, value: Any) -> str:
        """تجزئة قابلة للتكرار: نفس القيمة + نفس الملح = نفس المعرّف دايماً"""
        raw = (self.salt + ":" + str(value)).encode("utf-8")
        return "ANON_" + hashlib.sha256(raw).hexdigest()[:12]

    def generalize_age(self, age: int, strategy: Optional[str] = None) -> Any:
        """تعميم العمر لحماية كبار السن (HIPAA: >89 يُعمّم)"""
        strategy = strategy or self.age_strategy
        if strategy == "cap":
            return 90 if age > 89 else age
        # bucket: نطاقات عشرية
        if age > 89:
            return "90+"
        bucket = (age // 10) * 10
        return f"{bucket}-{bucket + 9}"

    def anonymize_record(
        self, record: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], AnonymizationLog]:
        """إخفاء سجل واحد (يرجع نسخة، الأصل لا يتأثر)"""
        anon = dict(record)  # نسخة سطحية → الأصل سالم
        log = AnonymizationLog()

        # 1) تجزئة المعرّف
        if anon.get("patient_id") not in (None, ""):
            anon["patient_id"] = self.hash_id(anon["patient_id"])
            log.ids_hashed += 1

        # 2) حذف الحقول الحساسة
        for f in self.sensitive_fields:
            if f in anon:
                anon.pop(f)
                log.fields_removed[f] = log.fields_removed.get(f, 0) + 1

        # 3) تعميم العمر
        if anon.get("age") not in (None, ""):
            try:
                anon["age"] = self.generalize_age(int(float(anon["age"])))
                log.ages_generalized += 1
            except (ValueError, TypeError):
                pass

        return anon, log

    def anonymize_batch(
        self, records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], BatchReport]:
        """إخفاء مجموعة مع تقرير تدقيق شامل"""
        out: List[Dict[str, Any]] = []
        report = BatchReport(records=len(records))
        for r in records:
            anon, log = self.anonymize_record(r)
            out.append(anon)
            report.ids_hashed += log.ids_hashed
            report.ages_generalized += log.ages_generalized
            for k, v in log.fields_removed.items():
                report.fields_removed[k] = report.fields_removed.get(k, 0) + v
        logger.info(f"تم إخفاء {report.records} سجل (معرفات={report.ids_hashed})")
        return out, report
