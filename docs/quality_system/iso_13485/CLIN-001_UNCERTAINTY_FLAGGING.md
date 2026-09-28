# CLIN-001: Uncertainty Flagging & Physicist Review Policy

## Document Control
| ID | Version | Generated | Generator commit | Status |
|---|---|---|---|---|
| CLIN-001 | 1.0 | 2026-09-28 19:02 UTC | 0a6be7c | EFFECTIVE |

## 1. Scope
Applies to every ProtonAI organ-at-risk segmentation released into
a proton therapy planning workflow.

## 2. Definitions
- Vote entropy: mean pixel-wise binary entropy across the K=5 seed
  ensemble (ADR-006).
- Flagging threshold theta: maximum in-domain per-case vote entropy
  in the validated evidence set (uq_analysis_results.json).
- Separation margin: min cross-domain FAILING-case uncertainty
  minus theta (safety trench between safe and failing regions).

## 3. Flagging Rule (mandatory, machine-enforced)
- theta = 0.002382
- Separation margin = 0.005932
- Decision states (enforced by clinical_gate.py):

| State | Condition | Action |
|---|---|---|
| AUTO | no flagged cases | release pathway |
| FLAGGED_REVIEW | 0 < flag fraction <= 0.20 | flagged cases to
physicist review; remainder released |
| SUSPEND_AND_CAPA | flag fraction > 0.20 | suspend automated
pathway; manual contouring; CAPA within 24h |

- A flagged case MUST receive documented medical physicist review
  before any contour is used in planning. Release without review
  is a procedure violation.

## 4. Records & Audit
- Per case: uncertainty value, flag decision, decision state,
  reviewer ID, decision timestamp. Immutable audit trail (T-05).

## 5. Threshold Governance
- theta is recomputed only under change control: model retrain,
  new domain data, or annual review. Each change bumps this
  document version, clin001_policy.json, and the CHANGELOG.

## 6. Evidence Basis & Validation
- In-domain maximum (threshold source): 0.002382
- Cross-domain flag rate at theta: 8/8
- Cross-domain failures captured by flag: True
- OOD sensitivity: Mann-Whitney p = 0.0001
- Traceability: RISK_REGISTER R-010; ADR-006; RPT-001 v3.0 s9.2.

## 7. Approval
| Role | Name | Signature | Date |
|---|---|---|---|
| Author (Research Lead) | (pending) | (pending) | (pending) |
| Reviewer (Medical Physicist) | (pending) | (pending) | (pending) |
| Approver (QMS Manager) | (pending) | (pending) | (pending) |
