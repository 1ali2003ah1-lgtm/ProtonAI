"""
ProtonAI - Plan Comparison
مقارنة عدة خطط علاجية بمؤشرات الجودة: جدول مؤشرات + ترتيب + خطة مفضّلة
المنطق السريري: الأمان أولاً (الأسوأ يحكم)، ثم عدد الأحمر/الأصفر، ثم الأخضر
خطة بلا بيانات (overall UNKNOWN) = غير مفضّلة أبداً (لا نُكافئ "ما أدري")
"""

import logging
from typing import Dict, Any, List, Optional

from quality_indicators import QualityIndicators, Status
from treatment_plan import TreatmentPlan

logger = logging.getLogger("ProtonAI.PlanComparison")

_NO_DATA_RANK = 99  # مرتبة "بلا بيانات" (أسوأ من أي حالة مقيّمة)


def _status_rank_value(status: Status) -> int:
    """قيمة ترتيب للحالة: UNKNOWN → _NO_DATA_RANK (لا تُكافأ)، وإلا شدتها"""
    return _NO_DATA_RANK if status == Status.UNKNOWN else int(status)


class PlanComparison:
    """
    مقارن الخطط.
    - compare(plans): يقيّم كل خطة (evaluate_plan) ثم يقارن.
    - compare_evaluations(evals): يقارن نتائج evaluate/evaluate_plan مباشرة (مرونة).
    - المنطق: الأمان أولاً، ثم red، ثم amber، ثم green؛ بلا بيانات = بالآخر.
    - recommended=None عند التعادل أو غياب البيانات (لا نخترع فائزاً).
    """

    def __init__(self, quality: Optional[QualityIndicators] = None):
        self.qi = quality if quality is not None else QualityIndicators()

    def _n_green(self, ev: Dict[str, Any]) -> int:
        """عدد المؤشرات الخضراء (المشتق)"""
        total = len(ev["indicators"])
        return total - ev["n_red"] - ev["n_amber"] - ev["n_unknown"]

    def _rank_key(self, ev: Dict[str, Any]):
        """مفتاح ترتيب: أصغر = أأمن. بلا بيانات → بالآخر"""
        if ev["overall"] == Status.UNKNOWN:
            return (_NO_DATA_RANK, 0, 0, 0)
        return (int(ev["overall"]), ev["n_red"], ev["n_amber"], -self._n_green(ev))

    def _indicator_table(self, evals: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """جدول: لكل مؤشر، قيم/حالات كل خطة + الفائز به (None عند التعادل)"""
        if not evals:
            return []
        first = next(iter(evals.values()))
        order = [ind.name for ind in first["indicators"]]
        lookup: Dict[str, Dict[str, Any]] = {name: {} for name in order}
        for pname, ev in evals.items():
            for ind in ev["indicators"]:
                lookup[ind.name][pname] = ind
        table: List[Dict[str, Any]] = []
        for name in order:
            per_plan = lookup[name]
            values = {pn: ind.value for pn, ind in per_plan.items()}
            statuses = {pn: ind.status.name for pn, ind in per_plan.items()}
            symbols = {pn: ind.to_dict()["symbol"] for pn, ind in per_plan.items()}
            rank_vals = {pn: _status_rank_value(ind.status) for pn, ind in per_plan.items()}
            min_v = min(rank_vals.values())
            winners = [pn for pn, v in rank_vals.items() if v == min_v]
            winner = winners[0] if len(winners) == 1 else None
            table.append({
                "indicator": name,
                "label": per_plan[next(iter(per_plan))].label,
                "values": values, "statuses": statuses, "symbols": symbols,
                "winner": winner,
            })
        return table

    def compare_evaluations(self, evals: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """مقارنة نتائج evaluate/evaluate_plan مسبقاً (مرونة + اختبار)"""
        if len(evals) < 2:
            raise ValueError("المقارنة تحتاج خطتين على الأقل")
        table = self._indicator_table(evals)
        per_plan = {name: {
            "overall": ev["overall"].name,
            "overall_symbol": ev["overall_symbol"],
            "n_red": ev["n_red"], "n_amber": ev["n_amber"], "n_unknown": ev["n_unknown"],
            "rank_key": self._rank_key(ev),
        } for name, ev in evals.items()}
        ranking = sorted(evals.keys(), key=lambda n: per_plan[n]["rank_key"])

        # التوصية: حاسمة فقط لو الأعلى يتفوق فعلاً وحالته مقيّمة
        k0 = per_plan[ranking[0]]["rank_key"]
        k1 = per_plan[ranking[1]]["rank_key"]
        top_overall = evals[ranking[0]]["overall"]
        if top_overall == Status.UNKNOWN:
            recommended = None
            reason = "لا توجد بيانات كافية للمقارنة (كل المؤشرات غير متوفرة)"
            decisive = False
        elif k0 == k1:
            recommended = None
            reason = "تعادل: الخطتان متكافئتان بالسلامة والمؤشرات"
            decisive = False
        else:
            recommended = ranking[0]
            decisive = True
            reason = (f"الخطة '{recommended}' مفضّلة: حالتها الكلية "
                      f"{per_plan[ranking[0]]['overall']} مقابل "
                      f"{per_plan[ranking[1]]['overall']}، وأحمر "
                      f"{per_plan[ranking[0]]['n_red']} مقابل "
                      f"{per_plan[ranking[1]]['n_red']}")
        logger.info(f"comparison: ranking={ranking}, recommended={recommended}")
        return {
            "indicator_table": table, "per_plan": per_plan, "ranking": ranking,
            "recommended": recommended, "recommendation_reason": reason,
            "is_decisive": decisive,
        }

    def compare(self, plans: Dict[str, TreatmentPlan]) -> Dict[str, Any]:
        """مقارنة خطط: تقيّم كل خطة ثم تقارن"""
        evals = {name: self.qi.evaluate_plan(p) for name, p in plans.items()}
        return self.compare_evaluations(evals)
