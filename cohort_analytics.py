"""
ProtonAI - Cohort Analytics (تحليلات جماعية مؤسسية)
يجمّع عدة CaseDossier بلوحة إحصائية واحدة:
- توزيع القرارات + stop_rate.
- متوسط إجماع المجلس + معدل آراء الأقلية.
- معدل تفضيل البروتون والجدوى الاقتصادية.
- تفصيل لكل موقع ورم.
- يستبعد dossiers غير السليمة (forensics) ويعدّها منفصلة.
يدعم لوحة الـ tumor board والإدارة والمراجعة الدورية.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from case_orchestrator import CaseDossier
from dossier_verify import verify_dossier


@dataclass
class CohortStats:
    total: int
    valid: int
    invalid: int
    decision_counts: Dict[str, int]
    stop_rate: float
    mean_agreement: float
    dissent_rate: float
    favors_proton_rate: float
    cost_effective_rate: float
    by_site: Dict[str, Dict[str, int]] = field(default_factory=dict)


def _rate(num: int, den: int) -> float:
    return round(num / den, 3) if den else 0.0


def analyze(dossiers: List[CaseDossier]) -> CohortStats:
    if not dossiers:
        raise ValueError("cohort فارغ")

    valid: List[CaseDossier] = []
    invalid = 0
    for d in dossiers:
        if verify_dossier(d)["valid"]:
            valid.append(d)
        else:
            invalid += 1

    counts = {"PROCEED": 0, "REVIEW": 0, "STOP": 0}
    by_site: Dict[str, Dict[str, int]] = {}
    agg = agree = dissent = fav = eco = 0
    for d in valid:
        counts[d.final] = counts.get(d.final, 0) + 1
        by_site.setdefault(d.site, {})
        by_site[d.site][d.final] = by_site[d.site].get(d.final, 0) + 1
        s = d.combined["synthesis"]
        agg += s.get("board_agreement", 0)
        dissent += 1 if s.get("board_dissent", 0) > 0 else 0
        fav += 1 if s.get("favors_proton") else 0
        eco += 1 if s.get("cost_effective") else 0

    n = len(valid)
    return CohortStats(
        total=len(dossiers), valid=n, invalid=invalid,
        decision_counts=counts,
        stop_rate=_rate(counts.get("STOP", 0), n),
        mean_agreement=_rate(round(agg, 3), n),
        dissent_rate=_rate(dissent, n),
        favors_proton_rate=_rate(fav, n),
        cost_effective_rate=_rate(eco, n),
        by_site=by_site,
    )


def render_text(st: CohortStats) -> str:
    lines = [
        f"cohort: {st.total} حالة (سليم {st.valid} / مرفوض {st.invalid})",
        f"القرارات: {st.decision_counts}",
        f"stop_rate={st.stop_rate:.0%} • mean_agreement={st.mean_agreement:.0%}",
        f"dissent={st.dissent_rate:.0%} • favors_proton={st.favors_proton_rate:.0%}",
    ]
    return "\n".join(lines)
