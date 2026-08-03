"""
ProtonAI - Enterprise Audit Trails
تدقيق مؤسسي بطبقتين: دفتر مشفّر مقاوم للتلاعب (audit.AuditTrail)
+ إسقاط مقروء يربط كل عملية بـ "مين عملها بأي دور"
فصل المهام على القراءة: فقط AUDITOR يشوف/يصدّر السجل الكامل
تصدير مؤسسي: JSON Lines + CSV
"""

import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from audit import AuditTrail
from access_control import AccessControl, User, Permission

logger = logging.getLogger("ProtonAI.EnterpriseAudit")

# أعمدة CSV ثابتة (ترتيب مؤسسي واضح)
_CSV_FIELDS = ["seq", "timestamp", "user_id", "role",
               "action", "target", "outcome", "details"]


class EnterpriseAuditTrail:
    """
    تدقيق مؤسسي.
    - log_action: يسجّل عملية مربوطة بالمستخدم/الدور (بالطبقتين).
    - view_events: يعرض الإسقاط المقروء (يتطلب VIEW_AUDIT).
    - export_jsonl / export_csv: تصدير مؤسسي (يتطلب EXPORT_AUDIT).
    - verify: سلامة سلسلة الهاش (من الدفتر المشفّر).
    """

    def __init__(
        self,
        audit: Optional[AuditTrail] = None,
        access: Optional[AccessControl] = None,
    ):
        self.audit = audit if audit is not None else AuditTrail()
        self.access = access if access is not None else AccessControl()
        self.records: List[Dict[str, Any]] = []  # الإسقاط المقروء

    def log_action(
        self,
        user: User,
        action: str,
        target: str = "",
        outcome: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """تسجيل عملية مربوطة بالمستخدم/الدور (بالطبقتين معاً)"""
        merged = dict(details or {})
        merged["user_id"] = user.user_id
        merged["role"] = user.role.value
        record = {
            "seq": len(self.records),
            "timestamp": datetime.now().isoformat(),
            "user_id": user.user_id,
            "role": user.role.value,
            "action": str(action),
            "target": str(target),
            "outcome": str(outcome),
            "details": merged,
        }
        self.records.append(record)
        # الدفتر المشفّر (سلسلة الهاش) — نفس العملية للأمان
        try:
            self.audit.log("enterprise", str(action), str(target),
                           str(outcome), merged)
        except Exception:  # لا نكسر الإسقاط لو تغيّرت واجهة الدفتر
            logger.warning("تعذّر التسجيل بالدفتر المشفّر، الإسقاط فقط")
        return record

    def log_denied(self, user: User, action: str, target: str = "") -> Dict[str, Any]:
        """تسجيل محاولة وصول مرفوضة (للتدقيق الأمني)"""
        return self.log_action(user, action, target, outcome="DENIED")

    @property
    def count(self) -> int:
        """عدد السجلات"""
        return len(self.records)

    def view_events(self, user: User) -> List[Dict[str, Any]]:
        """عرض الإسقاط المقروء (فصل مهام: VIEW_AUDIT فقط)"""
        self.access.require(user, Permission.VIEW_AUDIT)
        return [dict(r) for r in self.records]  # نسخ، لا مراجع

    def export_jsonl(self, user: User, path) -> Path:
        """تصدير JSON Lines (سجل لكل سطر) — يتطلب EXPORT_AUDIT"""
        self.access.require(user, Permission.EXPORT_AUDIT)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for r in self.records:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        logger.info(f"تم تصدير JSONL ({len(self.records)}) إلى: {path}")
        return path

    def export_csv(self, user: User, path) -> Path:
        """تصدير CSV بأعمدة ثابتة — يتطلب EXPORT_AUDIT"""
        self.access.require(user, Permission.EXPORT_AUDIT)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
            writer.writeheader()
            for r in self.records:
                row = dict(r)
                row["details"] = json.dumps(row.get("details", {}),
                                            ensure_ascii=False, default=str)
                writer.writerow(row)
        logger.info(f"تم تصدير CSV ({len(self.records)}) إلى: {path}")
        return path

    def verify(self) -> bool:
        """سلامة سلسلة الهاش بالدفتر المشفّر"""
        return self.audit.verify_chain()
