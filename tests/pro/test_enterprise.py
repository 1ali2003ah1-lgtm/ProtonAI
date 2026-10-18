"""Enterprise layer tests."""
import os, sys, tempfile
sys.path.insert(0, os.getcwd())

from protonai.enterprise.auth import TenantStore, Tenant, User
from protonai.enterprise.tasks import TaskQueue, TaskStatus
from protonai.enterprise.audit_log import AuditLog


def test_rbac_permissions():
    u = User(id="u1", email="p@x.com", role="physician",
             tenant_id="t1", api_key_hash="")
    assert u.has("read.cases")
    assert u.has("write.approvals")
    assert not u.has("admin.anything")


def test_rbac_admin_wildcard():
    u = User(id="a", email="a@x.com", role="admin",
             tenant_id="t1", api_key_hash="")
    assert u.has("any.thing")


def test_tenant_store_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        ts = TenantStore(path=os.path.join(td, "t.json"))
        t = ts.create_tenant(Tenant(id="t1", name="Hospital X"))
        assert t.id == "t1"
        u, key = ts.create_user(User(id="u1", email="u@x.com",
                                      role="physicist", tenant_id="t1"))
        auth = ts.authenticate(key)
        assert auth is not None and auth.id == "u1"


def test_task_queue_submit_and_complete():
    with tempfile.TemporaryDirectory() as td:
        q = TaskQueue(state_path=os.path.join(td, "q.json"))
        @q.register("test_task")
        def _h(task):
            return {"ok": True}
        t = q.submit("test_task", {"x": 1})
        import time; time.sleep(0.3)
        assert q.get(t.id).status == TaskStatus.SUCCESS


def test_audit_log_integrity():
    with tempfile.TemporaryDirectory() as td:
        log = AuditLog(db_path=os.path.join(td, "a.db"))
        log.record("login", user_id="u1")
        log.record("case.processed", resource_type="case",
                   resource_id="c1", user_id="u1")
        log.record("approval", resource_type="case",
                   resource_id="c1", user_id="u1")
        v = log.verify_integrity()
        assert v["valid"] and v["count"] == 3
