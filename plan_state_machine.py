"""
ProtonAI - Plan State Machine
سير عمل الخطة المحروس: مسودة ← فحص فيزياء ← اعتماد طبيب ← جاهزة ← مسلّمة
كل انتقال محروس بشروط (تواقيع + مؤشرات + بوابة). الحالات النهائية لا تُغادر.
مفكوك الارتباط: يقرأ الشروط من context dict (build_context يبنيه من الكائنات)
"""

import logging
from enum import Enum
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Set

logger = logging.getLogger("ProtonAI.PlanStateMachine")


class PlanState(str, Enum):
    """حالات الخطة"""
    DRAFT = "draft"                   # مسودة
    PHYSICS_REVIEW = "physics_review" # قيد فحص الفيزيائي
    PHYSICIAN_REVIEW = "physician_review"  # قيد اعتماد الطبيب
    READY = "ready"                   # جاهزة للتسليم
    DELIVERED = "delivered"           # مسلّمة (نهائية)
    REJECTED = "rejected"             # مرفوضة (نهائية)


TERMINAL_STATES: Set[PlanState] = {PlanState.DELIVERED, PlanState.REJECTED}

# الانتقالات المسموحة منطقياً (قبل فحص الحرس)؛ REJECTED يُضاف ضمنياً لكل غير نهائي
_ALLOWED: Dict[PlanState, Set[PlanState]] = {
    PlanState.DRAFT: {PlanState.PHYSICS_REVIEW},
    PlanState.PHYSICS_REVIEW: {PlanState.PHYSICIAN_REVIEW, PlanState.DRAFT},
    PlanState.PHYSICIAN_REVIEW: {PlanState.READY, PlanState.PHYSICS_REVIEW, PlanState.DRAFT},
    PlanState.READY: {PlanState.DELIVERED},
}


class GuardFailedError(ValueError):
    """فشل حرس انتقال (الشروط غير محققة، رغم أن الانتقال منطقي)"""


# ---------------- الحراس (يقرأون من context) ----------------

def _g_draft_to_physics(ctx: Dict[str, Any]) -> bool:
    """لا فحص فيزياء بلا بيانات فيزياء"""
    return bool(ctx.get("physics_available"))


def _g_physics_to_physician(ctx: Dict[str, Any]) -> bool:
    """الفيزيائي وقّع + المؤشرات الفيزيائية ليست خطرة/مفقودة"""
    return (bool(ctx.get("physics_signed"))
            and ctx.get("overall_status") not in ("RED", "UNKNOWN"))


def _g_physician_to_ready(ctx: Dict[str, Any]) -> bool:
    """الطبيب وقّع + البوابة مفتوحة (can_deliver)"""
    return bool(ctx.get("physician_signed")) and bool(ctx.get("can_deliver"))


def _g_ready_to_delivered(ctx: Dict[str, Any]) -> bool:
    """التسليم فقط بقرار المتخصص = approve (التجاوز موثّق بالـ decision، لا هنا)"""
    return ctx.get("specialist_decision") == "approve"


def _g_to_rejected(ctx: Dict[str, Any]) -> bool:
    """الرفض فقط بقرار المتخصص = reject"""
    return ctx.get("specialist_decision") == "reject"


def _g_always(_ctx: Dict[str, Any]) -> bool:
    """الرجوع للتحرير مسموح دايماً"""
    return True


# خريطة الحراس: (من، إلى) → دالة
_GUARDS: Dict[tuple, Callable[[Dict[str, Any]], bool]] = {
    (PlanState.DRAFT, PlanState.PHYSICS_REVIEW): _g_draft_to_physics,
    (PlanState.PHYSICS_REVIEW, PlanState.PHYSICIAN_REVIEW): _g_physics_to_physician,
    (PlanState.PHYSICIAN_REVIEW, PlanState.READY): _g_physician_to_ready,
    (PlanState.READY, PlanState.DELIVERED): _g_ready_to_delivered,
    (PlanState.PHYSICS_REVIEW, PlanState.DRAFT): _g_always,
    (PlanState.PHYSICIAN_REVIEW, PlanState.DRAFT): _g_always,
    (PlanState.PHYSICIAN_REVIEW, PlanState.PHYSICS_REVIEW): _g_always,
}


def build_context(
    plan: Any = None,
    evaluation: Any = None,
    decision: Any = None,
    *,
    physics_available: Optional[bool] = None,
    physician_signed: Optional[bool] = None,
    physics_signed: Optional[bool] = None,
    specialist_decision: Optional[str] = None,
) -> Dict[str, Any]:
    """
    يبني context من الكائنات (اختياري)؛ القيم الصريحة تتجاوز المستخرج.
    مفكوك: يفحص hasattr، لا يستورد الأنواع.
    """
    ctx: Dict[str, Any] = {}
    if plan is not None:
        ctx["physics_available"] = bool(getattr(plan, "physics", None))
    if evaluation is not None:
        overall = evaluation.get("overall") if isinstance(evaluation, dict) else None
        if overall is not None:
            ctx["overall_status"] = overall.name if hasattr(overall, "name") else str(overall)
    if decision is not None:
        if hasattr(decision, "can_deliver"):
            ctx["can_deliver"] = bool(decision.can_deliver)
        if hasattr(decision, "physician_signed"):
            ctx["physician_signed"] = bool(decision.physician_signed)
        if hasattr(decision, "physics_signed"):
            ctx["physics_signed"] = bool(decision.physics_signed)
        sd = getattr(decision, "specialist_decision", None)
        if sd is not None:
            ctx["specialist_decision"] = str(sd)
    # القيم الصريحة تتجاوز
    if physics_available is not None:
        ctx["physics_available"] = bool(physics_available)
    if physician_signed is not None:
        ctx["physician_signed"] = bool(physician_signed)
    if physics_signed is not None:
        ctx["physics_signed"] = bool(physics_signed)
    if specialist_decision is not None:
        ctx["specialist_decision"] = str(specialist_decision)
    return ctx


class PlanStateMachine:
    """
    آلة حالات الخطة.
    - transition: ينتقل إن مسموح منطقياً والحرس ناجح، وإلا يرمي.
    - can_transition: فحص جاف بدون تغيير الحالة.
    - history: سجل الانتقالات (للتدقيق).
    - is_terminal / allowed_targets: استعلامات.
    """

    def __init__(self, initial: PlanState = PlanState.DRAFT):
        self._state = initial
        self.history: List[Dict[str, str]] = []

    @property
    def state(self) -> PlanState:
        """الحالة الحالية"""
        return self._state

    @property
    def is_terminal(self) -> bool:
        """هل الحالة نهائية (لا خروج)؟"""
        return self._state in TERMINAL_STATES

    def _allowed(self, state: PlanState) -> Set[PlanState]:
        """الانتقالات المسموحة منطقياً من حالة (مع REJECTED لغير النهائي)"""
        base = set(_ALLOWED.get(state, set()))
        if state not in TERMINAL_STATES:
            base.add(PlanState.REJECTED)
        return base

    def allowed_targets(self) -> Set[PlanState]:
        """الانتقالات المسموحة منطقياً من الحالة الحالية"""
        return self._allowed(self._state)

    def _guard_for(self, src: PlanState, dst: PlanState):
        """دالة الحرس لانتقال (REJECTED من أي غير نهائي → _g_to_rejected)"""
        g = _GUARDS.get((src, dst))
        if g is not None:
            return g
        if dst == PlanState.REJECTED:
            return _g_to_rejected
        return None

    def _check(self, target: PlanState, ctx: Dict[str, Any]):
        """فحص جاف: (ok, reason)"""
        if self._state in TERMINAL_STATES:
            return False, "terminal"
        if target not in self._allowed(self._state):
            return False, "not_allowed"
        guard = self._guard_for(self._state, target)
        if guard is None or not guard(ctx):
            return False, "guard_failed"
        return True, ""

    def can_transition(self, target: PlanState, ctx: Optional[Dict[str, Any]] = None) -> bool:
        """هل الانتقال ممكن الآن؟ (بدون تغيير الحالة)"""
        ok, _ = self._check(target, ctx or {})
        return ok

    def transition(self, target: PlanState, ctx: Optional[Dict[str, Any]] = None) -> PlanState:
        """تنفيذ الانتقال، يرمي إن تعذّر"""
        ctx = ctx or {}
        ok, reason = self._check(target, ctx)
        if not ok:
            if reason == "terminal":
                raise ValueError(f"لا انتقال من حالة نهائية: {self._state.value}")
            if reason == "not_allowed":
                raise ValueError(
                    f"انتقال غير مسموح منطقياً: {self._state.value} → {target.value}")
            raise GuardFailedError(
                f"فشل حرس الانتقال: {self._state.value} → {target.value} "
                f"(الشروط غير محققة)")
        old = self._state
        self._state = target
        self.history.append({
            "from": old.value, "to": target.value,
            "timestamp": datetime.now().isoformat(),
        })
        logger.info(f"state: {old.value} → {target.value}")
        return self._state
