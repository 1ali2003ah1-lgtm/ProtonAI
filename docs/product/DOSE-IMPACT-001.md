# DOSE-IMPACT-001: Dose-Impact Study Report (synthetic)

## Document Control
| ID | Version | Generated | Status |
|---|---|---|---|
| DOSE-IMPACT-001 | 1.0 | 2026-10-01 23:53 UTC | EFFECTIVE |

## 1. Objective
Quantify whether AI contouring yields a better proton dose than the
baseline segmenter, evaluated on ground truth.

## 2. Methods
Paired DVH deltas (B2) on D95 + OAR-V20 with bootstrap CI and one-sided
Wilcoxon; radiobiology translation (B3) via logistic TCP and LKB NTCP.
Non-inferiority margin 0.02. Dose surrogate scaled to 60.0 Gy.

## 3. Results
| Endpoint | Mean delta | CI | p | Verdict |
|---|---|---|---|---|
| D95 | 0.061 | [0.061,0.061] | 0.0039 | SUPERIOR |
| OAR V20 | 0.000 | [0.000,0.000] | 1.0000 | NON_INFERIOR |
| dTCP | 0.123 | - | - | benefit |
| dNTCP | 0.5637 | - | - | sparing |

## 4. Methodology Decision (ADR-equivalent)
Dose bridge is a physics-motivated surrogate (B1); weight-optimized SOBP;
clinical margins; range uncertainty worst-case. Superseded by TOPAS/MC
for clinical dose.

## 5. Limitations
Synthetic water phantoms; ct-conditioning v2 pending; real data pending.

## 6. Conclusion
AI contouring preserves/improves target coverage and is non-inferior on OAR sparing over baseline on synthetic phantoms; real-data confirmation pending (Stage D).

## 7. Traceability
B1 dose_bridge, B2 dose_stats, B3 tcp_ntcp, SVP-001 (PAP-3), RPT-001 v4.0.
