# REG-001: Regulatory Strategy (FDA 510(k) + CE MDR)

## Document Control
| ID | Version | Generated | Generator commit | Status |
|---|---|---|---|---|
| REG-001 | 2.0 | 2026-09-30 22:32 UTC | 002a889 | EFFECTIVE |

## 1. Classification Justification
SaMD providing diagnostic/therapeutic suggestions to clinicians (physicists/oncologists) for proton contour review. Does NOT autonomously set dose; final approval is human. Under MDR Rule 11: Class IIa (decisions with diagnostic/therapeutic purpose). FDA: Class II (21 CFR 892.2050 - medical image processing) via 510(k) predicate.

## 2. Predicate Analysis (FDA substantial equivalence)
| Predicate | Manufacturer | Clearance | Similarity | Our differentiation |
|---|---|---|---|---|
| RayStation AI Contouring | RaySearch Laboratories | CE MDR Class IIa; FDA 510(k) K222953 | auto-contouring + TPS integration | no open evidence chain, no unified confidence, no exposed PMS loop |
| Limbus AI | Limbus Medical AI | Health Canada, CE, FDA 510(k) | fast contouring AI for RT | no AI x physics unified score |

## 3. GSPR Table (MDR Annex I)
| GSPR | Platform asset |
|---|---|
| GSPR 1 - General safety | PRM-001 + PMS-001 |
| GSPR 8 - Software lifecycle | repo ADRs + release gate + versioned tags |
| GSPR 9 - Electronic programmable systems | ADR-008 + ADR-007 |
| GSPR 10 - Measurement functions | ADR-007 + confidence display |
| GSPR 14 - Information supplied with device | IFU + NEXUS UI + MODEL_CARD |
| GSPR 17 - Cybersecurity | de-id gate + ISO 27001 plan |
| GSPR 18 - Interoperability | DICOM reader + playbook integration |
| GSPR 21 - Protection against risks to patients | CLIN-001 + interlock |

## 4. UDI Path
- UDI-DI (device identifier) from issuing entity (e.g. GS1)
- UDI-PI (production identifier) per batch/version
- Registration in EUDAMED (EU) and GUDID (FDA)
- Labeling per MDR Annex VI / 21 CFR 830

## 5. Cybersecurity File (FDA 2023 Guidance)
- SBOM (software bill of materials) auto-generated
- Vulnerability disclosure policy (public)
- Patching SLA: critical <72h, high <14d
- Penetration testing pre-release
- Encrypted data at rest + in transit (TLS 1.3)
- Authentication (Keycloak) + audit log (immutable)

## 6. Post-Market Clinical Follow-up (PMCF)
- Annual review of real-data playbook ledger (PMS-001)
- User feedback aggregation from NEXUS console
- Post-market clinical follow-up survey (yearly, 30+ users)
- Re-evaluation of SVP-001 PAP-3 claims as data grows
- Trigger re-validation on model version change (ADR-008)

## 7. FDA Path
1. Pre-Submission (Q-Sub) meeting
2. Predicate analysis & substantial equivalence
3. 510(k) submission (eSTAR preferred)
4. Interactive review (90 days)
5. Clearance + GUDID registration

## 8. CE MDR Path
1. QMS ISO 13485 certification (Notified Body)
2. Technical documentation (Annex II/III)
3. GSPR conformity assessment
4. Clinical evaluation report (CER)
5. Notified Body audit
6. CE marking + EUDAMED registration

## 9. Timeline
| Window | Milestone |
|---|---|
| T0-T3m | ISO 13485 gap assessment + HFE formative (USP-001) |
| T3-T6m | ISO 13485 certification + UDI assignment |
| T6-T9m | Q-Sub + predicate analysis + SBOM |
| T9-T15m | clinical data (PAP-3) + 510(k) submission |
| T15-T21m | CE NB audit + clearance interaction |
| T21-T24m | CE marking + FDA clearance + EUDAMED/GUDID |

## 10. Honest Gaps
- real clinical data (stage D / PAP-3)
- ISO 13485 certificate (certification pending)
- Notified Body contract (BSI / TÜV / DEKRA)
- summative HFE study (post-formative)
- clinical evaluation report (CER) drafting
- UDI issuing entity agreement (GS1)
- FDA eSTAR template completion
- SBOM generator integration

## 11. Traceability
PRM-001, USP-001, PMS-001, SVP-001, NEXUS-PRD-001, ADR-007, ADR-008, IEC 62304, ISO 14971, IEC 62366-1, ISO 20416, MDR 2017/745, 21 CFR 807, FDA Cybersecurity Guidance 2023.
