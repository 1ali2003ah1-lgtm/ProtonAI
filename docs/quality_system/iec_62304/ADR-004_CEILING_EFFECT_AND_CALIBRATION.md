# ADR-004: Ceiling effect discovery and difficulty calibration
Status: ACCEPTED

## Context
Through the validated ingestion path (v0.2.0), SYNTH-001 saturated at
Dice = 1.0 for both arms (delta 0.0, "NO IMPROVEMENT"): integer HU
quantization plus high-contrast circular lesions made the task too easy
to discriminate loss functions. An experiment that cannot fail cannot
succeed.

## Decision
1. Calibrate a harder phantom (SYNTH-002): contrast +80 HU, background
   noise sigma=25, irregular multi-blob lesions, smooth bias field.
2. Treat discriminative power (baseline mean < 1.0) as a precondition
   for any model-comparison claim.
3. Official evidence = committed artifacts pipeline_experiment_synth002.json
   and experiment_statistics_synth002.json, sealed by
   docs/experiments/PROVENANCE_synth002.json (sha256). Interactive
   BCa/Shapiro exploration is supplementary only.

## Evidence (SYNTH-002)
- Baseline mean Dice 0.9769 (std 0.0087); Experiment 0.9815 (std 0.0019)
- Delta +0.004628; Wilcoxon one-sided p = 0.03125 (< 0.05)
- Bootstrap 95% CI excludes 0 (bounds in committed JSON)
- Seeds 42/123/999: all SUPPORTED (robust)
- Final: STRONG EVIDENCE: HYPOTHESIS SUPPORTED
- Secondary finding: Dice+CE reduces cross-case variance
  (std 0.0087 -> 0.0019): consistency gain, clinically relevant.

## Consequences
- SYNTH-001 remains for ingestion verification only (ADR-001).
- Future evaluation datasets must pass a discriminative-power check
  before verdicts are interpreted (risk R-008, CAPA-001).
