# CLIN-002: Clinical Decision Dashboard

## Document Control
| ID | Version | Generated | Generator commit | Status |
|---|---|---|---|---|
| CLIN-002 | 2.0 | 2026-09-30 03:27 UTC | dde1d82 | EFFECTIVE |

## 1. Executive KPIs
| KPI | Value |
|---|---|
| physics confidence | 0.963599 |
| theta (entropy) | 0.002382 |
| threshold C | 0.960288 |
| separation margin | 0.00593160526443647 |
| failures captured | True |
| urgent entropy | 0.0198191848529466 |
| cross flag rate | 1.00 |

## 2. Batch decision states
| Scope | Cases | Flagged | Batch state |
|---|---|---|---|
| in_domain | 8 | 0 | AUTO |
| cross_domain | 8 | 8 | SUSPEND_AND_CAPA |

## 3. Per-case triage (cross-domain)
| Case | entropy | confidence | flag | triage | review |
|---|---|---|---|---|---|
| cross_domain-0 | 0.008643 | 0.951585 | True | REVIEW | physicist |
| cross_domain-1 | 0.013138 | 0.945336 | True | REVIEW | physicist |
| cross_domain-2 | 0.011714 | 0.947315 | True | REVIEW | physicist |
| cross_domain-3 | 0.008314 | 0.952042 | True | REVIEW | physicist |
| cross_domain-4 | 0.005538 | 0.955901 | True | REVIEW | physicist |
| cross_domain-5 | 0.012080 | 0.946806 | True | REVIEW | physicist |
| cross_domain-6 | 0.010344 | 0.949219 | True | REVIEW | physicist |
| cross_domain-7 | 0.019819 | 0.936047 | True | URGENT | physicist |

## 4. Traceability
CLIN-001 (flagging), ADR-006 (UQ), ADR-007 (confidence),
RPT-001 v4.0; history: clinical_dashboard_history.json.
