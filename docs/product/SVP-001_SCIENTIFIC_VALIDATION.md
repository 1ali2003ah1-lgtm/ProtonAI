# SVP-001: Scientific Validation Plan

## Document Control
| ID | Version | Generated | Generator commit | Status |
|---|---|---|---|---|
| SVP-001 | 1.0 | 2026-09-30 22:25 UTC | 7371a83 | EFFECTIVE |

## 1. Purpose
Convert platform evidence into peer-reviewed credibility; order: PAP-1 and PAP-2 in parallel now, PAP-3 after stages B and D.

## PAP-1: Content-hash sealing for reproducible medical AI evidence
- Target: Medical Physics / IEEE JBHI
- Status: evidence complete - write now
- Evidence: PROVENANCE_phase2/3, REPRO_BUNDLE.json, release_gate
- Statistics: hash verification, bootstrap CI

## PAP-2: Unified clinical confidence from AI and physics uncertainty for proton therapy segmentation
- Target: Physics in Medicine & Biology
- Status: evidence complete - write now
- Evidence: confidence_analysis_results.json, uq_analysis_results.json, inter_observer_study.json
- Statistics: Wilcoxon, bootstrap CI, Dice/HD95

## PAP-3: Clinical validation and dose impact of AI proton segmentation: a real-data study
- Target: Radiotherapy & Oncology
- Status: protocol - needs dose bridge (B) + real data (D)
- Evidence: dose_bridge (stage B), real-data playbook runs (stage D)
- Statistics: paired DVH deltas, TCP/NTCP

## 4. Integrity (non-negotiable)
- Preregister PAP-3 protocol before first real-data run.
- No p-hacking: primary endpoints fixed (Dice/HD95, paired DVH deltas).
- Negative results published as deviations, never hidden.

## 5. Traceability
NEXUS-PRD-001, PRM-001 (R-106), MSS-001, ADR-006, ADR-007, RPT-001 v4.0.
