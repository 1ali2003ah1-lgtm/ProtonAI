# PLAYBOOK-001: One-Command Real-Data Evidence Run

## Document Control
| ID | Version | Status |
|---|---|---|
| PLAYBOOK-001 | 1.0 | EFFECTIVE |

## 1. Command
python tools/run_real_data_playbook.py SERIES_DIR DATASET_ID [--dry-run]

## 2. Flow (all steps reuse validated tools)
1. Manifest built for the series.
2. Intake: QC gate (de-id, completeness, HU, contours) + selective
   sealing + append-only audit (P5-S3).
3. If ACCEPT: registered validation with multi-seed paired statistics,
   Wilcoxon and seed concordance (P5-S4).
4. Playbook artifact real_data_playbook_<ID>.json records the chain.

## 3. Decision Rules
- REJECT at intake halts the evidence chain; reason ledgered.
- ACCEPT without significance is reported honestly (no p-hacking).
- Batch flag fraction > 0.20 triggers CLIN-001 SUSPEND_AND_CAPA.

## 4. Traceability
DATA-ACQ-001, CLIN-001, ADR-005, ADR-007, RPT-001 v4.0.
