"""
ProtonAI - Access Control (RBAC)
التحكم بالوصول حسب الدور: أدوار + صلاحيات + فصل مهام (separation of duties)
الأساس لكل الجاهزية المؤسسية: كل عملية تسأل "مين؟ بأي دور؟ هل يجوز له؟"
مبدأان: least privilege (الحد الأدنى) + separation of duties (المدقق ≠ المشغّل)
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Iterable, Set, Union

logger = logging.getLogger("ProtonAI.AccessControl")


class Role(str, Enum):
    """الأدوار المؤسسية"""
    VIEWER = "viewer"        # مشاهدة فقط
    PHYSICIAN = "physician"  # طبيب: يوصي ويوقّع سريرياً
    PHYSICIST = "physicist"  # فيزيائي: يوقّع فيزيائياً ويشغّل QA
    ADMIN = "admin"          # إداري: يشغّل ويسلّم ويدير (بلا تدقيق حسّاس)
    AUDITOR = "auditor"      # مدقق: يقرأ السجلات فقط (بلا تعديل/تسليم)


class Permission(str, Enum):
    """الصلاحيات الذرية"""
    VIEW_PLAN = "view_plan"
    VIEW_DASHBOARD = "view_dashboard"
    EDIT_PLAN = "edit_plan"
    EDIT_PHYSICS = "edit_physics"
    SIGN_PHYSICIAN = "sign_physician"
    SIGN_PHYSICS = "sign_physics"
    RECOMMEND = "recommend"
    DELIVER = "deliver"
    REJECT = "reject"
    MANAGE_USERS = "manage_users"
    CHANGE_CONFIG = "change_config"
    VIEW_AUDIT = "view_audit"
    EXPORT_AUDIT = "export_audit"
    EXPORT_FHIR = "export_fhir"
    RUN_QA = "run_qa"


# خريطة الدور → صلاحياته (مبنية بمبدأي least privilege + separation of duties)
_V = {Permission.VIEW_PLAN, Permission.VIEW_DASHBOARD}
ROLE_PERMISSIONS = {
    Role.VIEWER: set(_V),
    Role.PHYSICIAN: set(_V) | {Permission.EDIT_PLAN, Permission.SIGN_PHYSICIAN,
                               Permission.RECOMMEND},
    Role.PHYSICIST: set(_V) | {Permission.EDIT_PHYSICS, Permission.SIGN_PHYSICS,
                               Permission.RUN_QA},
    # ADMIN يشغّل ويسلّم ويدير، لكن لا يرى سجل التدقيق الحسّاس (separation)
    Role.ADMIN: set(_V) | {Permission.EDIT_PLAN, Permission.EDIT_PHYSICS,
                           Permission.SIGN_PHYSICIAN, Permission.SIGN_PHYSICS,
                           Permission.RECOMMEND, Permission.DELIVER, Permission.REJECT,
                           Permission.MANAGE_USERS, Permission.CHANGE_CONFIG,
                           Permission.EXPORT_FHIR},
    # AUDITOR يقرأ/يدقّق فقط، لا يعدّل ولا يسلّم (separation)
    Role.AUDITOR: {Permission.VIEW_PLAN, Permission.VIEW_DASHBOARD,
                   Permission.VIEW_AUDIT, Permission.EXPORT_AUDIT},
}

# كل الصلاحيات (اتحاد الأدوار) — لفحص عدم وجود صلاحية يتيمة
ALL_PERMISSIONS: Set[Permission] = set().union(*ROLE_PERMISSIONS.values())


class PermissionDeniedError(PermissionError):
    """محاولة وصول مرفوضة (تُرفع بـ require)"""


def _perm(value: Union[Permission, str]) -> Permission:
    """تحويل آمن للصلاحية (يرمي ValueError لو غريبة)"""
    if isinstance(value, Permission):
        return value
    return Permission(str(value))  # ValueError تلقائياً لو غير موجودة


@dataclass(frozen=True)
class User:
    """مستخدم مؤسسي (immutable: الدور لا يتغيّر بعد الإنشاء)"""
    user_id: str
    role: Role
    name: str = ""

    def __post_init__(self):
        if not str(self.user_id).strip():
            raise ValueError("user_id لا يمكن أن يكون فارغاً")
        # قبول str للدور وتوحيده (يرمي ValueError لو دور غريب)
        if not isinstance(self.role, Role):
            object.__setattr__(self, "role", Role(str(self.role)))

    @property
    def permissions(self) -> Set[Permission]:
        """صلاحيات الدور (نسخة، لا تُعدّل الخريطة الأصلية)"""
        return set(ROLE_PERMISSIONS[self.role])


class AccessControl:
    """
    محرّك RBAC.
    - can: هل للمستخدم الصلاحية؟ (bool، لا يرمي).
    - require: يؤكد الصلاحية، يرمي PermissionDeniedError إن رُفضت.
    - has_all / has_any: فحص مجموعة صلاحيات.
    لا حالة داخلية (stateless) → آمن ومتكرر.
    """

    def can(self, user: User, permission: Union[Permission, str]) -> bool:
        """هل للمستخدم الصلاحية؟"""
        try:
            p = _perm(permission)
        except ValueError:
            return False
        return p in user.permissions

    def require(self, user: User, permission: Union[Permission, str]) -> bool:
        """يؤكد الصلاحية، يرمي إن رُفضت (رسالة فيها الهوية للتدقيق)"""
        p = _perm(permission)  # ValueError لو غريبة (مقصود)
        if p not in user.permissions:
            logger.warning(f"رفض وصول: user={user.user_id} role={user.role.value} "
                           f"permission={p.value}")
            raise PermissionDeniedError(
                f"المستخدم '{user.user_id}' بدور '{user.role.value}' "
                f"لا يملك صلاحية '{p.value}'")
        return True

    def has_all(self, user: User, permissions: Iterable[Union[Permission, str]]) -> bool:
        """هل يملك كل الصلاحيات؟"""
        return all(self.can(user, p) for p in permissions)

    def has_any(self, user: User, permissions: Iterable[Union[Permission, str]]) -> bool:
        """هل يملك واحدة على الأقل؟"""
        return any(self.can(user, p) for p in permissions)
