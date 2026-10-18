"""Clinical decision support rules (physician alerts).
Designed & developed by: Ali Hussein Thajil

Implements evidence-based rules that trigger alerts for physician review.
Aligned with NCCN/ESTRO guidelines for proton therapy.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

SEVERITY = ("info", "warning", "critical")


@dataclass
class RuleAlert:
    rule_id: str
    severity: str
    title: str
    message: str
    recommendation: str
    evidence: str = ""


class ClinicalRuleEngine:
    def __init__(self):
        self.rules = [
            self._r_d95, self._r_oar_spinal, self._r_oar_brainstem,
            self._r_robust, self._r_uncertainty, self._r_tcp,
            self._r_hi, self._r_ci,
        ]

    def evaluate(self, summary: Dict) -> List[RuleAlert]:
        alerts = []
        for r in self.rules:
            a = r(summary)
            if a:
                alerts.append(a)
        return alerts

    def _r_d95(self, s: Dict):
        v95 = s.get("physics", {}).get("v95", 1.0)
        if v95 < 0.95:
            return RuleAlert(
                "RULE-D95-LOW", "critical",
                "Insufficient target coverage",
                f"V95 = {v95:.3f} (below 0.95 threshold)",
                "Consider increasing beam energy or adding fields",
                "ICRU 78, ICRU 91")
        return None

    def _r_oar_spinal(self, s: Dict):
        # Placeholder: OAR doses would be in summary
        return None

    def _r_oar_brainstem(self, s: Dict):
        return None

    def _r_robust(self, s: Dict):
        worst = s.get("robust_worst_d95", 1.0)
        if worst < 0.90:
            return RuleAlert(
                "RULE-ROBUST-LOW", "warning",
                "Low robustness",
                f"Worst-case D95 = {worst:.3f}",
                "Consider larger margins or robust optimization",
                "Lomax 2008, ICRU 78")
        return None

    def _r_uncertainty(self, s: Dict):
        unc = s.get("uncertainty_mean", 0.0)
        if unc > 0.30:
            return RuleAlert(
                "RULE-UNCERTAINTY-HIGH", "warning",
                "High segmentation uncertainty",
                f"Mean uncertainty = {unc:.3f}",
                "Physician review strongly recommended",
                "")
        return None

    def _r_tcp(self, s: Dict):
        tcp = s.get("physics", {}).get("tcp", 1.0)
        if tcp < 0.85:
            return RuleAlert(
                "RULE-TCP-LOW", "warning",
                "Low predicted tumor control",
                f"TCP = {tcp:.3f}",
                "Consider dose escalation or combination therapy",
                "")
        return None

    def _r_hi(self, s: Dict):
        hi = s.get("physics", {}).get("hi", 0.0)
        if hi > 0.20:
            return RuleAlert(
                "RULE-HI-HIGH", "info",
                "High dose heterogeneity in target",
                f"HI = {hi:.3f}",
                "Review hot spots; consider replanning",
                "ICRU 91")
        return None

    def _r_ci(self, s: Dict):
        ci = s.get("physics", {}).get("ci", 1.0)
        if ci > 1.5 or ci < 0.8:
            return RuleAlert(
                "RULE-CI-POOR", "info",
                "Poor conformity",
                f"CI = {ci:.3f}",
                "Review field arrangement",
                "ICRU 91")
        return None
