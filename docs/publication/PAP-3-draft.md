# PAP-3 Draft Manuscript (v0.1)

## Document Control
| ID | Version | Date | Status |
|---|---|---|---|
| PAP-3 | 0.1 | 2026-10-04 | DRAFT |

## Authors & Affiliations
[First Author]^1, [Co-Author]^2, [Corresponding Author]^1*
1. ProtonAI Project. 2. [Partner Institution].
*Corresponding: [email].

## Abstract
(see ABSTRACT-001)

## 1. Introduction
Proton dose is sensitive to range/contour uncertainty; manual contouring
is variable. We quantify the dosimetric/radiobiological impact of an open,
auditable AI contouring-assistance platform.

## 2. Methods
Weight-optimized SOBP surrogate with clinical margins + range-uncertainty
worst case (B1); paired DVH deltas with bootstrap CI + Wilcoxon + NI margin
0.02 (B2); logistic TCP and LKB NTCP (B3).

## 3. Results
| Endpoint | Delta | CI | p | Verdict |
|---|---|---|---|---|
| D95 | 0.061 | [0.061,0.061] | 0.0039 | SUPERIOR |
| dTCP | +0.123 | - | - | benefit |
| dNTCP | 0.5637 | - | - | sparing |

## 4. Discussion
Improved coverage and sparing translate into higher TCP / lower NTCP.

## 5. Limitations
Synthetic water phantoms; surrogate dose; real-patient validation pending.
NOT for clinical use.

## Figure/Table Plan
Fig 1: DVH paired curves. Fig 2: TCP/NTCP deltas. Table 1: endpoints.

## References
1. Lyman JT. Complication probability as assessed from dose-volume
   histograms. Radiat Res. 1985;104(2):S319-S324.
2. Schneider U, Pedroni E, Lomax A. The calibration of CT Hounsfield units
   for radiotherapy treatment planning. Phys Med Biol. 1996;41(1):111-124.
3. Niemierko A. Reporting and analyzing dose distributions: a concept of
   equivalent uniform dose. Med Phys. 1997;24(1):103-110.
4. Paganetti H. Proton Therapy Physics. CRC Press; 2012.

## Traceability
RPT-001 v4.0, DOSE-IMPACT-001, SVP-001, NEXUS-PRD-001.

## Ethics Statement
All current evidence uses synthetic phantoms; no human subjects or
identifiable data were used. The real-data phase requires IRB/ethics
approval and a signed data-sharing agreement (see docs/partnership/).

## Data Availability
Synthetic phantom generators, code, and artifacts are publicly available at
https://github.com/1ali2003ah1-lgtm/ProtonAI and archived via DOI
10.5281/zenodo.23147530.

## Conflicts of Interest
The author declares no conflict of interest.

## Funding
No external funding was received for this work.

## Author Contributions & ORCID
Ali Hussein Thajil (CRediT): conceptualization, methodology, software,
validation, writing. ORCID: [FILL-ORCID].

## Limitations
Synthetic pretraining; constant RBE=1.1; surrogate-to-clinical transfer
pending real-data validation; single-institution initial scope.

## Statistical Analysis
Paired Wilcoxon signed-rank with bootstrap confidence intervals; alpha=0.05;
power considerations documented in docs/publication/.

## Reporting Guideline Compliance
Reported per CLAIM 2024 and TRIPOD+AI checklists for AI-based medical
imaging prediction models.

## Protocol Registration
Analysis protocol and synthetic phantom generators archived on Zenodo
(DOI 10.5281/zenodo.23147530); no prospective registration applies to the
synthetic phase.
