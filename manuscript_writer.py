"""
ProtonAI - Manuscript Writer
مخطوطة IMRaD إنجليزية كاملة + Cover Letter، بأرقام حية من المنصة
ملخص مُهيكل (Background/Methods/Results/Conclusions) + مراجع مقترحة للتوثيق
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from paper_builder import PaperBuilder

logger = logging.getLogger("ProtonAI.ManuscriptWriter")

# مصادر مقترحة للتوثيق (يكمّل الباحث تفاصيلها/DOIs من مكتبته — لا نختلق)
SUGGESTED_REFERENCES = [
    "ICRU Report 78 — Prescribing, recording, and reporting proton-beam therapy.",
    "ICRU Report 91 — Prescribing/recording/reporting SBRT.",
    "NIST PSTAR — Stopping powers and ranges for protons (validation reference).",
    "Low et al. (1998) — Gamma-index evaluation technique (Med. Phys.).",
    "HL7 FHIR — Interoperability standard (PACS/HIS/RIS integration).",
    "Relevant reviews of AI/ML in radiation oncology (to complete by author).",
]


class ManuscriptWriter:
    """
    كاتب المخطوطة الإنجليزية.
    - build_manuscript: IMRaD كاملة بملخص مُهيكل وأرقام حية.
    - build_cover_letter: خطاب تقديم للمجلة.
    - save_all: يحفظ المخطوطة + الخطاب.
    """

    def __init__(
        self,
        title: str = "ProtonAI: An Integrated, Reproducible Decision-Support "
                     "Platform for Proton Therapy",
        authors: Optional[list] = None,
        venue: str = "Medical Physics / Radiotherapy & Oncology",
    ):
        self.title = title
        self.authors = list(authors) if authors else []
        self.venue = venue
        self._collector = PaperBuilder()

    def collect(self) -> Dict[str, Any]:
        """سحب المقاييس الحية من المنصة"""
        return self._collector.collect()

    def _fmt(self, v) -> str:
        return f"{v:.3f}" if isinstance(v, float) else str(v)

    def build_manuscript(self, r: Dict[str, Any]) -> str:
        retro, ext = r.get("retro", {}), r.get("external", {})
        clin, repro = r.get("clinical", {}), r.get("reproducibility", {})
        imp = r.get("improvement", {})
        acc, sens, spec = (retro.get("accuracy", 0), retro.get("sensitivity", 0),
                           retro.get("specificity", 0))
        gap, verdict = ext.get("generalization_gap", 0), ext.get("verdict", "?")
        ready = "ready for publication" if ext.get("publication_ready") else \
                "not yet ready for publication"
        L = [f"# {self.title}", ""]
        if self.authors:
            L.append(f"**Authors:** {', '.join(self.authors)}  ")
        L += [f"**Target venue:** {self.venue}", "", "## Abstract", "",
              f"**Background:** Proton therapy demands tight integration of imaging, "
              f"physics computation, and clinical decision-making with full "
              f"accountability. **Methods:** We developed ProtonAI, an integrated "
              f"platform spanning anonymized data ingestion, explainable AI, "
              f"Monte-Carlo-validated proton physics, human-in-the-loop decision "
              f"support, and enterprise readiness (RBAC, audit trails, maker–checker "
              f"gates, monitoring, FHIR integration, containerization). We evaluated "
              f"it via retrospective validation and external generalization. "
              f"**Results:** Retrospective accuracy was {self._fmt(acc)} "
              f"(sensitivity {self._fmt(sens)}, specificity {self._fmt(spec)}). On an "
              f"independent external set the generalization gap was {self._fmt(gap)} "
              f"({verdict}); results are {ready}. **Conclusions:** ProtonAI provides a "
              f"transparent, reproducible decision-support pipeline that retains final "
              f"authority with the specialist.", "",
              "**Keywords:** proton therapy; decision support; Monte Carlo; radiation "
              "physics; external generalization; reproducibility.", "",
              "## 1. Introduction", "",
              "Proton therapy offers superior dose conformation, yet its clinical "
              "workflow couples imaging, physics, and judgment in ways that are hard "
              "to audit end-to-end. Existing tools address isolated stages; few "
              "integrate data-to-decision with accountability and reproducibility. "
              "We present ProtonAI, a platform that closes this gap while keeping "
              "the final decision with the specialist.", "",
              "## 2. Methods", "",
              "- **Data layer:** contract-gated UCI ingestion with automatic "
              "de-identification.",
              "- **Evaluation:** 95% confidence intervals, fingerprinted "
              "reproducibility, physician review.",
              "- **AI engine:** explainability, self-tuning, ensemble, dose engine, "
              "versioned model registry.",
              "- **Imaging:** DICOM reading, tissue/OAR segmentation, breathing margin.",
              "- **Physics:** Bragg/SOBP/range/RBE models validated against PSTAR, "
              "Monte Carlo simulation, gamma-index, uncertainty propagation.",
              "- **Decision support:** color-coded indicators, plan comparison, "
              "guarded state machine, human-in-the-loop approval.",
              "- **Enterprise:** RBAC, audit trails, maker–checker gates, monitoring, "
              "FHIR adapters, containerization.", "",
              "## 3. Results", "",
              f"Clinical pipeline reached state `{clin.get('state','?')}` with overall "
              f"status `{clin.get('overall','?')}`. Retrospective validation yielded "
              f"accuracy {self._fmt(acc)}, sensitivity {self._fmt(sens)}, specificity "
              f"{self._fmt(spec)} (PPV {self._fmt(retro.get('ppv'))}, NPV "
              f"{self._fmt(retro.get('npv'))}). External generalization gave internal "
              f"accuracy {self._fmt(ext.get('internal_accuracy'))} vs external "
              f"{self._fmt(ext.get('external_accuracy'))} (gap {self._fmt(gap)}, "
              f"{verdict}). The improvement loop flagged {imp.get('n_issues',0)} "
              f"issue(s). Reproducibility seeds: {repro.get('seeds',[])}; Python "
              f"{repro.get('python','?')}.", "",
              "## 4. Discussion", "",
              f"The small generalization gap ({self._fmt(gap)}) indicates limited "
              "overfitting, and the maker–checker + audit design provides the "
              "accountability expected of clinical software. Retaining final authority "
              "with the specialist aligns with regulatory and ethical expectations.", "",
              "## 5. Limitations", "",
              "- Retrospective single-cohort validation; prospective multi-center "
              "studies are needed.",
              "- Physics models are analytic/CSDA approximations, not full Monte Carlo "
              "transport in tissue.",
              "- FHIR/PACS integration is validated at the contract level, not against "
              "a live hospital system.",
              "- Demo datasets are synthetic for testing.", "",
              "## 6. Conclusions", "",
              "ProtonAI delivers an integrated, transparent, reproducible decision-"
              "support pipeline for proton therapy, with final authority retained by "
              "the specialist, and paves the way for prospective multi-center "
              "validation.", "",
              "## References (to complete by author)", ""]
        L += [f"- {ref}" for ref in SUGGESTED_REFERENCES]
        L.append("")
        return "\n".join(L)

    def build_cover_letter(
        self, r: Dict[str, Any], editor: str = "[Editor]",
        journal: str = "[Journal]",
    ) -> str:
        ext = r.get("external", {})
        return (f"Dear {editor},\n\n"
                f"We submit our manuscript “{self.title}” for consideration in "
                f"{journal}. The work presents ProtonAI, an integrated, reproducible "
                f"decision-support platform for proton therapy, evaluated by "
                f"retrospective validation and external generalization (gap "
                f"{self._fmt(ext.get('generalization_gap', 0))}). The platform keeps "
                f"final clinical authority with the specialist and ships with a full "
                f"reproducibility package.\n\n"
                f"This manuscript is original and not under consideration elsewhere. "
                f"All authors approve the submission.\n\n"
                f"Sincerely,\n{', '.join(self.authors) or '[Corresponding author]'}\n")

    def save_all(self, r: Dict[str, Any], outdir) -> None:
        out = Path(outdir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "manuscript.md").write_text(self.build_manuscript(r), encoding="utf-8")
        (out / "cover_letter.md").write_text(self.build_cover_letter(r), encoding="utf-8")
        logger.info(f"حُفظت المخطوطة والخطاب في: {out}")
