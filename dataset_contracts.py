"""
ProtonAI - Dataset Contracts
عقود بيانات لمجموعات البيانات المعتمدة
تضمن الأعمدة والأنواع والنطاقات قبل أي معالجة أو تدريب
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ProtonAI.DatasetContracts")


@dataclass
class ColumnSpec:
    """مواصفات عمود واحد بالعقد"""
    name: str
    dtype: str = "float"  # float | int | str
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None

    def __post_init__(self):
        if self.dtype not in ("float", "int", "str"):
            raise ValueError(f"dtype غير صالح: {self.dtype}")


@dataclass
class ContractIssue:
    """مشكلة واحدة مكتشفة بالعقد"""
    column: str
    message: str
    value: Any = None


@dataclass
class ContractReport:
    """تقرير تحقق العقد لمجموعة بيانات"""
    total: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    invalid_details: List[Dict[str, Any]] = field(default_factory=list)
    acceptance_threshold: float = 0.95

    @property
    def acceptance_rate(self) -> float:
        return (self.valid_count / self.total * 100.0) if self.total else 0.0

    @property
    def is_acceptable(self) -> bool:
        return self.acceptance_rate >= (self.acceptance_threshold * 100.0)

    def summary(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "acceptance_rate": f"{self.acceptance_rate:.1f}%",
            "is_acceptable": self.is_acceptable,
        }


class DatasetContract:
    """
    عقد dataset: يتحقق من كل سجل مقابل مواصفات الأعمدة.
    - validate_record: يرجع قائمة مشاكل لسجل واحد.
    - validate_dataset: يرجع ContractReport لمجموعة.
    """

    def __init__(self, name: str, columns: List[ColumnSpec]):
        if not columns:
            raise ValueError("columns لا يمكن أن تكون فارغة")
        self.name = name
        self.columns = list(columns)

    def required_columns(self) -> List[str]:
        """أسماء الأعمدة الإلزامية"""
        return [c.name for c in self.columns if c.required]

    @staticmethod
    def _is_missing(value: Any) -> bool:
        return value is None or str(value).strip() == ""

    def validate_record(self, record: Dict[str, Any]) -> List[ContractIssue]:
        """التحقق من سجل واحد، يرجع قائمة المشاكل"""
        issues: List[ContractIssue] = []
        for col in self.columns:
            value = record.get(col.name)

            # 1) الإلزامية
            if self._is_missing(value):
                if col.required:
                    issues.append(ContractIssue(
                        col.name, f"العمود الإلزامي مفقود: {col.name}", value))
                continue

            # 2) النوع + النطاق للأرقام
            if col.dtype in ("float", "int"):
                try:
                    num = float(value)
                except (ValueError, TypeError):
                    issues.append(ContractIssue(
                        col.name, f"قيمة غير رقمية بعمود {col.dtype}: {col.name}", value))
                    continue
                if col.dtype == "int" and num != int(num):
                    issues.append(ContractIssue(
                        col.name, f"قيمة غير صحيحة بعمود int: {col.name}", value))
                    continue
                if col.min_value is not None and num < col.min_value:
                    issues.append(ContractIssue(
                        col.name, f"القيمة أقل من الحد الأدنى ({col.min_value}) لـ {col.name}", value))
                if col.max_value is not None and num > col.max_value:
                    issues.append(ContractIssue(
                        col.name, f"القيمة أعلى من الحد الأقصى ({col.max_value}) لـ {col.name}", value))

            # 3) القيم المسموحة للنصوص
            elif col.dtype == "str":
                if col.allowed_values is not None and str(value) not in col.allowed_values:
                    issues.append(ContractIssue(
                        col.name,
                        f"قيمة غير مسموحة بـ {col.name}: {value} (المسموح: {col.allowed_values})",
                        value))
        return issues

    def validate_dataset(
        self, records: List[Dict[str, Any]], acceptance_threshold: float = 0.95
    ) -> ContractReport:
        """التحقق من مجموعة بيانات كاملة"""
        report = ContractReport(total=len(records), acceptance_threshold=acceptance_threshold)
        for idx, record in enumerate(records):
            issues = self.validate_record(record)
            if issues:
                report.invalid_count += 1
                report.invalid_details.append({
                    "index": idx,
                    "issues": [{"column": i.column, "message": i.message} for i in issues],
                })
            else:
                report.valid_count += 1
        logger.info(f"[{self.name}] تحقق: {report.valid_count}/{report.total} صالح")
        return report


# ===== عقود جاهزة لمجموعات بيانات معتمدة =====

UCI_CANCER = DatasetContract(
    name="UCI Breast Cancer Wisconsin",
    columns=[
        ColumnSpec("diagnosis", dtype="str", allowed_values=["M", "B"]),  # M=خبيث B=حميد
        ColumnSpec("radius_mean", dtype="float", min_value=0),
        ColumnSpec("texture_mean", dtype="float", min_value=0),
        ColumnSpec("perimeter_mean", dtype="float", min_value=0),
        ColumnSpec("area_mean", dtype="float", min_value=0),
        ColumnSpec("smoothness_mean", dtype="float", min_value=0, max_value=1),
    ],
)

# سجل العقود الجاهزة (للتوسع المستقبلي: كل dataset جديد يُضاف هنا)
REGISTRY: Dict[str, DatasetContract] = {
    "uci_cancer": UCI_CANCER,
}


def get_contract(name: str) -> DatasetContract:
    """استرجاع عقد جاهز بالاسم"""
    if name not in REGISTRY:
        raise KeyError(f"عقد غير معروف: {name}. المتاح: {list(REGISTRY.keys())}")
    return REGISTRY[name]
