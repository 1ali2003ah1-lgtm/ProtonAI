# RELEASE NOTES v0.5.0-clinical-package

## Document Control
| ID | Version | Base | Status |
|---|---|---|---|
| REL-005 | 1.0 | v0.4.0-real-world-ready | EFFECTIVE |

## 1. Scope
Phase-4 clinical readiness package: controlled reporting, executable
safety policy, and real-data acquisition infrastructure.

## 2. Contents
- RPT-001 v3.0: Phase-2+3 evidence, evidence sealing, revision history.
- CLIN-001 + clinical_gate.py: evidence-derived uncertainty threshold,
  three-state batch decision (AUTO / FLAGGED_REVIEW / SUSPEND_AND_CAPA),
  policy integrity verified on every load.
- DATA-ACQ-001 + run_data_acquisition_qc.py + DATASET_REGISTER.md:
  executable acceptance gate and controlled dataset ledger
  (reference row DATASET-000-SYNTH-REF).
- tools/release_gate.py: machine-enforced pre-tag checklist.

## 3. Evidence Summary
- Phase 2: Wilcoxon one-sided p = 0.031250; bootstrap 95% CI excludes 0;
  3/3 seeds concordant; STRONG EVIDENCE in-domain.
- Phase 3: external validation MIXED (in-domain gain, not shift
  robustness); UQ INFORMATIVE + OOD-SENSITIVE (cross-domain failure
  AUC = 1.0; OOD Mann-Whitney p = 0.0001).

## 4. Verification
- release_gate.py all-PASS on main before tagging.
- Full pytest suite green on main; unified CI workflow green.

## 5. Known Limitations (honest disclosure)
- Validation on synthetic phantoms only; real-data execution pending
  per DATA-ACQ-001 (n_min = 19, target = 30 paired volumes).
- Inter-observer contour reliability study pending.
- CLIN-001 approval signatures pending.

## 6. Upgrade Notes
- Additive changes only; no breaking API modifications.

## 7. Approval
| Role | Name | Signature | Date |
|---|---|---|---|
| Release Manager | (pending) | (pending) | (pending) |
| Medical Physicist | (pending) | (pending) | (pending) |
| QMS Manager | (pending) | (pending) | (pending) |
