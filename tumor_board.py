"""
ProtonAI - Tumor Board (محاكاة اجتماع الورم)
محاكاة احترافية لسير عمل الـ tumor board:
- أدوار متعددة (أورام/فيزياء/جراحة/أشعة/باثولوجيا + رئيس).
- نصاب إلزامي (oncologist + physicist) قبل أي قرار.
- إجماع بنسبة قابلة للضبط؛ آراء الأقلية موثقة (dissent).
- حق نقض سلامة: أي STOP أو safety_flag ⇒ القرار STOP (السلامة أولاً).
- تعادل ⇒ تصعيد إلى REVIEW (لا نخترع فائزاً).
"""

from dataclasses import dataclass, field
from typing import List, Optional

REC_VALUES = {"PROCEED": 2, "REVIEW": 1, "STOP": 0}
REQUIRED_ROLES = {"oncologist", "physicist"}


@dataclass
class Opinion:
    participant: str
    role: str
    recommendation: str
    confidence: float
    rationale: str = ""
    safety_flag: bool = False

    def __post_init__(self):
        if self.recommendation not in REC_VALUES:
            raise ValueError(f"توصية غير صالحة: {self.recommendation}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("الثقة لازم بين 0 و1")


@dataclass
class BoardRecord:
    case_id: str
    quorum_ok: bool
    decision: Optional[str]
    consensus: bool
    agreement_ratio: float
    dissent: List[Opinion] = field(default_factory=list)
    reason: str = ""


class TumorBoard:
    def __init__(self, case_id: str, consensus_threshold: float = 0.75):
        self.case_id = case_id
        self.threshold = consensus_threshold
        self.opinions: List[Opinion] = []

    def add(self, op: Opinion):
        self.opinions.append(op)

    def quorum_ok(self) -> bool:
        roles = {o.role for o in self.opinions}
        return REQUIRED_ROLES.issubset(roles)

    def tally(self) -> dict:
        t = {"PROCEED": 0, "REVIEW": 0, "STOP": 0}
        for o in self.opinions:
            t[o.recommendation] += 1
        return t

    def decide(self) -> BoardRecord:
        if not self.opinions:
            return BoardRecord(self.case_id, False, None, False, 0.0,
                               [], "لا آراء بعد")
        if not self.quorum_ok():
            return BoardRecord(self.case_id, False, None, False, 0.0,
                               self.opinions,
                               "نصاب غير مكتمل (يلزم oncologist + physicist)")

        # حق نقض السلامة
        if any(o.recommendation == "STOP" or o.safety_flag
               for o in self.opinions):
            dissent = [o for o in self.opinions if o.recommendation != "STOP"]
            return BoardRecord(self.case_id, True, "STOP", True, 1.0,
                               dissent,
                               "نقض سلامة: أي STOP/safety_flag يوقف الخطة")

        t = self.tally()
        ordered = sorted(t.items(), key=lambda kv: (-kv[1], REC_VALUES[kv[0]]))
        (top_rec, top_n), (second_rec, second_n) = ordered[0], ordered[1]
        n = len(self.opinions)
        ratio = top_n / n

        if top_n == second_n:
            return BoardRecord(self.case_id, True, "REVIEW", False, ratio,
                               [o for o in self.opinions
                                if o.recommendation != "REVIEW"],
                               "تعادل: تصعيد إلى REVIEW")

        consensus = ratio >= self.threshold
        dissent = [o for o in self.opinions if o.recommendation != top_rec]
        return BoardRecord(self.case_id, True, top_rec, consensus, ratio,
                           dissent, f"إجماع {ratio:.0%} على {top_rec}")
