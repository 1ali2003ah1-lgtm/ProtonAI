"""
ProtonAI - Physician Review Loop
حلقة مراجعة الطبيب: إحالة تلقائية للتنبؤات المشبوهة + تسجيل قرارات الطبيب
كل قرار يُسجّل بسجل تدقيق مقاوم للتلاعب (إن مُرّر)
"""

import uuid
import logging
from enum import Enum
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ProtonAI.PhysicianReview")


class ReviewStatus(str, Enum):
    """حالة طلب المراجعة"""
    PENDING = "pending"
    REVIEWED = "reviewed"


class ReviewDecision(str, Enum):
    """قرار الطبيب"""
    APPROVE = "approve"   # يوافق على التنبؤ
    REJECT = "reject"     # يرفضه (التنبؤ غلط)
    FLAG = "flag"         # يعلّمه للمتابعة/مزيد فحص


def _to_decision(value: Any) -> ReviewDecision:
    """تحويل آمن لقرار (str أو enum) مع validation"""
    if isinstance(value, ReviewDecision):
        return value
    try:
        return ReviewDecision(str(value).strip().lower())
    except ValueError:
        valid = [d.value for d in ReviewDecision]
        raise ValueError(f"قرار غير صالح: {value}. المسموح: {valid}")


@dataclass
class ReviewRequest:
    """طلب مراجعة واحد"""
    request_id: str
    sample_id: str
    prediction: Any
    reasons: List[str]
    status: ReviewStatus = ReviewStatus.PENDING
    true_value: Any = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    record: Optional[Dict[str, Any]] = None
    decision: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReviewRequest":
        return cls(
            request_id=d["request_id"], sample_id=d["sample_id"],
            prediction=d["prediction"], reasons=d["reasons"],
            status=ReviewStatus(d["status"]), true_value=d.get("true_value"),
            metrics=d.get("metrics", {}), record=d.get("record"),
            decision=d.get("decision"), created_at=d.get("created_at", ""),
        )


class PhysicianReviewLoop:
    """
    حلقة مراجعة الطبيب.
    - flag_for_review: يحيل عينة تلقائياً إن خالفت قاعدة، وإلا None.
    - submit_decision: يسجّل قرار الطبيب (مرة وحدة فقط).
    - pending / completed / stats: استعلامات.
    - save / load: حفظ السجل.
    """

    def __init__(
        self,
        audit: Any = None,
        low_confidence_threshold: float = 0.7,
        high_ci_width: Optional[float] = None,
        clinical_tolerance: float = 3.0,
    ):
        if not (0 <= low_confidence_threshold <= 1):
            raise ValueError("low_confidence_threshold يجب أن يكون بين 0 و 1")
        if clinical_tolerance <= 0:
            raise ValueError("clinical_tolerance يجب أن يكون > 0")
        self.audit = audit
        self.low_confidence_threshold = low_confidence_threshold
        self.high_ci_width = high_ci_width
        self.clinical_tolerance = clinical_tolerance
        self.requests: List[ReviewRequest] = []

    def _index(self, request_id: str) -> int:
        for i, r in enumerate(self.requests):
            if r.request_id == request_id:
                return i
        raise ValueError(f"طلب مراجعة غير موجود: {request_id}")

    def flag_for_review(
        self,
        sample_id: str,
        prediction: Any,
        true_value: Any = None,
        confidence: Optional[float] = None,
        ci_width: Optional[float] = None,
        abs_error: Optional[float] = None,
        out_of_protocol: bool = False,
        record: Optional[Dict[str, Any]] = None,
    ) -> Optional[ReviewRequest]:
        """إحالة تلقائية إن خالفت قاعدة واحدة على الأقل، وإلا None"""
        reasons: List[str] = []
        if confidence is not None and confidence < self.low_confidence_threshold:
            reasons.append(f"low_confidence:{confidence:.3f}")
        if (ci_width is not None and self.high_ci_width is not None
                and ci_width > self.high_ci_width):
            reasons.append(f"high_uncertainty:{ci_width:.3f}")
        if abs_error is not None and abs_error > self.clinical_tolerance:
            reasons.append(f"clinical_error:{abs_error:.3f}")
        if out_of_protocol:
            reasons.append("out_of_protocol")

        if not reasons:
            return None

        req = ReviewRequest(
            request_id=uuid.uuid4().hex[:12],
            sample_id=str(sample_id), prediction=prediction,
            reasons=reasons, true_value=true_value,
            metrics={"confidence": confidence, "ci_width": ci_width,
                     "abs_error": abs_error, "out_of_protocol": out_of_protocol},
            record=record,
        )
        self.requests.append(req)
        logger.info(f"إحالة للمراجعة {req.request_id} ({sample_id}): {reasons}")
        if self.audit is not None:
            self.audit.log("physician_review", "flag", str(sample_id),
                           _audit_outcome(self.audit, "INFO"),
                           {"request_id": req.request_id, "reasons": reasons,
                            "prediction": prediction})
        return req

    def submit_decision(
        self, request_id: str, reviewer_id: str,
        decision: Any, notes: str = "",
    ) -> ReviewRequest:
        """تسجيل قرار الطبيب (مرة وحدة فقط لكل طلب)"""
        dec = _to_decision(decision)
        i = self._index(request_id)
        req = self.requests[i]
        if req.status == ReviewStatus.REVIEWED:
            raise ValueError(f"الطلب {request_id} تمت مراجعته مسبقاً")
        decision_record = {
            "reviewer_id": str(reviewer_id), "decision": dec.value,
            "notes": notes, "timestamp": datetime.now().isoformat(),
        }
        req.decision = decision_record
        req.status = ReviewStatus.REVIEWED
        logger.info(f"قرار الطبيب على {request_id}: {dec.value} بواسطة {reviewer_id}")
        if self.audit is not None:
            self.audit.log("physician_review", f"decision_{dec.value}",
                           req.sample_id, _audit_outcome(self.audit, "SUCCESS"),
                           {"request_id": request_id, "reviewer_id": str(reviewer_id),
                            "notes": notes})
        return req

    def pending(self) -> List[ReviewRequest]:
        """الطلبات المنتظرة للمراجعة"""
        return [r for r in self.requests if r.status == ReviewStatus.PENDING]

    def completed(self) -> List[ReviewRequest]:
        """الطلبات المُراجعة"""
        return [r for r in self.requests if r.status == ReviewStatus.REVIEWED]

    def stats(self) -> Dict[str, Any]:
        """إحصاءات الحلقة"""
        by_decision: Dict[str, int] = {}
        by_reason: Dict[str, int] = {}
        for r in self.requests:
            for reason in r.reasons:
                key = reason.split(":")[0]
                by_reason[key] = by_reason.get(key, 0) + 1
            if r.decision:
                d = r.decision["decision"]
                by_decision[d] = by_decision.get(d, 0) + 1
        return {
            "total_flagged": len(self.requests),
            "pending_count": len(self.pending()),
            "completed_count": len(self.completed()),
            "by_decision": by_decision,
            "by_reason": by_reason,
        }

    def save(self, path: str | Path) -> None:
        """حفظ سجل المراجعات"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            import json
            json.dump([r.to_dict() for r in self.requests], f, indent=2, ensure_ascii=False)
        logger.info(f"تم حفظ سجل المراجعات ({len(self.requests)}) في: {path}")

    def load(self, path: str | Path) -> None:
        """تحميل سجل المراجعات"""
        import json
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"ملف المراجعات غير موجود: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.requests = [ReviewRequest.from_dict(d) for d in data]
        logger.info(f"تم تحميل {len(self.requests)} طلب مراجعة من: {path}")


def _audit_outcome(audit: Any, name: str):
    """استخراج قيمة AuditOutcome بالاسم إن وُجدت، وإلا النص (للمرونة)"""
    try:
        from audit import AuditOutcome
        return getattr(AuditOutcome, name)
    except Exception:
        return name
