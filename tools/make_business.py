"""W6 FINAL: dual-license strategy with indicative pricing + LOI template."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIZ = ROOT / "docs" / "business"

DOCS = {
    "LICENSING-001.md": """# Licensing & Revenue Strategy — LICENSING-001

## Dual-license model
- Academic/Research tier: open-source core (MIT) — free for research and
  education; citation required (DOI 10.5281/zenodo.23147530).
- Commercial/Clinical tier: paid license for clinical deployment covering
  the regulatory package (W5), validated real-data models, support, SLA,
  and hosted option. New clinical-grade features ship commercial-only.

## Pricing (indicative, pre-market)
- Clinical site license: $25,000 setup + $10,000/year maintenance.
- Hosted SaaS: $50/case or $5,000/month unlimited.
- Validation-as-a-service: $8,000/site.
- Training & certification: $3,000/cohort.

## Why the moat survives open source
Defensible assets: (1) regulatory submission package, (2) validated
real-data models, (3) evidence chain (physics QA + benchmark), (4) partner
hospital data network, (5) validation & support services.

## Governance
Single-author copyright today; a Contributor License Agreement (CLA) is
required before accepting external contributions to preserve
dual-licensing viability.
""",
    "LOI-TEMPLATE-001.md": """# Letter of Intent (Non-Binding) — LOI-TEMPLATE-001

Between: [Hospital/Center] ("Data Partner") and ProtonAI ("Developer").

1. Purpose: explore a research collaboration to validate ProtonAI on
   de-identified proton-therapy CT cases.
2. Data: up to 10 de-identified DICOM CT series transferred per
   DEID-CHECKLIST-001 and DSA-001; no PHI leaves the partner.
3. Roles: Partner provides data + clinical review; Developer provides
   platform, analysis, and reporting.
4. Publication: joint authorship per ICMJE; partner reviews drafts.
5. IP: background IP remains with each party; foreground results shared.
6. Non-binding: creates no financial/legal obligation; a definitive
   agreement follows ethics approval.
7. Term: 6 months, renewable.

Placeholders to fill: [Hospital/Center], signatory name/title/date.

Signatures:
Data Partner (name/title/date): ______________________
Developer: Ali Hussein Thajil ______________________
""",
}


def main():
    BIZ.mkdir(parents=True, exist_ok=True)
    for name, body in DOCS.items():
        (BIZ / name).write_text(body, encoding="utf-8")
    print(f"W6 FINAL: business docs written ({len(DOCS)})")


if __name__ == "__main__":
    main()
