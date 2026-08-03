"""
ProtonAI - Approval Gates (Maker-Checker)
بوابات اعتماد التغييرات الحسّاسة بمبدأ four-eyes:
المُنشئ يقترح، شخص ثاني يعتمد/يرفض (maker ≠ checker)
حراسات: RBAC (CHANGE_CONFIG) + فصل مهام + لا قرار مزدوج
كل خطوة تُسجّل بالتدقيق المؤسسي باسم صاحبها ودوره
"""

import uuid
import logging
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

from access_control import AccessControl, User, Permission, PermissionDeniedError

logger = logging.getLogger("ProtonAI.ApprovalGates")


class ChangeStatus(str, Enum):
    """حالة طلب التغيير"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SeparationOfDutiesError(ValueError):
    """محاولة اعتماد/رفض تغيير من نفس مُنشئه (maker = checker)"""


@dataclass
class ChangeRequest:
    """طلب تغيير حسّاس"""
    request_id: str
    change_type: str          # config / protocol / role / threshold ...
    description: str
    proposed_by: str          # الـ maker
    payload: Dict[str, Any] = field(default_factory=dict)
    status: ChangeStatus = ChangeStatus.PENDING
    decided_by: Optional[str] = None   # الـ checker
    decided_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


class ApprovalGate:
    """
    بوابة maker-checker.
    - propose: ينشئ طلب تغيير PENDING (أي دور).
    - approve / reject: يبتّ بالطلب (CHANGE_CONFIG + maker≠checker + لم يُبتّ).
    - pending / approved / rejected: استعلامات.
    - يسجّل كل خطوة بالتدقيق المؤسسي إن حُقن.
    """

    def __init__(
        self,
        access: Optional[AccessControl] = None,
        audit: Any = None,  # EnterpriseAuditTrail اختياري
    ):
        self.access = access if access is not None else AccessControl()
        self.audit = audit
        self.requests: Dict[str, ChangeRequest] = {}

    def _log(self, user: User, action: str, target: str,
             outcome: str = "SUCCESS", details: Optional[Dict[str, Any]] = None) -> None:
        if self.audit is not None:
            self.audit.log_action(user, action, target, outcome, details)

    def propose(
        self,
        user: User,
        change_type: str,
        description: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> ChangeRequest:
        """إنشاء طلب تغيير PENDING (الـ maker)"""
        rid = uuid.uuid4().hex[:8]
        cr = ChangeRequest(
            request_id=rid, change_type=str(change_type),
            description=str(description), proposed_by=user.user_id,
            payload=dict(payload or {}))
        self.requests[rid] = cr
        self._log(user, "propose_change", rid, "SUCCESS",
                  {"change_type": cr.change_type})
        logger.info(f"propose: {rid} by {user.user_id} ({change_type})")
        return cr

    def _get(self, request_id: str) -> ChangeRequest:
        if request_id not in self.requests:
            raise ValueError(f"طلب تغيير غير موجود: {request_id}")
        return self.requests[request_id]

    def _decide(
        self, approver: User, request_id: str, decision: ChangeStatus
    ) -> ChangeRequest:
        """البتّ بالطلب بحراسات RBAC + فصل مهام + لا قرار مزدوج"""
        cr = self._get(request_id)
        if cr.status != ChangeStatus.PENDING:
            raise ValueError(f"الطلب {request_id} مُبتّ به مسبقاً ({cr.status.value})")
        # 1) RBAC: المعتمد يملك CHANGE_CONFIG
        self.access.require(approver, Permission.CHANGE_CONFIG)
        # 2) فصل مهام: المعتمد ≠ المُنشئ
        if approver.user_id == cr.proposed_by:
            self._log(approver, "decide_change", request_id, "DENIED",
                      {"reason": "maker_equals_checker"})
            raise SeparationOfDutiesError(
                f"المستخدم '{approver.user_id}' لا يقدر يعتمد تغييراً أنشأه بنفسه "
                f"(maker ≠ checker)")
        cr.status = decision
        cr.decided_by = approver.user_id
        cr.decided_at = datetime.now().isoformat()
        self._log(approver, f"{'approve' if decision == ChangeStatus.APPROVED else 'reject'}_change",
                  request_id, "SUCCESS", {"change_type": cr.change_type})
        logger.info(f"decide: {request_id} → {decision.value} by {approver.user_id}")
        return cr

    def approve(self, approver: User, request_id: str) -> ChangeRequest:
        """اعتماد الطلب (checker)"""
        return self._decide(approver, request_id, ChangeStatus.APPROVED)

    def reject(self, approver: User, request_id: str) -> ChangeRequest:
        """رفض الطلب (checker)"""
        return self._decide(approver, request_id, ChangeStatus.REJECTED)

    def pending(self) -> List[ChangeRequest]:
        """الطلبات المعلّقة"""
        return [c for c in self.requests.values() if c.status == ChangeStatus.PENDING]

    def approved(self) -> List[ChangeRequest]:
        """الطلبات المعتمدة"""
        return [c for c in self.requests.values() if c.status == ChangeStatus.APPROVED]

    def rejected(self) -> List[ChangeRequest]:
        """الطلبات المرفوضة"""
        return [c for c in self.requests.values() if c.status == ChangeStatus.REJECTED]
