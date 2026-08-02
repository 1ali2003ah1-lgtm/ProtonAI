"""
ProtonAI - Decision Model
نموذج القرار البشري في الحلقة (human-in-the-loop)
المنصة توصي فقط؛ القرار النهائي + التوقيع = للمتخصص (final decision remains with specialist)
بوابة تسليم صريحة: لا تسليم بلا مؤشرات آمنة + توقيع الطبيب + توقيع الفيزيائي
تجاوز المتخصص للبوابة = override موثّق (مساءلة، لا صمت)
"""

import logging
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from quality_indicators import QualityIndicators, Status
from treatment_plan import TreatmentPlan

logger = logging.getLogger("ProtonAI.DecisionModel")


class Recommendation(str, Enum):
    """توصية المنصة (ليست قراراً)"""
    APPROVE = "approve"              # موصى بالاعتماد
    REVIEW_REQUIRED = "review"       # يلزم مراجعة قبل الاعتماد
    REJECT = "reject"                # مرفوض (مؤشرات خطرة)
    INCOMPLETE = "incomplete"        # بيانات ناقصة (لا توصية ممكنة)


class SpecialistDecision(str, Enum):
    """قرار المتخصص النهائي"""
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"   # يؤجل القرار (يطلب بيانات/مراجعة إضافية)


def _to_decision(value: Any) -> SpecialistDecision:
    """تحويل آمن لقرار المتخصص"""
    if isinstance(value, SpecialistDecision):
        return value
    try:
        return SpecialistDecision(str(value).strip().lower())
    except ValueError:
        valid = [d.value for d in SpecialistDecision]
        raise ValueError(f"قرار غير صالح: {value}. المسموح: {valid}")


@dataclass
class DecisionRecord:
    """سجل قرار واحد: توصية المنصة + بوابة التسليم + قرار المتخصص"""
    recommendation: Recommendation
    recommendation_reason: str
    can_deliver: bool
    delivery_blockers: List[str]
    overall_status: str
    physician_signed: bool
    physics_signed: bool
    specialist_decision: Optional[str] = None
    specialist_id: Optional[str] = None
    specialist_notes: str = ""
    specialist_timestamp: Optional[str] = None
    override: bool = False  # True = المتخصص اعتمد رغم إغلاق البوابة (موثّق)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["recommendation"] = self.recommendation.value
        return d


class DecisionModel:
    """
    نموذج القرار.
    - recommend: يبني DecisionRecord من تقييم جودة + تواقيع (توصية + بوابة، بلا قرار متخصص).
    - recommend_plan: يستخرج التقييم من خطة ثم يوصي.
    - record_specialist_decision: يسجّل قرار المتخصص (مرة وحدة؛ override موثّق).
    المنصة توصي فقط؛ can_deliver=False يمنع التسليم الآلي، لا قرار المتخصص الواعي.
    """

    def __init__(self, quality: Optional[QualityIndicators] = None):
        self.qi = quality if quality is not None else QualityIndicators()

    def _blockers(
        self, overall: Status, physician_signed: bool, physics_signed: bool
    ) -> List[str]:
        """قائمة موانع التسليم (فاضية = يمكن التسليم الآلي)"""
        blockers: List[str] = []
        if overall == Status.RED:
            blockers.append("quality_red")
        if overall == Status.UNKNOWN:
            blockers.append("quality_unknown")
        if not physician_signed:
            blockers.append("physician_unsigned")
        if not physics_signed:
            blockers.append("physics_unsigned")
        return blockers

    def _recommendation(
        self, overall: Status, physician_signed: bool, physics_signed: bool
    ):
        """مستوى التوصية + السبب (توصية فقط، لا قرار)"""
        if overall == Status.UNKNOWN:
            return Recommendation.INCOMPLETE, "بيانات غير مكتملة — لا توصية ممكنة"
        if overall == Status.RED:
            return Recommendation.REJECT, "مؤشرات خطرة — يلزم تصحيح قبل أي اعتماد"
        if not physician_signed or not physics_signed:
            missing = []
            if not physician_signed:
                missing.append("الطبيب")
            if not physics_signed:
                missing.append("الفيزيائي")
            return (Recommendation.REVIEW_REQUIRED,
                    f"التواقيع البشرية ناقصة ({', '.join(missing)}) — القرار النهائي معلّق")
        if overall == Status.AMBER:
            return (Recommendation.REVIEW_REQUIRED,
                    "مؤشرات تحذيرية — يلزم مراجعة المتخصص قبل الاعتماد")
        return (Recommendation.APPROVE,
                "المؤشرات مقبولة والتواقيع مكتملة — موصى بالاعتماد")

    def recommend(
        self,
        evaluation: Dict[str, Any],
        physician_signed: bool = False,
        physics_signed: bool = False,
    ) -> DecisionRecord:
        """بناء سجل قرار من تقييم جودة مُسبق + تواقيع"""
        overall = evaluation["overall"]
        blockers = self._blockers(overall, physician_signed, physics_signed)
        rec, reason = self._recommendation(overall, physician_signed, physics_signed)
        logger.info(f"decision: rec={rec.value}, can_deliver={not blockers}, "
                    f"blockers={blockers}")
        return DecisionRecord(
            recommendation=rec, recommendation_reason=reason,
            can_deliver=not blockers, delivery_blockers=blockers,
            overall_status=overall.name,
            physician_signed=bool(physician_signed),
            physics_signed=bool(physics_signed),
        )

    def recommend_plan(
        self,
        plan: TreatmentPlan,
        physician_signed: bool = False,
        physics_signed: bool = False,
    ) -> DecisionRecord:
        """استخراج التقييم من خطة ثم التوصية"""
        evaluation = self.qi.evaluate_plan(plan)
        return self.recommend(evaluation, physician_signed, physics_signed)

    def record_specialist_decision(
        self,
        record: DecisionRecord,
        decision: Any,
        specialist_id: str,
        notes: str = "",
    ) -> DecisionRecord:
        """
        تسجيل قرار المتخصص النهائي (مرة وحدة).
        override=True لو APPROVE والبوابة مغلقة (تجاوز واعي موثّق، لا صمت).
        """
        dec = _to_decision(decision)
        if record.specialist_decision is not None:
            raise ValueError("تم تسجيل قرار المتخصص مسبقاً على هذا السجل")
        if not str(specialist_id).strip():
            raise ValueError("specialist_id لا يمكن أن يكون فارغاً")
        override = bool(dec == SpecialistDecision.APPROVE and not record.can_deliver)
        if override:
            logger.warning(f"تجاوز المتخصص للبوابة: {specialist_id} اعتمد رغم "
                           f"blockers={record.delivery_blockers} — موثّق كـ override")
        record.specialist_decision = dec.value
        record.specialist_id = str(specialist_id)
        record.specialist_notes = notes
        record.specialist_timestamp = datetime.now().isoformat()
        record.override = override
        return record
