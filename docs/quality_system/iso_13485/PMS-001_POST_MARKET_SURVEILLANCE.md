# PMS-001: Post-Market Surveillance Plan (ISO 20416)

## Document Control
| ID | Version | Status |
|---|---|---|
| PMS-001 | 2.0 | EFFECTIVE |

## 1. Indicators
- Flag-rate drift: one-sided two-proportion z-test (baseline first run
  vs latest), alpha = 0.05 AND practical delta > 0.10; <3 runs =>
  insufficient history.
- URGENT triage count per batch (CLIN-002).
- Inter-observer verdict (DATA-ACQ-001 s6): Dice >= 0.85 AND HD95 <= 5.0 mm.
- User complaints and incident reports.

## 2. Thresholds & Actions
- DRIFT or URGENT>0 or inter-observer FAIL => SURVEILLANCE: ESCALATE,
  open review; CAPA if confirmed; recalibration under CLIN-001
  threshold governance.
- Any URGENT case => physicist review within 24h (CLIN-001).
- Inter-observer failure => suspend intake of that source pending review.

## 3. Review Cadence
- Automated surveillance each dashboard run; append-only ledger
  (pms_ledger.json, last 100).
- Quarterly formal PMS review; annual threshold re-derivation.

## 4. Traceability
CLIN-001, CLIN-002, DATA-ACQ-001, CAPA_LOG, ISO 20416.
