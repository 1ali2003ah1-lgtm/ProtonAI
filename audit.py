"""
ProtonAI - Audit Trail
سجل تدقيق موحّد ومقاوم للتلاعب (سلسلة مربوطة بتجزئة SHA-256)
يسجّل كل عملية: من / متى / شنو / على شنو / النتيجة
"""

import json
import uuid
import hashlib
import logging
from enum import Enum
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ProtonAI.Audit")

# تجزئة البداية للسلسلة (genesis)
GENESIS_HASH = "0" * 64


class AuditOutcome(str, Enum):
    """نتيجة العملية المسجّلة"""
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    INFO = "info"


@dataclass
class AuditEvent:
    """حدث تدقيق واحد"""
    event_id: str
    timestamp: str
    actor: str
    action: str
    target: str
    outcome: AuditOutcome
    details: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = GENESIS_HASH
    hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["outcome"] = self.outcome.value  # نحفظ القيمة النصية
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AuditEvent":
        return cls(
            event_id=d["event_id"],
            timestamp=d["timestamp"],
            actor=d["actor"],
            action=d["action"],
            target=d["target"],
            outcome=AuditOutcome(d["outcome"]),
            details=d.get("details", {}),
            previous_hash=d.get("previous_hash", GENESIS_HASH),
            hash=d.get("hash", ""),
        )


def _compute_hash(event: "AuditEvent") -> str:
    """
    حساب تجزئة الحدث من حقوله + تجزئة الحدث السابق.
    ربط previous_hash بالحساب هو ما يجعل السلسلة مقاومة للتلاعب.
    """
    payload = {
        "previous_hash": event.previous_hash,
        "event_id": event.event_id,
        "action": event.action,
        "target": event.target,
        "outcome": event.outcome.value,
        "timestamp": event.timestamp,
        "details": event.details,
    }
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class AuditTrail:
    """
    سجل التدقيق.
    - log: يضيف حدثاً جديداً مربوطاً بالسلسلة.
    - verify_chain: يكشف أي تلاعب بأي حدث.
    - filter_by: يستخرج أحداثاً محددة للمراجعة.
    - save / load: حفظ واسترجاع السجل.
    """

    def __init__(self):
        self.events: List[AuditEvent] = []

    def _last_hash(self) -> str:
        return self.events[-1].hash if self.events else GENESIS_HASH

    def log(
        self,
        actor: str,
        action: str,
        target: str,
        outcome: AuditOutcome = AuditOutcome.INFO,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """تسجيل حدث تدقيق جديد"""
        event = AuditEvent(
            event_id=uuid.uuid4().hex,
            timestamp=datetime.now().isoformat(),
            actor=actor,
            action=action,
            target=target,
            outcome=outcome,
            details=details or {},
            previous_hash=self._last_hash(),
        )
        event.hash = _compute_hash(event)
        self.events.append(event)
        logger.info(f"[AUDIT] {actor} :: {action} :: {target} :: {outcome.value}")
        return event

    def verify_chain(self) -> bool:
        """
        التحقق من سلامة السلسلة كاملة.
        يرجع False لو أي حدث تغيّر أو فُصل عن سابقه.
        """
        for i, event in enumerate(self.events):
            expected_prev = GENESIS_HASH if i == 0 else self.events[i - 1].hash
            if event.previous_hash != expected_prev:
                logger.warning(f"كسر بالسلسلة عند الحدث {i}: previous_hash غير مطابق")
                return False
            if _compute_hash(event) != event.hash:
                logger.warning(f"تلاعب مكتشف بالحدث {i}: التجزئة لا تطابق المحتوى")
                return False
        return True

    def filter_by(
        self,
        action: Optional[str] = None,
        outcome: Optional[AuditOutcome] = None,
        target: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> List[AuditEvent]:
        """استخراج أحداث حسب معايير المراجعة"""
        result = self.events
        if action is not None:
            result = [e for e in result if e.action == action]
        if outcome is not None:
            result = [e for e in result if e.outcome == outcome]
        if target is not None:
            result = [e for e in result if e.target == target]
        if actor is not None:
            result = [e for e in result if e.actor == actor]
        return result

    def save(self, path: str | Path) -> None:
        """حفظ السجل في ملف JSON"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self.events], f, indent=2, ensure_ascii=False)
        logger.info(f"تم حفظ سجل التدقيق ({len(self.events)} حدث) في: {path}")

    def load(self, path: str | Path) -> None:
        """تحميل السجل من ملف JSON"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"ملف السجل غير موجود: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.events = [AuditEvent.from_dict(d) for d in data]
        logger.info(f"تم تحميل {len(self.events)} حدث تدقيق من: {path}")

    def summary(self) -> Dict[str, Any]:
        """ملخص السجل (مفيد للتقارير)"""
        by_outcome: Dict[str, int] = {}
        for e in self.events:
            by_outcome[e.outcome.value] = by_outcome.get(e.outcome.value, 0) + 1
        return {
            "total_events": len(self.events),
            "chain_valid": self.verify_chain(),
            "by_outcome": by_outcome,
}
