"""
ProtonAI - Strict Validation
طبقة تحقق صارمة فوق التحقق الأساسي
تفرّق بين الأخطاء القاتلة والتحذيرات، وتكشف القيم الشاذة إحصائياً
"""

import math
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("ProtonAI.StrictValidation")


class Severity(str, Enum):
    """خطورة المشكلة: خطأ قاتل أم تحذير"""
    ERROR = "error"      # مستحيل فيزيائياً/منطقياً → رفض حتمي
    WARNING = "warning"  # شاذ إحصائياً لكن ممكن → تنبيه


@dataclass
class ValidationIssue:
    """مشكلة واحدة مكتشفة بالتحقق"""
    field: str
    message: str
    severity: Severity
    value: Any = None


@dataclass
class StrictValidationReport:
    """تقرير تحقق مفصّل (مو مجرد صح/غلط)"""
    issues: List[ValidationIssue] = field(default_factory=list)
    mode: str = "strict"  # strict: أي مشكلة ترفض | lenient: الأخطاء فقط ترفض

    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def is_valid(self) -> bool:
        if self.mode == "strict":
            return len(self.issues) == 0
        return len(self.errors()) == 0

    def summary(self) -> Dict[str, Any]:
        return {
            "valid": self.is_valid,
            "mode": self.mode,
            "errors": len(self.errors()),
            "warnings": len(self.warnings()),
        }


# الحدود المطلقة (hard limits): مستحيل فيزيائياً/بيولوجياً تتجاوزها
DEFAULT_REQUIRED: List[str] = ["patient_id", "age", "gender", "tumor_type"]
DEFAULT_TYPES: Dict[str, type] = {
    "patient_id": str, "age": int, "gender": str, "tumor_type": str,
}
DEFAULT_HARD_RANGES: Dict[str, Tuple[float, float]] = {
    "age": (0, 130),            # الحد البشري المطلق
    "dose_gy": (0.0, 150.0),    # الحد الفيزيائي المطلق للبروتون
    "fractions": (1, 60),       # حد منطقي لعدد الجلسات
}


def _percentile(sorted_vals: List[float], p: float) -> float:
    """حساب المئين بدون مكتبات خارجية"""
    n = len(sorted_vals)
    if n == 0:
        raise ValueError("لا يمكن حساب المئين لقائمة فارغة")
    if n == 1:
        return sorted_vals[0]
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def detect_outliers_iqr(values: List[Any], factor: float = 1.5) -> List[float]:
    """كشف القيم الشاذة بطريقة IQR (يرجع القيم الشاذة فقط)"""
    nums = [float(v) for v in values
            if isinstance(v, (int, float)) and v is not None]
    if len(nums) < 4:  # ما نكشف شذوذ بمجموعة صغيرة جداً
        return []
    s = sorted(nums)
    q1 = _percentile(s, 0.25)
    q3 = _percentile(s, 0.75)
    iqr = q3 - q1
    lo = q1 - factor * iqr
    hi = q3 + factor * iqr
    return [v for v in nums if v < lo or v > hi]


class StrictValidator:
    """
    المتحقق الصارم.
    - validate_record: يفحص سجل واحد (اكتمال + أنواع + حدود مطلقة).
    - validate_batch_outliers: يفحص شذوذ القيم الرقمية عبر مجموعة.
    """

    def __init__(
        self,
        required: Optional[List[str]] = None,
        types: Optional[Dict[str, type]] = None,
        hard_ranges: Optional[Dict[str, Tuple[float, float]]] = None,
    ):
        self.required = list(required) if required else list(DEFAULT_REQUIRED)
        self.types = dict(types) if types else dict(DEFAULT_TYPES)
        self.hard_ranges = dict(hard_ranges) if hard_ranges else dict(DEFAULT_HARD_RANGES)

    def validate_record(
        self, record: Dict[str, Any], mode: str = "strict"
    ) -> StrictValidationReport:
        """التحقق الصارم من سجل واحد"""
        report = StrictValidationReport(mode=mode)

        # 1) اكتمال الحقول الإلزامية
        for f in self.required:
            if f not in record or record[f] is None or str(record[f]).strip() == "":
                report.issues.append(ValidationIssue(
                    field=f, message=f"الحقل الإلزامي مفقود: {f}",
                    severity=Severity.ERROR, value=record.get(f),
                ))

        # 2) صحة الأنواع
        for f, expected in self.types.items():
            if f in record and record[f] is not None and record[f] != "":
                # العمر قد يأتي كنص رقمي من CSV، نتسامح معه بالتحويل
                if expected is int and isinstance(record[f], str):
                    try:
                        int(float(record[f]))
                        continue
                    except (ValueError, TypeError):
                        pass
                if not isinstance(record[f], expected):
                    report.issues.append(ValidationIssue(
                        field=f, message=f"نوع خاطئ لـ {f}: المتوقع {expected.__name__}",
                        severity=Severity.ERROR, value=record[f],
                    ))

        # 3) الحدود المطلقة (hard limits)
        for f, (lo, hi) in self.hard_ranges.items():
            if f in record and record[f] is not None and record[f] != "":
                try:
                    val = float(record[f])
                except (ValueError, TypeError):
                    continue
                if val < lo or val > hi:
                    report.issues.append(ValidationIssue(
                        field=f, message=f"القيمة خارج الحد المطلق [{lo}, {hi}] لـ {f}",
                        severity=Severity.ERROR, value=val,
                    ))

        return report

    def validate_batch_outliers(
        self, records: List[Dict[str, Any]], numeric_keys: List[str],
        mode: str = "strict", factor: float = 1.5,
    ) -> StrictValidationReport:
        """كشف القيم الشاذة إحصائياً عبر مجموعة (تحذيرات)"""
        report = StrictValidationReport(mode=mode)
        for key in numeric_keys:
            values = [r.get(key) for r in records]
            outliers = detect_outliers_iqr(values, factor)
            for ov in outliers:
                report.issues.append(ValidationIssue(
                    field=key, message=f"قيمة شاذة إحصائياً لـ {key}",
                    severity=Severity.WARNING, value=ov,
                ))
        return report
