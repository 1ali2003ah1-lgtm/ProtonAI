# USP-001: Use Specification & Usability Engineering (IEC 62366-1)

## Document Control
| ID | Version | Generated | Generator commit | Status |
|---|---|---|---|---|
| USP-001 | 1.0 | 2026-09-30 22:12 UTC | f7062eb | EFFECTIVE |

## 1. Intended Use
Review, triage and approval assistance for AI-generated proton-therapy contours; not a treatment planning system.

## 2. User Profiles
| ID | Role | Expertise | Primary tasks |
|---|---|---|---|
| UP-1 | Medical physicist | high | plan approval, DVH review, model-card verification |
| UP-2 | Radiation oncologist | clinical | contour review, triage response |
| UP-3 | Dosimetrist | medium | contour editing, what-if exploration |
| UP-4 | QA officer | quality | PMS review, regulatory bundle generation |

## 3. Tasks & Criticality (linked to PRM-001)
| ID | Task | Profile | Critical | Linked risk |
|---|---|---|---|---|
| T-1 | Review AI contour with uncertainty overlay | UP-2 | True | R-101 |
| T-2 | Approve or reject plan (interlock) | UP-1 | True | R-102 |
| T-3 | Explore what-if dose | UP-3 | False | R-108 |
| T-4 | Verify model card parity | UP-1 | False | R-105 |
| T-5 | Review PMS drift wall | UP-4 | True | R-103 |
| T-6 | Generate regulatory bundle | UP-4 | False | R-107 |

## 4. Formative Evaluation Plan
- Participants: 6 (all profiles); sessions: 2.
- Method: think-aloud + System Usability Scale (SUS).
- Success criterion: first-use task success > 95% (matches NEXUS-PRD-001 KPI).

## 5. Summative Evaluation Plan
- Pre-approval simulated-use study on de-identified cases; zero critical use errors tolerated.

## 6. User Interface Characteristics
Dark reading-room default; color-blind-safe palette; Arabic/English i18n; response <100ms; approval interlock visible and explained.

## 7. Traceability
IEC 62366-1, PRM-001 (R-101..R-108), NEXUS-PRD-001, CLIN-001, CLIN-002.
