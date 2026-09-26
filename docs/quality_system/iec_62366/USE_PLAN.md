# Usability Engineering Plan (IEC 62366-1:2015+A1:2020)
Doc ID: USE-001 | Version: 2.0 | Status: DRAFT

## 1. User profiles
| Profile | Tasks | Knowledge |
|---|---|---|
| Radiation oncologist | Contour approval/edit, plan review | Clinical |
| Medical physicist | Dose verification, gamma/QA, release | Physics + SW |
| RT therapist | Pre-treatment checks | Clinical workflow |

## 2. Use scenarios
US-001 Select patient case
US-002 Review auto-contours, edit if needed
US-003 Evaluate plan (DVH, gamma, OAR doses)
US-004 Approve / reject plan (signed)
US-005 Export anonymized report

## 3. Hazard-related use scenarios (from RSK-001)
HUS-001 (R-006): wrong case selected -> wrong-patient treatment
HUS-002 (R-005): unauthorized/unsigned approval
HUS-003 (R-001): contour accepted without review due to UI fatigue

## 4. UI risk control requirements
- Patient ID double-check banner on every case open (HUS-001)
- Approval requires role + signature + reason (HUS-002)
- UQ flags visually block approve until acknowledged (HUS-003)

## 5. Formative evaluation
>=5 clinicians per profile; think-aloud; task success + error logging;
findings feed risk register and UI backlog.

## 6. Summative evaluation
Simulated tasks on frozen release; acceptance: ZERO critical use
errors; all residual errors risk-assessed and documented.
