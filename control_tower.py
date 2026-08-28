"""
ProtonAI - Autonomous Control Tower (برج المراقبة الذاتي)
طبقة حوكمة ذاتية تفحص المنظومة كاملة بدورة واحدة:
- فيزياء الأسطول (fleet_qa) • انجراف النموذج (drift) •
  سلامة السجلات (forensics) • أداء الـ cohort (analytics).
تُنتج GovernanceReport: وضعية عامة RAG + تنبيهات مُصعَّدة + سرد تنفيذي.
قاعدة: أي HIGH ⇒ RED؛ أي MEDIUM ⇒ AMBER؛ وإلا GREEN.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from cohort_analytics import analyze
from dossier_verify import verify_dossier
from physics_qa import fleet_qa

SEV = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
RAG_OF_SEV = {2: "RED", 1: "AMBER", 0: "GREEN"}


@dataclass
class Alert:
    domain: str       # physical / operational / integrity / clinical
    severity: str     # HIGH / MEDIUM / LOW
    message: str
    action: str


@dataclass
class GovernanceReport:
    posture: str
    alerts: List[Alert] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    summary: str = ""


class ControlTower:
    """دورة فحص ذاتية واحدة => GovernanceReport"""

    def run_cycle(self, scanners: Dict[str, List[float]],
                  drift_status: str, dossiers: list,
                  stop_rate_threshold: float = 0.3) -> GovernanceReport:
        alerts: List[Alert] = []

        # 1) فيزياء الأسطول
        fq = fleet_qa(scanners)
        if fq["overall"] == "RED":
            alerts.append(Alert("physical", "HIGH",
                                f"انحراف معايرة حرج: {fq['flagged']}",
                                "إيقاف السريرات المتأثرة وإعادة معايرة"))
        elif fq["overall"] == "AMBER":
            alerts.append(Alert("physical", "MEDIUM",
                                f"انحراف معايرة متزايد: {fq['flagged']}",
                                "جدولة إعادة معايرة خلال 48 ساعة"))

        # 2) انجراف النموذج
        if drift_status == "RED":
            alerts.append(Alert("operational", "HIGH",
                                "انجراف نموذج حرج",
                                "إيقاف الاعتماد وإعادة تدريب"))
        elif drift_status == "AMBER":
            alerts.append(Alert("operational", "MEDIUM",
                                "انجراف نموذج متزايد",
                                "مراجعة وإعادة تقييم أسبوعية"))

        # 3) سلامة السجلات
        invalid = sum(1 for d in dossiers
                      if not verify_dossier(d)["valid"])
        if invalid:
            alerts.append(Alert("integrity", "HIGH",
                                f"{invalid} سجل غير سليم (تلاعب محتمل)",
                                "تجميد الاعتماد وفتح تحقيق"))

        # 4) أداء الـ cohort
        co = analyze(dossiers) if dossiers else None
        if co and co.stop_rate > stop_rate_threshold:
            alerts.append(Alert("clinical", "MEDIUM",
                                f"معدل إيقاف مرتفع: {co.stop_rate:.0%}",
                                "مراجعة منهجية للعتبات"))

        worst = max((SEV[a.severity] for a in alerts), default=0)
        posture = RAG_OF_SEV[worst]
        metrics = {"fleet": fq["overall"], "drift": drift_status,
                   "invalid": invalid,
                   "stop_rate": co.stop_rate if co else 0.0,
                   "mean_agreement": co.mean_agreement if co else 0.0}
        summary = self._narrate(posture, alerts, metrics)
        return GovernanceReport(posture, alerts, metrics, summary)

    @staticmethod
    def _narrate(posture, alerts, metrics) -> str:
        high = sum(1 for a in alerts if a.severity == "HIGH")
        med = sum(1 for a in alerts if a.severity == "MEDIUM")
        return (f"الوضعية العامة: {posture}. "
                f"تنبيهات حرجة: {high}، متوسطة: {med}. "
                f"الأسطول: {metrics['fleet']}، الانجراف: {metrics['drift']}، "
                f"سجلات غير سليمة: {metrics['invalid']}، "
                f"معدل الإيقاف: {metrics['stop_rate']:.0%}.")
