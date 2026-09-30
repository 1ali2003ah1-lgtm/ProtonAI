# TLM-001: Traceability Link Matrix

## Document Control
| ID | Version | Generated | Generator commit | Status |
|---|---|---|---|---|
| TLM-001 | 2.0 | 2026-09-30 22:39 UTC | 5ef113a | EFFECTIVE |

## 1. Method
Links are DISCOVERED from source text; required links and sibling coverage are enforced; core assets must be covered; docs fingerprinted (sha256-12). Gaps refuse generation.

## 2. Discovered Document-to-Document Matrix
| Source | NEXUS-PRD-001 | PRM-001 | USP-001 | MSS-001 | SVP-001 | REG-001 |
|---|---|---|---|---|---|---|
| NEXUS-PRD-001 | · | ✓ | ✓ | ✓ | ✓ | ✓ |
| PRM-001 | ✓ | · | ✓ | · | ✓ | ✓ |
| USP-001 | ✓ | ✓ | · | · | · | · |
| MSS-001 | ✓ | · | · | · | ✓ | ✓ |
| SVP-001 | ✓ | ✓ | · | ✓ | · | · |
| REG-001 | ✓ | ✓ | ✓ | · | ✓ | · |

## 3. Required Links (enforced)
- PRM-001->NEXUS-PRD-001; USP-001->PRM-001; USP-001->NEXUS-PRD-001; MSS-001->NEXUS-PRD-001; MSS-001->SVP-001; MSS-001->REG-001; SVP-001->NEXUS-PRD-001; SVP-001->PRM-001; SVP-001->MSS-001; REG-001->PRM-001; REG-001->USP-001; REG-001->SVP-001; REG-001->NEXUS-PRD-001; NEXUS-PRD-001->PRM-001; NEXUS-PRD-001->USP-001; NEXUS-PRD-001->MSS-001; NEXUS-PRD-001->SVP-001; NEXUS-PRD-001->REG-001

## 4. Core-Asset Coverage
| Asset | Referenced by |
|---|---|
| CLIN-001 | NEXUS-PRD-001, PRM-001, USP-001, REG-001 |
| CLIN-002 | NEXUS-PRD-001, PRM-001, USP-001 |
| ADR-006 | SVP-001 |
| ADR-007 | NEXUS-PRD-001, PRM-001, MSS-001, SVP-001, REG-001 |
| ADR-008 | NEXUS-PRD-001, PRM-001, REG-001 |
| PMS-001 | NEXUS-PRD-001, PRM-001, MSS-001, REG-001 |
| RPT-001 | NEXUS-PRD-001, PRM-001, SVP-001 |
| PLAYBOOK-001 | REG-001 |

## 5. Document Integrity Fingerprints
| Doc | sha256-12 |
|---|---|
| NEXUS-PRD-001 | 1ceca1dc0fc2 |
| PRM-001 | d8bc628dbd6c |
| USP-001 | 0f75447480ae |
| MSS-001 | a18945459106 |
| SVP-001 | a7b2817d127e |
| REG-001 | 84e8566aaae5 |

## 6. Notes
- 21 discovered links; 18 required; 8 core assets covered.
- Regenerate after any controlled-doc change.

## 7. Traceability
All six controlled docs + ADR/CLIN/PMS/RPT/PLAYBOOK assets.
