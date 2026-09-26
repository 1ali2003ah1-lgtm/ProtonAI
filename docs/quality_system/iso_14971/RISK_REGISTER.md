# ProtonAI Risk Register (ISO 14971:2019)
Doc ID: RSK-001 | Version: 1.0 | LIVING DOCUMENT
Scale: Severity 1-5, Probability 1-5, RPN = S x P.
Acceptance: residual RPN <= 6; no S=5 with P >= 2 left unmitigated.

| ID | Hazard | Foreseeable event | Harm | S | P | RPN | Controls | Residual S/P | Status |
|---|---|---|---|---|---|---|---|---|---|
| R-001 | Auto-segmentation error | OAR under-contoured | OAR overdose | 5 | 3 | 15 | safety_gate dose limits; physician approval gate; UQ flags; per-OAR Dice monitoring | 5/1 | OPEN |
| R-002 | HU->RSP calibration error | Bragg peak range miss | tumor underdose / OAR overdose | 5 | 2 | 10 | hu_rsp_calibration checks; robust margins; gamma verification | 5/1 | OPEN |
| R-003 | Model drift (scanner/protocol change) | silent accuracy loss | wrong contours over time | 4 | 3 | 12 | drift_monitor alerts; scheduled re-validation; release gating | 4/1 | OPEN |
| R-004 | PHI exposure | data breach | privacy & legal harm | 4 | 2 | 8 | anonymizer + phi_scrubber; RBAC; audit trails; encryption | 4/1 | OPEN |
| R-005 | Unauthorized plan change | malicious/erroneous edit | patient harm | 5 | 1 | 5 | approval_gates; immutable audit trail; role separation | 5/1 | OPEN |
| R-006 | Use error (wrong case selected) | treatment of wrong plan | patient harm | 5 | 2 | 10 | IEC 62366 usability file; confirmations; patient ID double-check | 5/1 | OPEN |
| R-007 | Model/weight tampering | corrupted predictions | patient harm | 5 | 1 | 5 | artifact signing; integrity check at load; least privilege | 5/1 | OPEN |

## Risk acceptance rule
Residual risk accepted only with documented benefit-risk rationale and
signature of Founder + clinical advisor.
