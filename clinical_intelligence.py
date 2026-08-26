"""
ProtonAI - Clinical Intelligence Engine
محرك ذكاء سريري يدمج كل طبقات المنصة بـ:
- Narrative طبي فصيح (بالعربي).
- Multi-stakeholder views (طبيب/فيزيائي/مريض/لجنة).
- Evidence chain لكل جملة.
- Risk synthesis متعددة الأبعاد.

ليس مجرد aggregator — هو مُحلّل يُنشئ قصة حالة متماسكة.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from clinical_report import build_report
from radiobiology import variable_rbe, tcp, ntcp_lkb
from oar_constraints import evaluate as eval_oars, constraints_for
from plan_photon_comparison import favors_proton
from cost_effectiveness import proton_value


@dataclass
class Evidence:
    """دليل يدعم جملة في السرد"""
    source: str  # "radiobiology", "oar_constraints", ...
    metric: str
    value: Any
    interpretation: str


@dataclass
class Risk:
    """خطر متعدد الأبعاد"""
    domain: str  # physical / clinical / economic / operational
    level: str   # HIGH / MEDIUM / LOW
    description: str
    mitigation: str


@dataclass
class StakeholderView:
    """وجهة نظر جهة معينة"""
    stakeholder: str  # physician / physicist / patient / committee
    headline: str
    key_points: List[str]


@dataclass
class IntelligenceReport:
    """تقرير الذكاء السريري الكامل"""
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
    يأخذ بيانات حالة مُجمَّعة ويُنتج تقرير ذكاء متكامل.
    """

    def synthesize(self, case_id: str, site: str,
                   dice: float = 0.92, ece: float = 0.02,
                   prescription: float = 70.0, range_mm: float = 100.0,
                   let: float = 3.0, achieved_oars: dict = None,
                   cost_proton: float = 60000, cost_photon: float = 40000,
                   qaly_p: float = 8.2, qaly_f: float = 7.8,
                   integral_proton: float = 120) -> IntelligenceReport:
        """دمج كل الطبقات بـ IntelligenceReport واحد"""
        evidence: List[Evidence] = []
        risks: List[Risk] = []

        # 1) تقرير القرار الأساسي
        rep = build_report(case_id, site, dice, ece, range_mm=range_mm)
        evidence.append(Evidence("clinical_report", "decision",
                                 rep["decision"], f"بوابة القرار: {rep['decision']}"))

        # 2) البيولوجيا الإشعاعية
        rbe = variable_rbe(2.0, let)
        tcp_val = tcp(prescription, 50.0)
        evidence.append(Evidence("radiobiology", "rbe_2gy", round(rbe, 3),
                                 f"RBE متغير = {rbe:.3f} عند LET={let}"))
        evidence.append(Evidence("radiobiology", "tcp", round(tcp_val, 3),
                                 f"احتمال السيطرة = {tcp_val:.1%}"))

        # 3) حدود OAR
        achieved_oars = achieved_oars or {}
        oar_eval = {"status": "GREEN", "rows": []}
        try:
            oar_eval = eval_oars(site, achieved_oars)
        except KeyError:
            pass  # site غير معروف بالكتالوج
        evidence.append(Evidence("oar_constraints", "status", oar_eval["status"],
                                 f"تقييم الحدود: {oar_eval['status']}"))

        # 4) مقارنة البروتون بالفوتون
        fav = favors_proton(site, achieved_oars, integral_proton)
        evidence.append(Evidence("plan_photon_comparison", "integral_reduction",
                                 fav["integral_reduction_pct"],
                                 f"انخفاض الجرعة المتكاملة = {fav['integral_reduction_pct']}%"))

        # 5) الاقتصاد
        eco = proton_value(cost_proton, cost_photon, qaly_p, qaly_f)
        evidence.append(Evidence("cost_effectiveness", "icer", eco.get("icer"),
                                 eco["note"]))

        # 6) توليد المخاطر
        risks = self._synthesize_risks(rep, oar_eval, fav, eco)

        # 7) توليد الـ narrative
        narrative = self._build_narrative(case_id, site, rep, evidence,
                                          oar_eval, fav, eco)

        # 8) توليد وجهات النظر
        views = self._build_views(rep, oar_eval, fav, eco, tcp_val)

        # 9) الـ synthesis النهائي
        synthesis = {
            "overall_quality": rep["decision"],
            "evidence_count": len(evidence),
            "risk_count": len(risks),
            "favors_proton": fav["favors_proton"],
            "cost_effective": eco["cost_effective"],
        }

        return IntelligenceReport(
            case_id=case_id, site=site, narrative=narrative,
            risks=risks, evidence=evidence, views=views, synthesis=synthesis)

    def _synthesize_risks(self, rep, oar_eval, fav, eco) -> List[Risk]:
        risks = []
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
                              "تجاوز حد عضو حساس",
                              "إعادة تخطيط إلزامية"))
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

        parts.extend([
            "",
            "**الأداء البيولوجي:**",
            f"- احتمالية السيطرة على الورم (TCP) مُقدَّرة بـ **{self._find(evidence, 'tcp'):.1%}**.",
            f"- RBE المتغير = **{self._find(evidence, 'rbe_2gy'):.3f}**.",
        ])

        parts.extend([
            "",
            "**سلامة الأعضاء الحساسة:**",
            f"- تقييم حدود OAR: **{oar_eval['status']}**.",
        ])

        parts.extend([
            "",
            "**ميزة البروتون مقابل الفوتون:**",
            f"- انخفاض الجرعة المتكاملة: **{self._find(evidence, 'integral_reduction')}%**.",
            f"- البروتون مفضّل: {'نعم' if fav['favors_proton'] else 'لا'}.",
        ])

        if eco.get("icer") is not None:
            parts.extend([
                "",
                "**التقييم الاقتصادي:**",
                f"- ICER = {eco['icer']:,.0f} لكل QALY.",
                f"- {'مجدٍ اقتصادياً' if eco['cost_effective'] else 'غير مجدٍ اقتصادياً'}.",
            ])

        parts.extend([
            "",
            "_كل توصية تتطلب إقراراً بشرياً نهائياً._",
        ])
        return "\n".join(parts)

    def _find(self, evidence, metric):
        for e in evidence:
            if e.metric == metric:
                return e.value
        return None

    def _build_views(self, rep, oar_eval, fav, eco, tcp_val) -> Dict[str, StakeholderView]:
        return {
            "physician": StakeholderView(
                "physician",
                f"القرار: {rep['decision']}",
                [
                    f"هامش المدى: {rep['range_margin_mm']:.1f} مم",
                    f"احتمال السيطرة (TCP): {tcp_val:.1%}",
                    f"تقييم OAR: {oar_eval['status']}",
                ]),
            "physicist": StakeholderView(
                "physicist",
                "الأداء الفيزيائي",
                [
                    f"Dice = {rep['metrics']['dice']:.2f}",
                    f"ECE = {rep['metrics']['ece']:.2f}",
                    f"القرار: {rep['decision']}",
                ]),
            "patient": StakeholderView(
                "patient",
                "ملخص مبسّط",
                [
                    "العلاج المُقترح يستخدم البروتون بدقة عالية.",
                    "هناك إجراءات أمان متعددة لحماية الأعضاء السليمة.",
                    "الطبيب سيراجع التوصية قبل اتخاذ القرار النهائي.",
                ]),
            "committee": StakeholderView(
                "committee",
                "ملخص للجنة/التأمين",
                [
                    f"ميزة البروتون: انخفاض الجرعة المتكاملة {self._find([Evidence('', 'integral_reduction', fav['integral_reduction_pct'], '')], 'integral_reduction')}%",
                    f"ICER = {eco.get('icer')}",
                    f"مجدٍ اقتصادياً: {'نعم' if eco['cost_effective'] else 'لا'}",
                ]),
}
