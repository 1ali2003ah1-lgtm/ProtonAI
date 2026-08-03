"""
ProtonAI - Test Approval Gates (Maker-Checker)
اختبارات بوابات الاعتماد (RBAC + فصل مهام + لا قرار مزدوج + تدقيق)
"""

import pytest
from approval_gates import (
    ApprovalGate, ChangeRequest, ChangeStatus, SeparationOfDutiesError,
)
from access_control import User, Role, PermissionDeniedError
from audit_trails import EnterpriseAuditTrail


def _u(role, uid):
    return User(uid, role)


ADMIN1 = lambda: _u(Role.ADMIN, "admin1")
ADMIN2 = lambda: _u(Role.ADMIN, "admin2")
PHYS = lambda: _u(Role.PHYSICIST, "phys1")
VIEW = lambda: _u(Role.VIEWER, "view1")


@pytest.fixture
def gate():
    return ApprovalGate()


class TestPropose:
    def test_creates_pending(self, gate):
        cr = gate.propose(ADMIN1(), "threshold", "رفع عتبة gamma", {"to": 0.96})
        assert cr.status == ChangeStatus.PENDING
        assert cr.proposed_by == "admin1"
        assert cr.change_type == "threshold"
        assert cr.payload == {"to": 0.96}
        assert len(cr.request_id) == 8

    def test_any_role_can_propose(self, gate):
        cr = gate.propose(PHYS(), "protocol", "تحديث بروتوكول")
        assert cr.proposed_by == "phys1"

    def test_pending_listed(self, gate):
        cr = gate.propose(ADMIN1(), "config", "x")
        assert [c.request_id for c in gate.pending()] == [cr.request_id]


class TestApprove:
    def test_different_admin_approves(self, gate):
        cr = gate.propose(ADMIN1(), "threshold", "x")
        upd = gate.approve(ADMIN2(), cr.request_id)
        assert upd.status == ChangeStatus.APPROVED
        assert upd.decided_by == "admin2"
        assert upd.decided_at

    def test_same_user_separation_raises(self, gate):
        cr = gate.propose(ADMIN1(), "threshold", "x")
        with pytest.raises(SeparationOfDutiesError):
            gate.approve(ADMIN1(), cr.request_id)

    def test_non_admin_denied(self, gate):
        cr = gate.propose(ADMIN1(), "threshold", "x")
        # الفيزيائي ما يملك CHANGE_CONFIG
        with pytest.raises(PermissionDeniedError):
            gate.approve(PHYS(), cr.request_id)

    def test_viewer_denied(self, gate):
        cr = gate.propose(ADMIN1(), "threshold", "x")
        with pytest.raises(PermissionDeniedError):
            gate.approve(VIEW(), cr.request_id)

    def test_unknown_request_raises(self, gate):
        with pytest.raises(ValueError):
            gate.approve(ADMIN2(), "nope")


class TestReject:
    def test_different_admin_rejects(self, gate):
        cr = gate.propose(ADMIN1(), "role", "x")
        upd = gate.reject(ADMIN2(), cr.request_id)
        assert upd.status == ChangeStatus.REJECTED
        assert upd.decided_by == "admin2"

    def test_same_user_reject_separation_raises(self, gate):
        cr = gate.propose(ADMIN1(), "role", "x")
        with pytest.raises(SeparationOfDutiesError):
            gate.reject(ADMIN1(), cr.request_id)


class TestNoDoubleDecision:
    def test_approve_then_approve_raises(self, gate):
        cr = gate.propose(ADMIN1(), "config", "x")
        gate.approve(ADMIN2(), cr.request_id)
        with pytest.raises(ValueError):
            gate.approve(ADMIN2(), cr.request_id)

    def test_approve_then_reject_raises(self, gate):
        cr = gate.propose(ADMIN1(), "config", "x")
        gate.approve(ADMIN2(), cr.request_id)
        with pytest.raises(ValueError):
            gate.reject(ADMIN2(), cr.request_id)

    def test_reject_then_approve_raises(self, gate):
        cr = gate.propose(ADMIN1(), "config", "x")
        gate.reject(ADMIN2(), cr.request_id)
        with pytest.raises(ValueError):
            gate.approve(ADMIN1(), cr.request_id)


class TestQueries:
    def test_three_buckets(self, gate):
        a = gate.propose(ADMIN1(), "config", "a")
        b = gate.propose(ADMIN1(), "config", "b")
        c = gate.propose(ADMIN1(), "config", "c")
        gate.approve(ADMIN2(), a.request_id)
        gate.reject(ADMIN2(), b.request_id)
        assert [x.request_id for x in gate.approved()] == [a.request_id]
        assert [x.request_id for x in gate.rejected()] == [b.request_id]
        assert [x.request_id for x in gate.pending()] == [c.request_id]


class TestAuditIntegration:
    def test_propose_and_approve_logged(self):
        ea = EnterpriseAuditTrail()
        gate = ApprovalGate(audit=ea)
        cr = gate.propose(ADMIN1(), "threshold", "x")
        gate.approve(ADMIN2(), cr.request_id)
        actions = [r["action"] for r in ea.records]
        assert "propose_change" in actions
        assert "approve_change" in actions
        # السجلات مربوطة بالأدوار
        rec = next(r for r in ea.records if r["action"] == "approve_change")
        assert rec["role"] == "admin"
        assert rec["user_id"] == "admin2"

    def test_separation_denied_logged(self):
        ea = EnterpriseAuditTrail()
        gate = ApprovalGate(audit=ea)
        cr = gate.propose(ADMIN1(), "threshold", "x")
        with pytest.raises(SeparationOfDutiesError):
            gate.approve(ADMIN1(), cr.request_id)
        outcomes = [r["outcome"] for r in ea.records if r["action"] == "decide_change"]
        assert "DENIED" in outcomes

    def test_no_audit_no_crash(self, gate):
        cr = gate.propose(ADMIN1(), "config", "x")
        gate.approve(ADMIN2(), cr.request_id)
        assert cr.status == ChangeStatus.APPROVED


class TestChangeRequestObject:
    def test_to_dict(self, gate):
        cr = gate.propose(ADMIN1(), "config", "desc", {"k": 1})
        d = cr.to_dict()
        assert d["status"] == "pending"
        assert d["payload"] == {"k": 1}
        assert isinstance(cr, ChangeRequest)
