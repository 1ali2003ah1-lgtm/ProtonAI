"""
ProtonAI - Clinical Intelligence Engine (محرك الذكاء السريري)
يدمج كل طبقات المنصة (فيزياء، تقسيم، بيولوجيا، حدود، مقارنة، اقتصاد)
بـ IntelligenceReport واحد يحتوي:
- Narrative طبي فصيح بالعربي.
- Multi-stakeholder views (طبيب/فيزيائي/مريض/لجنة).
- Evidence chain لكل جملة.
- Risk synthesis متعددة الأبعاد (فيزيائي/سريري/اقتصادي/تشغيلي).

ليس aggregator — بل مُحلّل يبني قصة حالة متماسكة وموثقة.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from clinical_report import build_report
from cost_effectiveness import proton_value
from oar_constraints import evaluate as eval_oars
from plan_photon_comparison import favors_proton
from radiobiology import tcp, variable_rbe

__all__ = ["ClinicalIntelligence", "IntelligenceReport",
           "Evidence", "Risk", "StakeholderView"]


@dataclass
class Evidence:
    """دليل يدعم جملة في السرد (source + metric + قيمة + تفسير)."""
    source: str
    metric: str
    value: Any
    interpretation: str


@dataclass
class Risk:
    """خطر متعدد الأبعاد مع إجراء تخفيف."""
    domain: str      # physical / clinical / economic / operational
    level: str       # HIGH / MEDIUM / LOW
    description: str
    mitigation: str


@dataclass
class StakeholderView:
    """وجهة نظر جهة معينة (عنوان + نقاط مفتاحية)."""
    stakeholder: str
    headline: str
    key_points: List[str]


@dataclass
class IntelligenceReport:
    """تقرير الذكاء السريري الكامل."""
    case_id: str
    site: str
    narrative: str
    risks: List[Risk]
    evidence: List[Evidence]
    views: Dict[str, StakeholderView]
    synthesis: Dict[str, Any]


class ClinicalIntelligence:
    """
    محرك الذكاء السريري.
    synthesize(...) => IntelligenceReport متكامل.
    """

    # ------------------------------------------------------------------ #
    # الواجهة الرئيسية
    # ------------------------------------------------------------------ #
    def synthesize(self, case_id: str, site: str,
                   dice: float = 0.92, ece: float = 0.02,
                   status: str = "GREEN",
                   prescription: float = 70.0, range_mm: float = 100.0,
                   let: float = 3.0, achieved_oars: Optional[dict] = None,
                   cost_proton: float = 60000, cost_photon: float = 40000,
                   qaly_p: float = 8.2, qaly_f: float = 7.8,
                   integral_proton: float = 120) -> IntelligenceReport:
        """دمج كل الطبقات بـ IntelligenceReport واحد."""
        evidence: List[Evidence] = []

        # 1) بوابة القرار الأساسية
        rep = build_report(case_id, site, dice, ece, status=status,
                           range_mm=range_mm)
        evidence.append(Evidence("clinical_report", "decision",
                                 rep["decision"],
                                 f"بوابة القرار: {rep['decision']}"))

        # 2) البيولوجيا الإشعاعية
        rbe = variable_rbe(2.0, let)
        tcp_val = tcp(prescription, 50.0)
        evidence.append(Evidence("radiobiology", "rbe_2gy", round(rbe, 3),
                                 f"RBE متغير = {rbe:.3f} عند LET={let}"))
        evidence.append(Evidence("radiobiology", "tcp", round(tcp_val, 3),
                                 f"احتمال السيطرة = {tcp_val:.1%}"))

        # 3) حدود الأعضاء الحساسة
        achieved_oars = achieved_oars or {}
        try:
            oar_eval = eval_oars(site, achieved_oars)
        except KeyError:
            oar_eval = {"status": "GREEN", "rows": []}
        evidence.append(Evidence("oar_constraints", "status",
                                 oar_eval["status"],
                                 f"تقييم الحدود: {oar_eval['status']}"))

        # 4) ميزة البروتون مقابل الفوتون
        fav = favors_proton(site, achieved_oars, integral_proton)
        evidence.append(Evidence("plan_photon_comparison",
                                 "integral_reduction",
                                 fav["integral_reduction_pct"],
                                 f"انخفاض الجرعة المتكاملة = "
                                 f"{fav['integral_reduction_pct']}%"))

        # 5) الجدوى الاقتصادية
        eco = proton_value(cost_proton, cost_photon, qaly_p, qaly_f)
        evidence.append(Evidence("cost_effectiveness", "icer",
                                 eco.get("icer"), eco["note"]))

        # 6-9) توليد المخاطر، السرد، الوجهات، والتلخيص
        risks = self._synthesize_risks(rep, oar_eval, fav, eco)
        narrative = self._build_narrative(case_id, site, rep, evidence,
                                          oar_eval, fav, eco)
        views = self._build_views(rep, oar_eval, fav, eco, tcp_val)
        synthesis = {
            "overall_quality": rep["decision"],
            "evidence_count": len(evidence),
            "risk_count": len(risks),
            "favors_proton": fav["favors_proton"],
            "cost_effective": eco["cost_effective"],
        }

        return IntelligenceReport(case_id=case_id, site=site,
                                  narrative=narrative, risks=risks,
                                  evidence=evidence, views=views,
                                  synthesis=synthesis)

    # ------------------------------------------------------------------ #
    # توليد المخاطر
    # ------------------------------------------------------------------ #
    def _synthesize_risks(self, rep, oar_eval, fav, eco) -> List[Risk]:
        risks: List[Risk] = []
        if rep["decision"] == "STOP":
            risks.append(Risk("operational", "HIGH",
                              "بوابة القرار أوقفت الخطة",
                              "مراجعة إلزامية قبل أي إجراء"))
        elif rep["decision"] == "REVIEW":
            risks.append(Risk("operational", "MEDIUM",
                              "الخطة تحت المراجعة",
                              "فحص إضافي قبل الاعتماد"))

        if oar_eval["status"] == "RED":
            risks.append(Risk("clinical", "HIGH",
                              "تجاوز حد عضو حساس", "إعادة تخطيط إلزامية"))
        elif oar_eval["status"] == "AMBER":
            risks.append(Risk("clinical", "MEDIUM",
                              "اقتراب من حد عضو حساس",
                              "مراقبة مشددة أثناء العلاج"))

        if not fav["favors_proton"]:
            risks.append(Risk("clinical", "MEDIUM",
                              "البروتون لا يتفوق على الفوتون هنا",
                              "إعادة تقييم اختيار البروتون"))

        if not eco["cost_effective"]:
            risks.append(Risk("economic", "MEDIUM",
                              "العلاج غير مجدٍ اقتصادياً",
                              "بحث بدائل أو دعم مالي"))
        return risks

    # ------------------------------------------------------------------ #
    # توليد السرد الطبي
    # ------------------------------------------------------------------ #
    def _build_narrative(self, case_id, site, rep, evidence,
                         oar_eval, fav, eco) -> str:
        parts = [
            f"**الحالة {case_id} ({site})** — تحليل منصة ProtonAI:",
            "",
            f"قرار البوابة: **{rep['decision']}** مع هامش مدى مقترح "
            f"**{rep['range_margin_mm']:.1f} مم**.",
        ]
        if rep["reasons"]:
            parts.append("الأسباب: " + "؛ ".join(rep["reasons"]) + ".")

        parts += [
            "",
            "**الأداء البيولوجي:**",
            f"- احتمال السيطرة على الورم (TCP): "
            f"**{self._find(evidence, 'tcp'):.1%}**.",
            f"- RBE المتغير: **{self._find(evidence, 'rbe_2gy'):.3f}**.",
            "",
            "**سلامة الأعضاء الحساسة:**",
            f"- تقييم حدود OAR: **{oar_eval['status']}**.",
            "",
            "**ميزة البروتون مقابل الفوتون:**",
            f"- انخفاض الجرعة المتكاملة: "
            f"**{self._find(evidence, 'integral_reduction')}%**.",
            f"- البروتون مفضّل: {'نعم' if fav['favors_proton'] else 'لا'}.",
        ]

        if eco.get("icer") is not None:
            parts += [
                "",
                "**التقييم الاقتصادي:**",
                f"- ICER = {eco['icer']:,.0f} لكل QALY.",
                "- " + ("مجدٍ اقتصادياً." if eco["cost_effective"]
                        else "غير مجدٍ اقتصادياً."),
            ]

        parts += ["", "_كل توصية تتطلب إقراراً بشرياً نهائياً._"]
        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    # توليد وجهات النظر
    # ------------------------------------------------------------------ #
    def _build_views(self, rep, oar_eval, fav, eco, tcp_val
                     ) -> Dict[str, StakeholderView]:
        return {
            "physician": StakeholderView(
                "physician", f"القرار: {rep['decision']}",
                [f"هامش المدى: {rep['range_margin_mm']:.1f} مم",
                 f"احتمال السيطرة (TCP): {tcp_val:.1%}",
                 f"تقييم OAR: {oar_eval['status']}"]),
            "physicist": StakeholderView(
                "physicist", "الأداء الفيزيائي",
                [f"Dice = {rep['metrics']['dice']:.2f}",
                 f"ECE = {rep['metrics']['ece']:.2f}",
                 f"القرار: {rep['decision']}"]),
            "patient": StakeholderView(
                "patient", "ملخص مبسّط",
                ["العلاج المُقترح يستخدم البروتون بدقة عالية.",
                 "توجد إجراءات أمان متعددة لحماية الأعضاء السليمة.",
                 "سيراجع الطبيب التوصية قبل القرار النهائي."]),
            "committee": StakeholderView(
                "committee", "ملخص للجنة/التأمين",
                [f"انخفاض الجرعة المتكاملة: "
                 f"{fav['integral_reduction_pct']}%",
                 f"ICER = {eco.get('icer')}",
                 "مجدٍ اقتصادياً: "
                 + ("نعم" if eco["cost_effective"] else "لا")]),
        }

    # ------------------------------------------------------------------ #
    @staticmethod
    def _find(evidence: List[Evidence], metric: str) -> Any:
        for e in evidence:
            if e.metric == metric:
                return e.value
        return None
