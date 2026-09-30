# NEXUS-PRD-001: Product Requirements — ProtonAI NEXUS Console

## Document Control
| ID | Version | Status | Owner |
|---|---|---|---|
| NEXUS-PRD-001 | 2.0 | EFFECTIVE | Founder |

---

## 1. Vision
The most trustworthy, explainable, safety-enforced clinical console for
proton therapy AI segmentation — the face of the ProtonAI evidence chain.

## 2. Mission
Transform proton therapy planning from hours to minutes while enforcing
safety at every interaction, making best-in-class AI segmentation
accessible to every cancer center worldwide.

## 3. Design Principles (non-negotiable)
- **Clickability**: every displayed number opens its full chain of custody.
- **Enforcement**: safety is enforced, not displayed (URGENT blocks
  approval until e-signed, per CLIN-001).
- **Calm**: reading-room aesthetic — dark mode default, color-blind-safe
  (WCAG AA), response <100ms.
- **Arabic/English**: i18n from line one (regional signature).

## 4. Success Metrics (KPIs)
| KPI | Target | Measure |
|---|---|---|
| Segmentation time | <30s/volume | system log |
| Clinician time saved | >50% vs manual | formative test |
| DVH metric preservation | ΔD95<1% | dose bridge |
| PMS drift detection | within 1 run | PMS-001 ledger |
| First-use success rate | >95% tasks | USP-001 formative |
| Regulatory bundle generation | <5 min | one-click |

## 5. Modules & Acceptance Criteria
1. **Cockpit (MPR + DVH)**: loads <500ms, scrollable z, uncertainty overlay toggle.
2. **What-if dose engine**: neural surrogate <500ms, MC verify on demand.
3. **CLIN-002 triage**: live, 3-level, approval interlocked.
4. **Provenance Explorer**: 3-click to root evidence.
5. **PMS wall**: drift map, ESCALATE alerts, per-department.
6. **Agreement room**: live Dice/HD95, consensus workflow.
7. **Model card**: live, one-click parity re-verify.
8. **Regulatory bundle**: one-click FDA/CE package.
9. **Federated console**: cross-site model versions.
10. **Patient story**: cinematic replay for committees.

## 6. Defensibility (why we cannot be copied)
- Sealed evidence chain (schema v2) — reproducible audit trail.
- Unified confidence (ADR-007): AI × physics in one score (not published commercially).
- Closed feedback loop (playbook → PMS → recalibration).
- Open methodology — trust through transparency, not obscurity.
- Regional signature: Arabic/English native i18n.

## 7. Non-Goals
- Not a full TPS (we complement, not replace Eclipse/RayStation).
- Not a general segmentation platform (proton-only, head/neck/lung focus).
- Not a research-only tool (we ship to clinical use).

## 8. Assumptions
- First hospital partnership delivers 10 de-identified cases within 6 months.
- Regulatory path: FDA 510(k) with predicate, CE MDR Class IIa.
- Pricing: B2B SaaS per-seat + per-patient.

## 9. Risks (linked to PRM-001)
- Data access delay; regulatory path change; competitor release.
- Mitigations documented in PRM-001 FMEA.

## 10. Open Questions
- Which organ sites first (brain vs lung vs head-neck)?
- Licensing vs subscription pricing model?
- First market: MENA vs EU vs US?

## 11. Compliance by Design
IEC 62366-1 usability file; FDA HFE testing; ISO 27001 auth+audit;
ISO 14971 risk (PRM-001); documented latency budgets.

## 12. Build Path
v1 Streamlit (cockpit) → v2 React/FastAPI (MPR + what-if) → v3 enterprise
(federated + PACS + submission bundle).

## 13. Traceability
CLIN-001, CLIN-002, ADR-007, ADR-008, PMS-001, RPT-001 v4.0, PRM-001,
USP-001, MSS-001, SVP-001, REG-001, TLM-001.
