"""
ProtonAI - Test Access Control (RBAC)
اختبارات الأدوار والصلاحيات + فصل المهام + require + الحراس
"""

import pytest
from access_control import (
    AccessControl, User, Role, Permission, PermissionDeniedError,
    ROLE_PERMISSIONS, ALL_PERMISSIONS, _perm,
)


@pytest.fixture
def ac():
    return AccessControl()


def _u(role):
    return User(f"id_{role}", role, name=f"name_{role}")


class TestRolePermissionsDesign:
    def test_every_role_has_permissions(self):
        for role in Role:
            assert len(ROLE_PERMISSIONS[role]) > 0

    def test_all_permissions_covered(self):
        # لا توجد صلاحية يتيمة (كل صلاحية عند دور واحد على الأقل)
        assert ALL_PERMISSIONS == set(Permission)

    def test_viewer_minimal(self):
        assert ROLE_PERMISSIONS[Role.VIEWER] == {
            Permission.VIEW_PLAN, Permission.VIEW_DASHBOARD}

    def test_separation_auditor_cannot_change(self):
        # المدقق لا يعدّل ولا يسلّم ولا يرفض (لا يغيّر ما يدقّقه)
        aud = ROLE_PERMISSIONS[Role.AUDITOR]
        for forbidden in (Permission.EDIT_PLAN, Permission.EDIT_PHYSICS,
                          Permission.DELIVER, Permission.REJECT,
                          Permission.SIGN_PHYSICIAN, Permission.SIGN_PHYSICS):
            assert forbidden not in aud

    def test_separation_admin_cannot_view_audit(self):
        # الإداري لا يرى سجل التدقيق الحسّاس (التدقيق للمستقل فقط)
        assert Permission.VIEW_AUDIT not in ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.EXPORT_AUDIT not in ROLE_PERMISSIONS[Role.ADMIN]

    def test_auditor_has_audit_rights(self):
        aud = ROLE_PERMISSIONS[Role.AUDITOR]
        assert Permission.VIEW_AUDIT in aud
        assert Permission.EXPORT_AUDIT in aud

    def test_admin_has_delivery_rights(self):
        adm = ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.DELIVER in adm
        assert Permission.REJECT in adm
        assert Permission.MANAGE_USERS in adm

    def test_physician_cannot_deliver(self):
        # الطبيب يوصي ويوقّع، لا يسلّم (التسليم إداري)
        assert Permission.DELIVER not in ROLE_PERMISSIONS[Role.PHYSICIAN]
        assert Permission.SIGN_PHYSICIAN in ROLE_PERMISSIONS[Role.PHYSICIAN]

    def test_physicist_cannot_sign_physician(self):
        # فصل بين توقيع الطبيب وتوقيع الفيزيائي
        assert Permission.SIGN_PHYSICIAN not in ROLE_PERMISSIONS[Role.PHYSICIST]
        assert Permission.SIGN_PHYSICS in ROLE_PERMISSIONS[Role.PHYSICIST]


class TestUser:
    def test_basic(self):
        u = User("u1", Role.PHYSICIAN, "Ahmed")
        assert u.user_id == "u1"
        assert u.role == Role.PHYSICIAN
        assert u.name == "Ahmed"

    def test_role_from_string(self):
        u = User("u1", "physician")
        assert u.role == Role.PHYSICIAN

    def test_permissions_match_role(self):
        u = _u(Role.ADMIN)
        assert u.permissions == ROLE_PERMISSIONS[Role.ADMIN]

    def test_permissions_is_copy(self):
        u = _u(Role.VIEWER)
        perms = u.permissions
        perms.add(Permission.DELIVER)  # تعديل النسخة
        assert Permission.DELIVER not in u.permissions  # الأصل سليم

    def test_empty_user_id_raises(self):
        with pytest.raises(ValueError):
            User("", Role.VIEWER)

    def test_whitespace_user_id_raises(self):
        with pytest.raises(ValueError):
            User("   ", Role.VIEWER)

    def test_invalid_role_raises(self):
        with pytest.raises(ValueError):
            User("u1", "superuser")

    def test_immutable(self):
        u = _u(Role.VIEWER)
        with pytest.raises(Exception):  # frozen dataclass
            u.role = Role.ADMIN  # type: ignore


class TestPermHelper:
    def test_from_enum(self):
        assert _perm(Permission.DELIVER) == Permission.DELIVER

    def test_from_string(self):
        assert _perm("deliver") == Permission.DELIVER

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            _perm("fly")


class TestCan:
    def test_viewer_can_view(self, ac):
        assert ac.can(_u(Role.VIEWER), Permission.VIEW_PLAN) is True

    def test_viewer_cannot_edit(self, ac):
        assert ac.can(_u(Role.VIEWER), Permission.EDIT_PLAN) is False

    def test_viewer_cannot_deliver(self, ac):
        assert ac.can(_u(Role.VIEWER), Permission.DELIVER) is False

    def test_physician_can_sign(self, ac):
        assert ac.can(_u(Role.PHYSICIAN), Permission.SIGN_PHYSICIAN) is True

    def test_physician_cannot_sign_physics(self, ac):
        assert ac.can(_u(Role.PHYSICIAN), Permission.SIGN_PHYSICS) is False

    def test_admin_can_deliver(self, ac):
        assert ac.can(_u(Role.ADMIN), Permission.DELIVER) is True

    def test_admin_cannot_view_audit(self, ac):
        assert ac.can(_u(Role.ADMIN), Permission.VIEW_AUDIT) is False

    def test_auditor_can_view_audit(self, ac):
        assert ac.can(_u(Role.AUDITOR), Permission.VIEW_AUDIT) is True

    def test_auditor_cannot_edit(self, ac):
        assert ac.can(_u(Role.AUDITOR), Permission.EDIT_PLAN) is False

    def test_string_permission_accepted(self, ac):
        assert ac.can(_u(Role.ADMIN), "deliver") is True

    def test_unknown_permission_returns_false(self, ac):
        # can لا يرمي على صلاحية غريبة → False
        assert ac.can(_u(Role.ADMIN), "fly") is False


class TestRequire:
    def test_allowed_returns_true(self, ac):
        assert ac.require(_u(Role.ADMIN), Permission.DELIVER) is True

    def test_denied_raises(self, ac):
        with pytest.raises(PermissionDeniedError):
            ac.require(_u(Role.VIEWER), Permission.DELIVER)

    def test_denied_message_has_identity(self, ac):
        try:
            ac.require(_u(Role.VIEWER), Permission.EDIT_PLAN)
            assert False, "كان يجب أن يرمي"
        except PermissionDeniedError as e:
            msg = str(e)
            assert "id_viewer" in msg
            assert "viewer" in msg
            assert "edit_plan" in msg

    def test_unknown_permission_raises(self, ac):
        # require يرمي ValueError على صلاحية غريبة (ليس صامتاً كـ can)
        with pytest.raises(ValueError):
            ac.require(_u(Role.ADMIN), "fly")

    def test_is_permission_error_subclass(self, ac):
        # PermissionDeniedError يرث PermissionError (دلالي)
        with pytest.raises(PermissionError):
            ac.require(_u(Role.VIEWER), Permission.DELIVER)


class TestHasAllAny:
    def test_has_all_true(self, ac):
        assert ac.has_all(_u(Role.PHYSICIAN),
                          [Permission.VIEW_PLAN, Permission.SIGN_PHYSICIAN]) is True

    def test_has_all_false(self, ac):
        assert ac.has_all(_u(Role.PHYSICIAN),
                          [Permission.VIEW_PLAN, Permission.DELIVER]) is False

    def test_has_all_empty_true(self, ac):
        assert ac.has_all(_u(Role.VIEWER), []) is True

    def test_has_any_true(self, ac):
        assert ac.has_any(_u(Role.VIEWER),
                          [Permission.DELIVER, Permission.VIEW_PLAN]) is True

    def test_has_any_false(self, ac):
        assert ac.has_any(_u(Role.VIEWER),
                          [Permission.DELIVER, Permission.EDIT_PLAN]) is False

    def test_has_any_empty_false(self, ac):
        assert ac.has_any(_u(Role.VIEWER), []) is False


class TestStateless:
    def test_two_instances_independent(self):
        a = AccessControl()
        b = AccessControl()
        u = _u(Role.ADMIN)
        assert a.can(u, Permission.DELIVER) == b.can(u, Permission.DELIVER)
