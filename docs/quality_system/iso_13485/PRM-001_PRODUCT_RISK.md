# PRM-001: Product Risk Management (ISO 14971)

## Document Control
| ID | Version | Generated | Generator commit | Status |
|---|---|---|---|---|
| PRM-001 | 1.0 | 2026-09-30 22:05 UTC | 0001b81 | EFFECTIVE |

## 1. Method
FMEA scales 1-5; RPN = S x O x D; acceptable iff RPN < 40. Mitigations reference controlled assets only.

## 2. Risk Register
| ID | Hazard | S | O | D | RPN | Mitigations | Acceptable |
|---|---|---|---|---|---|---|---|
| R-101 | Incorrect auto-segmentation | 5 | 2 | 2 | 20 | CLIN-002, CLIN-001, interlock | True |
| R-102 | Automation bias (rubber-stamp approval) | 4 | 3 | 3 | 36 | interlock, confidence display, USP-001 | True |
| R-103 | Performance drift (population shift) | 4 | 3 | 2 | 24 | PMS-001, playbook | True |
| R-104 | PHI exposure | 4 | 2 | 2 | 16 | schema v2, ISO 27001 | True |
| R-105 | Train/deploy model mismatch | 4 | 1 | 1 | 4 | ADR-008 | True |
| R-106 | Insufficient real-world evidence at launch | 3 | 4 | 2 | 24 | SVP-001, playbook | True |
| R-107 | Regulatory pathway change | 3 | 2 | 3 | 18 | REG-001, QMS ISO 13485 | True |
| R-108 | Use error (overlay misinterpretation) | 3 | 3 | 2 | 18 | USP-001, calm design | True |

## 3. Residual Risk Evaluation
- Max RPN = 36 (< 40); all residual risks acceptable.
- R-102 (automation bias) is watched: enforced interlock + formative usability testing (USP-001).

## 4. Review Cadence
- Quarterly with PMS-001 review; on every new module or adverse event.

## 5. Traceability
NEXUS-PRD-001 s9, RPT-001 v4.0, CLIN-001, CLIN-002, PMS-001, ADR-007, ADR-008, USP-001, REG-001, SVP-001, ISO 14971.
