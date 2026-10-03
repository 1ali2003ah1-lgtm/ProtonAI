# REAL-DATA-PLAYBOOK

## Document Control
| ID | Version | Generated | Commit | Status |
|---|---|---|---|---|
| REAL-DATA-PLAYBOOK | 1.0 | 2026-10-03 | 68cb6af | EFFECTIVE |

## 1. Purpose
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
