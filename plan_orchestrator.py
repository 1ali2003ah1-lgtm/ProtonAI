"""
ProtonAI - Plan Orchestrator
المايسترو المنسّق: يشغّل كل مراحل دعم القرار بترتيب واحد
providers (مزوّدو البيانات) محقونون → ملء الخطة ← تقييم ← توصية ← حركة حالة ← لوحة
منسّق خفيف: لا يستورد الفيزياء/التصوير الثقيلة، ينسّق وحدات المرحلة 6 فقط
الحركة التلقائية تصل READY؛ التسليم (DELIVERED) يحتاج قرار متخصص صريح
"""

import logging
from typing import Dict, Any, Optional, Callable, List

from treatment_plan import TreatmentPlan, new_plan_id, SECTIONS
from quality_indicators import QualityIndicators
from decision_model import DecisionModel
from clinical_dashboard import ClinicalDashboard
from plan_state_machine import PlanStateMachine, PlanState, build_context

logger = logging.getLogger("ProtonAI.PlanOrchestrator")

# مسار الحركة التلقائية (الترتيب السريري الثابت)
_AUTO_PATH = [PlanState.PHYSICS_REVIEW, PlanState.PHYSICIAN_REVIEW,
              PlanState.READY, PlanState.DELIVERED]


class PlanOrchestrator:
    """
    منسّق سير العمل.
    - run: ملء ← تقييم ← توصية ← (قرار متخصص اختياري) ← حركة ← لوحة.
    - providers: {"imaging": fn, "physics": fn, ...} كل fn(plan)->dict.
    - auto_advance: يمشي الخطة لأقصى حالة مسموحة (READY عادة، DELIVERED بـ approve).
    - يرجع قاموساً شاملاً: plan/evaluation/decision/dashboard/state/تقارير.
    """

    def __init__(
        self,
        quality: Optional[QualityIndicators] = None,
        decision_model: Optional[DecisionModel] = None,
        dashboard: Optional[ClinicalDashboard] = None,
    ):
        self.quality = quality if quality is not None else QualityIndicators()
        self.decision = (decision_model if decision_model is not None
                         else DecisionModel(self.quality))
        self.dashboard = (dashboard if dashboard is not None
                          else ClinicalDashboard(self.quality))

    def _fill_sections(
        self, plan: TreatmentPlan, providers: Dict[str, Callable]
    ) -> List[str]:
        """ملء الأقسام من المزوّدين، يرجع أسماء الأقسام الممتلئة فعلياً"""
        filled: List[str] = []
        for section in SECTIONS:
            if section in providers:
                data = providers[section](plan)  # يرمي إن رمى المزوّد (لا نخفي)
                plan.set_section(section, data)  # يتحقق من النوع (dict)
                if plan.section_filled(section):
                    filled.append(section)
        return filled

    def _auto_advance(self, sm: PlanStateMachine, ctx: Dict[str, Any]) -> None:
        """يمشي الخطة لأقصى حالة مسموحة؛ يتوقف عند أول حرس فاشل"""
        for target in _AUTO_PATH:
            if sm.can_transition(target, ctx):
                sm.transition(target, ctx)
            else:
                break

    def run(
        self,
        plan: Optional[TreatmentPlan] = None,
        providers: Optional[Dict[str, Callable]] = None,
        patient_id: str = "anonymous",
        physician_signed: bool = False,
        physics_signed: bool = False,
        specialist_decision: Optional[str] = None,
        specialist_id: Optional[str] = None,
        specialist_notes: str = "",
        auto_advance: bool = True,
        comparison: Optional[Dict[str, Any]] = None,
        title: str = "ProtonAI Clinical Dashboard",
    ) -> Dict[str, Any]:
        """تشغيل سير العمل الكامل، يرجع قاموساً شاملاً"""
        providers = dict(providers) if providers else {}

        # 1) الخطة (تُبنى لو غابت)
        if plan is None:
            plan = TreatmentPlan(new_plan_id(), str(patient_id))

        # 2) ملء الأقسام من المزوّدين
        filled = self._fill_sections(plan, providers)

        # 3) تقييم الجودة + التوصية
        evaluation = self.quality.evaluate_plan(plan)
        decision = self.decision.recommend(
            evaluation, physician_signed=physician_signed,
            physics_signed=physics_signed)

        # 4) قرار المتخصص الصريح (اختياري؛ التسليم يحتاجه)
        if specialist_decision is not None:
            if not str(specialist_id or "").strip():
                raise ValueError("specialist_id مطلوب عند تمرير specialist_decision")
            self.decision.record_specialist_decision(
                decision, specialist_decision, str(specialist_id), specialist_notes)

        # 5) اللوحة (تجمع كل شي)
        dashboard_model = self.dashboard.build(
            plan=plan, evaluation=evaluation, decision=decision,
            comparison=comparison, title=title)

        # 6) آلة الحالات + الحركة التلقائية
        ctx = build_context(plan=plan, evaluation=evaluation, decision=decision)
        sm = PlanStateMachine()
        if auto_advance:
            self._auto_advance(sm, ctx)

        # 7) التقارير الجاهزة
        markdown = self.dashboard.to_markdown(dashboard_model)
        html = self.dashboard.to_html(dashboard_model)

        logger.info(f"orchestrator: state={sm.state.value}, "
                    f"sections_filled={filled}, overall={evaluation['overall'].name}")
        return {
            "plan": plan,
            "evaluation": evaluation,
            "decision": decision,
            "dashboard": dashboard_model,
            "state": sm.state.value,
            "state_history": list(sm.history),
            "sections_filled": filled,
            "providers_used": list(providers.keys()),
            "report_markdown": markdown,
            "report_html": html,
}
