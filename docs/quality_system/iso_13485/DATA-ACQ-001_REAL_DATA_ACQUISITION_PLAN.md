# DATA-ACQ-001: Real Clinical Data Acquisition Plan

## Document Control
| ID | Version | Issued | Status |
|---|---|---|---|
| DATA-ACQ-001 | 1.0 | Phase 4 (v0.5.0 cycle) | EFFECTIVE |

## 1. Purpose
Define the controlled pathway for acquiring real head & neck CT data to
externally validate ProtonAI segmentation beyond synthetic phantoms.

## 2. Sources (priority order)
1. S1 - Public de-identified repositories (e.g. TCIA head & neck CT
   collections). License and de-identification statement verified first.
2. S2 - Hospital research agreements (DUA/MTA) with de-identification
   applied at export (DICOM PS3.15 de-identification profile).
3. S3 - Prospective collection under IRB/ethics approval (last resort).

## 3. Inclusion / Exclusion Criteria
- Include: head & neck CT, slice thickness <= 3 mm, certified OAR
  contours (RTOG atlas convention) available as RTSTRUCT or masks.
- Exclude: severe metal artifact, prior surgery deforming target
  anatomy, incomplete series (< 8 slices), non-calibrated HU.

## 4. De-Identification Gate (machine-enforced)
- Every series MUST pass
  `real_data_adapter.ingest_real_series(path, allow_phi=False)`.
- Exceptions require documented change control, never ad hoc.

## 5. Executable QC & Dataset Register
- tools/run_data_acquisition_qc.py enforces sections 3-6 per dataset:
  de-id gate, completeness, HU air calibration (conditional on air
  presence), contour presence; decision ACCEPT/REJECT.
- Every decision is ledgered in DATASET_REGISTER.md (one row per
  dataset id, immutable append-only).
- Reference run: DATASET-000-SYNTH-REF (synthetic calibration set).

## 6. Acceptance QC
- HU calibration: air ~ -1000 when air present; soft tissue reported.
- Inter-observer reliability: 10% of volumes double-contoured
  independently; inter-observer Dice >= 0.85 else series rejected.

## 7. Statistical Power
- Target effect delta = 0.02 Dice; conservative sigma = 0.03.
- alpha = 0.05 two-sided, power = 0.80, paired design, Wilcoxon
  efficiency 0.955 (computed by tools/power_analysis.py):
  n_min = 19 paired volumes; operational target = 30.

## 8. Governance & Provenance
- Each accepted dataset gets a register ID and a provenance manifest
  via tools/make_provenance_manifest.py.
- Encrypted storage, access logging, 10-year retention.
- No identifiable data leaves the hospital boundary (S2/S3).

## 9. Traceability
R-003 (real-data validation), ADR-001 (synthetic-first), ADR-005
(external validation), CLIN-001 (flagging), RPT-001 v3.0.

## 10. Approval
| Role | Name | Signature | Date |
|---|---|---|---|
| Author (Research Lead) | (pending) | (pending) | (pending) |
| Reviewer (Medical Physicist) | (pending) | (pending) | (pending) |
| Approver (QMS Manager) | (pending) | (pending) | (pending) |
