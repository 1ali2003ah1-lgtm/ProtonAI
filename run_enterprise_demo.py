"""
ProtonAI - Stage-7 Enterprise Demo
المايسترو المؤسسي: سيناريو كامل يربط RBAC + audit + gates + monitoring + FHIR + adapters
يولّد الرفض/التجاوز عمداً ليثبت أن المراقبة تكتشف المشاكل، لا فقط تعمل
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from access_control import (
    AccessControl, User, Role, Permission, PermissionDeniedError,
)
from audit_trails import EnterpriseAuditTrail
from approval_gates import ApprovalGate, SeparationOfDutiesError
from monitoring import Monitoring
from integration_adapters import IntegrationHub, InMemoryIntegrationAdapter
from treatment_plan import TreatmentPlan
from decision_model import DecisionRecord, Recommendation

logger = logging.getLogger("ProtonAI.EnterpriseDemo")


def _build_plan() -> TreatmentPlan:
    """خطة تجريبية ببيانات تصوير/فيزياء للنشر عبر FHIR"""
    p = TreatmentPlan("plan_demo", "anon_demo")
    p.set_section("imaging", {"modality": "CT", "slices": 120})
    p.set_section("physics", {"gamma_pass_rate": 0.97, "coverage_drop": 0.02})
    return p


def _decision(rec: str, override: bool = False) -> DecisionRecord:
    return DecisionRecord(
        recommendation=Recommendation(rec), recommendation_reason="r",
        can_deliver=True, delivery_blockers=[], overall_status="GREEN",
        physician_signed=True, physics_signed=True, override=override)


def run_enterprise_demo(output_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    """تشغيل السيناريو المؤسسي الكامل، يرجع قاموساً شاملاً + يحفظ إن طُلب"""
    # 1) المستخدمون بالأدوار
    admin1 = User("admin1", Role.ADMIN)
    admin2 = User("admin2", Role.ADMIN)
    phys = User("phys1", Role.PHYSICIAN)
    physicist = User("phys2", Role.PHYSICIST)
    auditor = User("aud1", Role.AUDITOR)
    viewer = User("view1", Role.VIEWER)

    # 2) البنية المؤسسية
    ac = AccessControl()
    ea = EnterpriseAuditTrail(access=ac)
    gate = ApprovalGate(access=ac, audit=ea)
    hub = IntegrationHub()
    hub.register(InMemoryIntegrationAdapter("pacs"))
    hub.register(InMemoryIntegrationAdapter("his"))

    # 3) محاولات وصول مرفوعة (تُسجّل DENIED عمداً)
    denied = 0
    try:
        ac.require(viewer, Permission.DELIVER)
    except PermissionDeniedError:
        ea.log_denied(viewer, "deliver"); denied += 1
    try:
        ac.require(admin1, Permission.VIEW_AUDIT)  # فصل مهام: الإداري ما يشوف التدقيق
    except PermissionDeniedError:
        ea.log_denied(admin1, "view_audit"); denied += 1

    # 4) توقيع سريري + فيزيائي
    ea.log_action(phys, "sign_physician", "plan_demo")
    ea.log_action(physicist, "sign_physics", "plan_demo")

    # 5) تغيير حسّاس بـ maker-checker + محاولة اعتماد ذاتي تُرفض
    cr = gate.propose(admin1, "threshold", "رفع عتبة gamma")
    separation_blocked = False
    try:
        gate.approve(admin1, cr.request_id)  # نفس المُنشئ → مرفوض
    except SeparationOfDutiesError:
        separation_blocked = True
    gate.approve(admin2, cr.request_id)  # عين ثانية → معتمد

    # 6) تسليم إداري
    ea.log_action(admin1, "deliver", "plan_demo")

    # 7) المدقق المستقل يشوف ويصدّر
    audit_events = ea.view_events(auditor)

    # 8) نشر الخطة عبر FHIR لـ PACS/HIS
    pub = hub.publish(_build_plan())

    # 9) المراقبة التشغيلية + تنبيهات
    mon = Monitoring()
    mon.add_audit(ea.records)
    mon.add_decisions([_decision("approve"), _decision("approve", override=True)])
    mon.add_overalls(["GREEN", "GREEN", "RED"])
    mon.add_states(["delivered", "rejected"])
    summary = mon.summary()
    markdown = mon.to_markdown()

    result = {
        "users": {u.user_id: u.role.value for u in
                  (admin1, admin2, phys, physicist, auditor, viewer)},
        "audit_count": ea.count,
        "denied_count": denied,
        "gate": {"request_id": cr.request_id, "status": cr.status.value,
                 "separation_blocked": separation_blocked,
                 "decided_by": cr.decided_by},
        "fhir": {"acks": pub["acks"], "entries": len(pub["bundle"]["entry"])},
        "monitoring": summary,
        "monitoring_markdown": markdown,
    }

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "enterprise_monitoring.md").write_text(markdown, encoding="utf-8")
        ea.export_jsonl(auditor, out / "enterprise_audit.jsonl")
        with open(out / "fhir_bundle.json", "w", encoding="utf-8") as f:
            json.dump(pub["bundle"], f, ensure_ascii=False, indent=2)
        logger.info(f"تم حفظ الديمو المؤسسي في: {out}")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    r = run_enterprise_demo()
    print("المستخدمون:", r["users"])
    print("محاولات مرفوضة:", r["denied_count"])
    print("البوابة:", r["gate"])
    print("إيصالات FHIR:", list(r["fhir"]["acks"]))
    print("تنبيهات المراقبة:", len(r["monitoring"]["alerts"]))
