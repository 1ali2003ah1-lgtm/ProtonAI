"""D1 FINAL: self-consistent institutional partnership package.

Single source of truth PARTNERSHIP-MANIFEST.json; six documents derived
from it; cross-consistency enforced by tests. Honest + legal disclaimer.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
D = ROOT / "docs" / "partnership"
DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")

HP = D / "HOSPITAL-PARTNERSHIP-001.md"
DSA = D / "DSA-001_DATA_SHARING.md"
RDP = D / "REAL-DATA-PLAYBOOK.md"
DEID = D / "DEID-CHECKLIST-001.md"
SEC = D / "DATA-TRANSFER-SECURITY-001.md"
IRB = D / "IRB-TEMPLATE-001.md"
MANIFEST = D / "PARTNERSHIP-MANIFEST.json"

SPEC = {
    "id": "PARTNERSHIP-MANIFEST", "version": "1.0",
    "min_cases": 10, "site_types": ["head-neck", "lung"],
    "endpoints": ["D95", "OAR_V20", "TCP", "NTCP"],
    "deid_tags": ["(0010,0010)", "(0010,0020)", "(0010,0030)",
                  "(0008,0090)", "(0008,0080)"],
    "security_controls": ["sha256 manifest", "TLS 1.3",
                          "encrypted at rest", "audit log",
                          "72h breach notice"],
    "irb_required": True,
    "honesty": "NOT yet validated on human patients; synthetic phantoms only.",
}


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def _head(doc_id):
    return (f"# {doc_id}\n\n## Document Control\n"
            "| ID | Version | Generated | Commit | Status |\n"
            "|---|---|---|---|---|\n"
            f"| {doc_id} | 1.0 | {DATE} | {git_commit()} | EFFECTIVE |\n\n")


def build_hp():
    return _head("HOSPITAL-PARTNERSHIP-001") + f"""## 1. Executive Summary
Open, auditable AI platform for proton-therapy contouring assistance;
seek one anchor partner for first real-patient validation on
{SPEC['min_cases']} de-identified cases.

## 2. Offer / 3. Ask
Free research access + joint authorship (SVP-001) + early NEXUS access.
Ask: {SPEC['min_cases']} de-id CT cases; two manual contours; RT-Plan;
IRB confirmation.

## 4. What We Do NOT Claim
{SPEC['honesty']} (RPT-001 v4.0, DOSE-IMPACT-001). Gateway to real
claims, not the claim.

## 5. Endpoints
{', '.join(SPEC['endpoints'])}.

## 6. Timeline
W1 DSA+IRB; W2-3 transfer; W4 runs; W5-6 report; W8 PAP-3 draft.

## 7. Traceability
NEXUS-PRD-001, SVP-001, REG-001, RPT-001, DOSE-IMPACT-001, DSA-001,
REAL-DATA-PLAYBOOK, DEID-CHECKLIST-001, DATA-TRANSFER-SECURITY-001,
IRB-TEMPLATE-001, PARTNERSHIP-MANIFEST.
"""


def build_dsa():
    return _head("DSA-001") + """## 1-3. Parties / Purpose / Scope
Provider [Hospital]; Recipient ProtonAI. Research, non-clinical.
De-id DICOM CT + contours + RT-Plan; no PHI.

## 4. De-identification
HIPAA Safe Harbor / GDPR Art. 4(5); see DEID-CHECKLIST-001.

## 5. Security
See DATA-TRANSFER-SECURITY-001.

## 6-8. Rights / Compliance / Termination
Provider owns source; recipient owns derived; ICMJE authorship; 30-day
review. Provider IRB; recipient ISO 27001-aligned. 30-day termination.

## 9. Legal Disclaimer
Research template; not legal advice; review with counsel.

## 10. Signatures
Provider: ______ Recipient: ______ Date: ____

## 11. Traceability
HOSPITAL-PARTNERSHIP-001, DEID-CHECKLIST-001, DATA-TRANSFER-SECURITY-001.
"""


def build_rdp():
    return _head("REAL-DATA-PLAYBOOK") + """## 1. Purpose
First real-case operational guide.

## 2. Pre-Flight
DSA signed; IRB letter; secure channel; DEID signed; bootstrap; gate green.

## 3. Run
python tools/run_real_data_playbook.py /incoming/REAL-001 REAL-001-001

## 4. Verify / 5. Escalation
intake=ACCEPT; seals match; audit committed; triage recorded.
REJECT->stop; URGENT->physicist; seal mismatch->CAPA.

## 6. Reporting / 7. Traceability
10 cases -> RPT-001 v5.0 + PAP-3. PLAYBOOK-001, CLIN-002, PMS-001.
"""


def build_deid():
    tags = "\n".join(f"- {t}" for t in SPEC["deid_tags"])
    return _head("DEID-CHECKLIST-001") + f"""## 1. Purpose
Ensure DICOM de-identified before transfer.

## 2. Tags To Scrub
{tags}

## 3. Verification
Tag dump confirms scrubbed; no PHI in private/free-text; pseudonym
REAL-xxx; provider signs per batch.

## 4. Traceability
DSA-001 s4, HIPAA Safe Harbor, GDPR Art. 4(5), PARTNERSHIP-MANIFEST.
"""


def build_sec():
    ctrls = "\n".join(f"- {c}" for c in SPEC["security_controls"])
    return _head("DATA-TRANSFER-SECURITY-001") + f"""## 1. Purpose
Secure transfer/storage of research DICOM.

## 2. Controls
{ctrls}

## 3. Retention / 4. Incident
5 years then destruction. Breach -> notify within 72h; CAPA.

## 5. Traceability
DSA-001 s5, ISO 27001, DEID-CHECKLIST-001, PMS-001.
"""


def build_irb():
    return _head("IRB-TEMPLATE-001") + """## 1. Title
Retrospective validation of AI contouring assistance for proton therapy
using de-identified imaging.

## 2. Design / 3. Risk-Benefit
Retrospective non-interventional. Minimal risk; evidence benefit.

## 4. Consent Waiver
Retrospective de-id; impracticable consent; no adverse effect on rights.

## 5. Confidentiality / 6. Contact
Per DATA-TRANSFER-SECURITY-001. [PI], [institution], [email].

## 7. Traceability
HOSPITAL-PARTNERSHIP-001, DSA-001, DEID-CHECKLIST-001.
"""


def partnership_ready():
    return {"docs": all(p.exists() for p in (HP, DSA, RDP, DEID, SEC, IRB)),
            "manifest": MANIFEST.exists(),
            "playbook": (ROOT / "tools" / "run_real_data_playbook.py").exists(),
            "bootstrap": (ROOT / "tools" / "bootstrap_env.sh").exists()}


def main():
    D.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(SPEC, indent=2), encoding="utf-8")
    for text, path in [(build_hp(), HP), (build_dsa(), DSA),
                       (build_rdp(), RDP), (build_deid(), DEID),
                       (build_sec(), SEC), (build_irb(), IRB)]:
        path.write_text(text, encoding="utf-8")
    ready = partnership_ready()
    print(f"D1 FINAL: 6 docs + manifest; ready={ready}")


if __name__ == "__main__":
    main()
