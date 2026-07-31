"""
ProtonAI - Treatment Plan
كائن الخطة العلاجية الموحّد: يجمع بيانات كل المراحل بأقسام منفصلة
patient_id مخفي الهوية (تذكير بأمان المرحلة 1). الأقسام dicts مرنة.
مصدر حقيقة واحد لكل وحدات دعم القرار السريري بالمرحلة 6
"""

import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger("ProtonAI.TreatmentPlan")

# الأقسام الأربعة المنظّمة (ترتيب ثابت)
SECTIONS = ("imaging", "physics", "ai", "reviews")


@dataclass
class TreatmentPlan:
    """
    خطة علاجية موحّدة.
    - set_section: يملأ قسماً (dict) مع التحقق من الاسم والنوع (نسخة آمنة).
    - section_filled / completeness / is_complete / missing_sections: قياس الاكتمال.
    - to_dict / from_dict: تسلسل (مع نسخ الأقسام، لا مراجع مشتركة).
    - summary: ملخص سريع للحالة.
    """
    plan_id: str
    patient_id: str  # يجب أن يكون مخفي الهوية (anonymized)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    imaging: Dict[str, Any] = field(default_factory=dict)   # ملخص التصوير/التقسيم
    physics: Dict[str, Any] = field(default_factory=dict)   # ملخص الفيزياء/الجرعة
    ai: Dict[str, Any] = field(default_factory=dict)        # ملخص الذكاء الاصطناعي
    reviews: Dict[str, Any] = field(default_factory=dict)   # ملخص المراجعات البشرية
    notes: str = ""

    def __post_init__(self):
        """التحقق من الهوية والمعرّف (patient_id مخفي الهوية إلزامي)"""
        if not str(self.plan_id).strip():
            raise ValueError("plan_id لا يمكن أن يكون فارغاً")
        if not str(self.patient_id).strip():
            raise ValueError("patient_id لا يمكن أن يكون فارغاً (ويجب أن يكون مخفي الهوية)")

    def set_section(self, name: str, data: Dict[str, Any]) -> None:
        """ملء قسم بنسخة آمنة (تعديل الأصل لا يؤثر بالخطة)"""
        if name not in SECTIONS:
            raise ValueError(f"قسم غير معروف: {name}. المسموح: {SECTIONS}")
        if not isinstance(data, dict):
            raise TypeError(f"بيانات القسم {name} يجب أن تكون dict")
        setattr(self, name, dict(data))

    def section_filled(self, name: str) -> bool:
        """هل القسم ممتلئ (غير فارغ)؟"""
        if name not in SECTIONS:
            raise ValueError(f"قسم غير معروف: {name}")
        return bool(getattr(self, name))

    def completeness(self) -> float:
        """نسبة الأقسام الممتلئة (0..1)"""
        filled = sum(1 for s in SECTIONS if self.section_filled(s))
        return filled / len(SECTIONS)

    def is_complete(self) -> bool:
        """هل كل الأقسام الأربعة ممتلئة؟"""
        return all(self.section_filled(s) for s in SECTIONS)

    def missing_sections(self) -> List[str]:
        """الأقسام الفارغة"""
        return [s for s in SECTIONS if not self.section_filled(s)]

    def to_dict(self) -> Dict[str, Any]:
        """تصدير كقاموس (نسخة عميقة للأقسام)"""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TreatmentPlan":
        """بناء من قاموس (نسخ الأقسام، افتراضيات آمنة للحقول الغائبة)"""
        return cls(
            plan_id=d["plan_id"], patient_id=d["patient_id"],
            created_at=d.get("created_at", datetime.now().isoformat()),
            imaging=dict(d.get("imaging", {})),
            physics=dict(d.get("physics", {})),
            ai=dict(d.get("ai", {})),
            reviews=dict(d.get("reviews", {})),
            notes=d.get("notes", ""),
        )

    def summary(self) -> Dict[str, Any]:
        """ملخص سريع لحالة الخطة"""
        return {
            "plan_id": self.plan_id, "patient_id": self.patient_id,
            "completeness": self.completeness(), "is_complete": self.is_complete(),
            "missing_sections": self.missing_sections(), "created_at": self.created_at,
        }


def new_plan_id() -> str:
    """معرّف خطة جديد فريد (12 خانة)"""
    return uuid.uuid4().hex[:12]
