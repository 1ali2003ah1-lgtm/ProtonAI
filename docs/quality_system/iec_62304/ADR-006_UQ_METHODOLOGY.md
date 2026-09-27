# ADR-006: Model-layer uncertainty quantification via seed ensembles
Status: ACCEPTED

## Context
Clinical deployment requires flagging unreliable segmentations. Validated
segmenters expose no probabilities and must not be architecturally
modified (regression risk). mc_uncertainty.MCUncertainty covers the
PHYSICS layer (proton range / MC histories), not model epistemic
uncertainty.

## Decision
1. Epistemic uncertainty = seed-ensemble disagreement (K=5): pixel-wise
   vote fraction p; uncertainty = mean binary entropy H(p).
2. Informative criteria: Spearman rho(uncertainty, error) > 0 with
   p < 0.05, or failure-prediction AUC >= 0.7 (failure: Dice < 0.97).
3. OOD sensitivity: cross-domain uncertainty > in-domain
   (Mann-Whitney one-sided, p < 0.05).
4. Physics-layer MC uncertainty remains MCUncertainty; combined clinical
   confidence is Phase-4 work.

## Consequences
- No changes to validated modules; UQ is an analysis layer.
- Silent failure risk (R-010) mitigated: high-uncertainty cases are
  flagged for physicist review in the clinical workflow.
