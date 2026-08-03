"""
ProtonAI - Operational Monitoring
مراقبة تشغيلية (مو سريرية): تجميع مقاييس النظام + ملخص + تنبيهات استباقية
تقرأ من سجلات التدقيق + القرارات + الحالات + المؤشرات، وترفع أعلام عند الريب
الفرق بين منصة لعبة ومنصة مستشفى: هذي تراقب نفسها قبل ما يراقبها أحد
"""

import logging
from collections import Counter
from typing import Dict, Any, List, Iterable

logger = logging.getLogger("ProtonAI.Monitoring")


class Monitoring:
    """
    مجمّع مقاييس تشغيلية.
    - add_audit: من سجلات EnterpriseAuditTrail (action/outcome/role).
    - add_decisions: من DecisionRecord (recommendation/override).
    - add_states / add_overalls: توزيع الحالات والمؤشرات.
    - summary: قاموس تشغيلي موحّد.
    - alerts: تنبيهات استباقية (warn/critical) عند الريب.
    - to_markdown: لوحة تشغيلية نصية.
    """

    def __init__(self):
        self._actions: Counter = Counter()
        self._by_role: Counter = Counter()
        self._recs: Counter = Counter()
        self._states: Counter = Counter()
        self._overall: Counter = Counter()
        self._denied = 0
        self._overrides = 0

    def add_audit(self, records: Iterable[Dict[str, Any]]) -> None:
        """تجميع من سجلات التدقيق"""
        for r in records:
            self._actions[str(r.get("action"))] += 1
            self._by_role[str(r.get("role"))] += 1
            if str(r.get("outcome")) == "DENIED":
                self._denied += 1

    def add_decisions(self, decisions: Iterable[Any]) -> None:
        """تجميع من سجلات القرار (recommendation + override)"""
        for d in decisions:
            rec = getattr(d, "recommendation", None)
            if rec is not None:
                self._recs[getattr(rec, "value", str(rec))] += 1
            if getattr(d, "override", False):
                self._overrides += 1

    def add_states(self, states: Iterable[str]) -> None:
        """توزيع حالات الخطط"""
        for s in states:
            self._states[str(s)] += 1

    def add_overalls(self, names: Iterable[str]) -> None:
        """توزيع الحالات الكلية للمؤشرات (GREEN/AMBER/RED/UNKNOWN)"""
        for n in names:
            self._overall[str(n)] += 1

    def alerts(self) -> List[Dict[str, str]]:
        """تنبيهات استباقية: أي denied/override/أحمر/مجهول = علم مرفوع"""
        out: List[Dict[str, str]] = []
        if self._denied > 0:
            out.append({"level": "warn",
                        "message": f"{self._denied} محاولة وصول مرفوضة — راجع الأمن"})
        if self._overrides > 0:
            out.append({"level": "critical",
                        "message": f"{self._overrides} تجاوز متخصص موثّق — راجع القرارات"})
        if self._overall.get("RED", 0) > 0:
            out.append({"level": "critical",
                        "message": f"{self._overall['RED']} خطة بمؤشرات حمراء — لا تسلّم"})
        if self._overall.get("UNKNOWN", 0) > 0:
            out.append({"level": "warn",
                        "message": f"{self._overall['UNKNOWN']} خطة ببيانات ناقصة"})
        return out

    def summary(self) -> Dict[str, Any]:
        """القاموس التشغيلي الموحّد"""
        return {
            "actions": dict(self._actions),
            "total_actions": sum(self._actions.values()),
            "denied_access": self._denied,
            "by_role": dict(self._by_role),
            "recommendations": dict(self._recs),
            "specialist_overrides": self._overrides,
            "states": dict(self._states),
            "overall_indicators": dict(self._overall),
            "alerts": self.alerts(),
        }

    def to_markdown(self) -> str:
        """لوحة تشغيلية نصية"""
        s = self.summary()
        lines = ["# 📈 لوحة المراقبة التشغيلية", "",
                 f"**إجمالي العمليات:** {s['total_actions']}  ",
                 f"**محاولات وصول مرفوضة:** {s['denied_access']}  ",
                 f"**تجاوزات متخصصين:** {s['specialist_overrides']}  ", "",
                 "## العمليات حسب النوع", ""]
        for k, v in s["actions"].items():
            lines.append(f"- {k}: {v}")
        lines += ["", "## النشاط حسب الدور", ""]
        for k, v in s["by_role"].items():
            lines.append(f"- {k}: {v}")
        lines += ["", "## التوصيات", ""]
        for k, v in s["recommendations"].items():
            lines.append(f"- {k}: {v}")
        lines += ["", "## الحالات الكلية للمؤشرات", ""]
        for k, v in s["overall_indicators"].items():
            lines.append(f"- {k}: {v}")
        lines += ["", "## التنبيهات", ""]
        if s["alerts"]:
            for a in s["alerts"]:
                icon = "🔴" if a["level"] == "critical" else "🟡"
                lines.append(f"- {icon} {a['message']}")
        else:
            lines.append("- 🟢 لا تنبيهات — النظام سليم")
        return "\n".join(lines)
