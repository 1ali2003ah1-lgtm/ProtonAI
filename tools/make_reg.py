"""A6 enhanced: regulatory strategy as code (REG-001 v2.0).

Adds: predicate analysis (real comparable devices), GSPR table (MDR
Annex I), UDI path, cybersecurity file, PMCF plan, classification
justification. Requirement-to-asset mapping + honest gaps preserved.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "product" / "REG-001_REGULATORY_STRATEGY.md"

PREDICATES = [
    {"device": "RayStation AI Contouring",
     "manufacturer": "RaySearch Laboratories",
     "clearance": "CE MDR Class IIa; FDA 510(k) K222953",
     "similarity": "auto-contouring + TPS integration",
     "differences": "no open evidence chain, no unified confidence, "
                    "no exposed PMS loop"},
    {"device": "Limbus AI",
     "manufacturer": "Limbus Medical AI",
     "clearance": "Health Canada, CE, FDA 510(k)",
     "similarity": "fast contouring AI for RT",
     "differences": "no AI x physics unified score"},
]

GSPR = [
    {"req": "GSPR 1 - General safety", "asset": "PRM-001 + PMS-001"},
    {"req": "GSPR 8 - Software lifecycle",
     "asset": "repo ADRs + release gate + versioned tags"},
    {"req": "GSPR 9 - Electronic programmable systems",
     "asset": "ADR-008 + ADR-007"},
    {"req": "GSPR 10 - Measurement functions",
     "asset": "ADR-007 + confidence display"},
    {"req": "GSPR 14 - Information supplied with device",
     "asset": "IFU + NEXUS UI + MODEL_CARD"},
    {"req": "GSPR 17 - Cybersecurity",
     "asset": "de-id gate + ISO 27001 plan"},
    {"req": "GSPR 18 - Interoperability",
     "asset": "DICOM reader + playbook integration"},
    {"req": "GSPR 21 - Protection against risks to patients",
     "asset": "CLIN-001 + interlock"},
]

UDI = ["UDI-DI (device identifier) from issuing entity (e.g. GS1)",
       "UDI-PI (production identifier) per batch/version",
       "Registration in EUDAMED (EU) and GUDID (FDA)",
       "Labeling per MDR Annex VI / 21 CFR 830"]

CYBER = ["SBOM (software bill of materials) auto-generated",
         "Vulnerability disclosure policy (public)",
         "Patching SLA: critical <72h, high <14d",
         "Penetration testing pre-release",
         "Encrypted data at rest + in transit (TLS 1.3)",
         "Authentication (Keycloak) + audit log (immutable)"]

PMCF = ["Annual review of real-data PLAYBOOK-001 ledger (PMS-001)",
        "User feedback aggregation from NEXUS console",
        "Post-market clinical follow-up survey (yearly, 30+ users)",
        "Re-evaluation of SVP-001 PAP-3 claims as data grows",
        "Trigger re-validation on model version change (ADR-008)"]

CLASSIFICATION_JUST = ("SaMD providing diagnostic/therapeutic suggestions "
                       "to clinicians (physicists/oncologists) for proton "
                       "contour review. Does NOT autonomously set dose; "
                       "final approval is human. Under MDR Rule 11: "
                       "Class IIa (decisions with diagnostic/therapeutic "
                       "purpose). FDA: Class II (21 CFR 892.2050 - "
                       "medical image processing) via 510(k) predicate.")

FDA_STEPS = ["Pre-Submission (Q-Sub) meeting",
             "Predicate analysis & substantial equivalence",
             "510(k) submission (eSTAR preferred)",
             "Interactive review (90 days)",
             "Clearance + GUDID registration"]
CE_STEPS = ["QMS ISO 13485 certification (Notified Body)",
            "Technical documentation (Annex II/III)",
            "GSPR conformity assessment",
            "Clinical evaluation report (CER)",
            "Notified Body audit",
            "CE marking + EUDAMED registration"]

TIMELINE = [
    {"t": "T0-T3m", "item": "ISO 13485 gap assessment + HFE formative (USP-001)"},
    {"t": "T3-T6m", "item": "ISO 13485 certification + UDI assignment"},
    {"t": "T6-T9m", "item": "Q-Sub + predicate analysis + SBOM"},
    {"t": "T9-T15m", "item": "clinical data (PAP-3) + 510(k) submission"},
    {"t": "T15-T21m", "item": "CE NB audit + clearance interaction"},
    {"t": "T21-T24m", "item": "CE marking + FDA clearance + EUDAMED/GUDID"},
]

GAPS = ["real clinical data (stage D / PAP-3)",
        "ISO 13485 certificate (certification pending)",
        "Notified Body contract (BSI / TÜV / DEKRA)",
        "summative HFE study (post-formative)",
        "clinical evaluation report (CER) drafting",
        "UDI issuing entity agreement (GS1)",
        "FDA eSTAR template completion",
        "SBOM generator integration"]


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# REG-001: Regulatory Strategy (FDA 510(k) + CE MDR)", "",
             "## Document Control",
             "| ID | Version | Generated | Generator commit | Status |",
             "|---|---|---|---|---|",
             f"| REG-001 | 2.0 | {now} | {git_commit()} | EFFECTIVE |", "",
             "## 1. Classification Justification",
             CLASSIFICATION_JUST, "",
             "## 2. Predicate Analysis (FDA substantial equivalence)",
             "| Predicate | Manufacturer | Clearance | Similarity | "
             "Our differentiation |",
             "|---|---|---|---|---|"]
    for p in PREDICATES:
        lines.append(f"| {p['device']} | {p['manufacturer']} | "
                     f"{p['clearance']} | {p['similarity']} | "
                     f"{p['differences']} |")
    lines += ["", "## 3. GSPR Table (MDR Annex I)",
              "| GSPR | Platform asset |", "|---|---|"]
    for g in GSPR:
        lines.append(f"| {g['req']} | {g['asset']} |")
    lines += ["", "## 4. UDI Path",
              "- " + "\n- ".join(UDI), "",
             "## 5. Cybersecurity File (FDA 2023 Guidance)",
             "- " + "\n- ".join(CYBER), "",
             "## 6. Post-Market Clinical Follow-up (PMCF)",
             "- " + "\n- ".join(PMCF), "",
             "## 7. FDA Path",
             ] + [f"{i+1}. {s}" for i, s in enumerate(FDA_STEPS)] + [
             "", "## 8. CE MDR Path",
             ] + [f"{i+1}. {s}" for i, s in enumerate(CE_STEPS)] + [
             "", "## 9. Timeline", "| Window | Milestone |", "|---|---|"]
    for t in TIMELINE:
        lines.append(f"| {t['t']} | {t['item']} |")
    lines += ["", "## 10. Honest Gaps",
              "- " + "\n- ".join(GAPS), "",
              "## 11. Traceability",
              "PRM-001, USP-001, PMS-001, SVP-001, NEXUS-PRD-001, "
              "ADR-007, ADR-008, IEC 62304, ISO 14971, IEC 62366-1, "
              "ISO 20416, MDR 2017/745, 21 CFR 807, FDA Cybersecurity "
              "Guidance 2023.", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"REG-001 v2: predicates={len(PREDICATES)} gspr={len(GSPR)} "
          f"gaps={len(GAPS)} timeline={len(TIMELINE)}")
    print("Saved -> docs/product/REG-001_REGULATORY_STRATEGY.md")


if __name__ == "__main__":
    main()
