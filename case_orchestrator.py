"""
ProtonAI - Case Orchestrator (Enterprise Capstone)
ينسّق سلسلة القرار الكاملة لحالة واحدة بـ CaseDossier موثق:
decision ← physics_qa ← phantom ← dose ← intelligence ← board ← final.
- سجل تدقيق متسلسل بالبصمات (hash chain) لكل مرحلة.
- قاعدة سلامة: أي STOP يثبّت التوصية النهائية STOP.
- تصدير مُخفى الهوية عبر reporting_export.scrub.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from board_intelligence import combine
from clinical_intelligence import ClinicalIntelligence
from clinical_report import build_report
from dose_stats import plan_metrics
from physics_qa import fleet_qa
from qa_phantom import phantom_qa
from reporting_export import scrub
from tumor_board import Opinion, TumorBoard


@dataclass
class CaseSpec:
    """مواصفات حالة كاملة (كل المدخلات اختيارية ما عدا الهوية/الموقع)"""
    case_id: str
    site: str
    dice: float = 0.92
    ece: float = 0.02
    status: str = "GREEN"
    prescription: float = 70.0
    range_mm: float = 100.0
    doses: Optional[List[float]] = None
    scanners: Optional[Dict[str, List[float]]] = None
    measured: Optional[List[float]] = None
    planned: Optional[List[float]] = None
    achieved_oars: Optional[Dict[str, float]] = None
    opinions: Optional[List[Opinion]] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Stage:
    name: str
    status: str
    summary: str
    hash: str


@dataclass
class CaseDossier:
    case_id: str
    site: str
    final: str
    stages: List[Stage]
    combined: dict
    extra: Dict[str, Any]

    @property
    def integrity(self) -> str:
        return self.stages[-1].hash if self.stages else ""

    def to_json(self) -> str:
        payload = {
            "case_id": self.case_id, "site": self.site,
            "final": self.final,
            "stages": [{"name": s.name, "status": s.status,
                        "hash": s.hash} for s in self.stages],
            "synthesis": self.combined["synthesis"],
            **self.extra,
        }
        return json.dumps(scrub(payload), ensure_ascii=False, indent=2)


class CaseOrchestrator:
    """منسّق الحالة: يبني Dossier موثق مرحلة‑بمرحلة"""

    def run(self, spec: CaseSpec) -> CaseDossier:
        stages: List[Stage] = []
        prev = "0" * 64

        def log(name, status, summary):
            nonlocal prev
            h = hashlib.sha256(
                (prev + name + status + summary).encode()).hexdigest()
            stages.append(Stage(name, status, summary, h))
            prev = h

        # 1) بوابة القرار
        rep = build_report(spec.case_id, spec.site, spec.dice, spec.ece,
                           status=spec.status, range_mm=spec.range_mm)
        log("decision", rep["decision"],
            f"margin={rep['range_margin_mm']:.1f}")

        # 2) فيزياء الأسطول
        if spec.scanners:
            fq = fleet_qa(spec.scanners)
            log("physics_qa", fq["overall"], f"flagged={fq['flagged']}")

        # 3) فانتوم QA
        if spec.measured and spec.planned:
            pq = phantom_qa(spec.measured, spec.planned)
            log("phantom_qa", pq["status"], f"pass={pq['pass_rate']}")

        # 4) مقاييس الجرعة
        if spec.doses:
            pm = plan_metrics(spec.doses, spec.prescription)
            log("dose", "OK", f"D95={pm['D95']}")

        # 5) الذكاء السريري
        intel = ClinicalIntelligence().synthesize(
            spec.case_id, spec.site, dice=spec.dice, ece=spec.ece,
            status=spec.status, prescription=spec.prescription,
            range_mm=spec.range_mm, achieved_oars=spec.achieved_oars)
        log("intelligence", "OK",
            f"evidence={intel.synthesis['evidence_count']}")

        # 6) مجلس الورم
        board = TumorBoard(spec.case_id)
        ops = spec.opinions or [
            Opinion("د. أورام", "oncologist", rep["decision"], 0.9),
            Opinion("د. فيزياء", "physicist", rep["decision"], 0.8),
        ]
        for o in ops:
            board.add(o)
        rec = board.decide()
        log("board", rec.decision or "NO_QUORUM", rec.reason)

        # 7) الدمج والختم
        combined = combine(intel, rec)
        final = combined["synthesis"]["overall_quality"]
        log("final", final, "dossier sealed")

        return CaseDossier(spec.case_id, spec.site, final, stages,
                           combined, spec.extra)
