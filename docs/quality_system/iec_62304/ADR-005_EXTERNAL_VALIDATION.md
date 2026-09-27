# ADR-005: External validation methodology for model comparison
Status: ACCEPTED

## Context
In-domain evaluation alone cannot distinguish a model that understands
the task from one that memorizes the training distribution. For a SaMD
platform, generalization claims require external validation.

## Decision
1. **Two-direction cross-domain evaluation**:
   - S1->S2 (easy->hard): model must generalize to harder distribution.
   - S2->S1 (hard->easy): model must not collapse on simpler distribution.
   Symmetry breaks the trivial "train easy, test hard" single-direction claim.
2. **Paired analysis**: per-slice gap difference between models, tested
   with a paired permutation test (n=10,000 resamples) — stronger than
   independent-sample tests for n=8 slices.
3. **Multi-seed robustness** (seeds 42/123/999) to rule out initialization
   artifacts.
4. **Bootstrap 95% CI** on gap differences (1,000 resamples of slices).
5. **Generalization gap** = in_domain(target) − cross(train→target).
   Smaller gap = better generalizer (understands, not memorizes).

## Consequences
- Claims of "better generalization" require BOTH directions to favor the
  model AND at least one to be statistically significant (STRONG verdict).
- Consistent-but-not-significant results get MODERATE label (honest
  reporting; no p-hacking).
- Single-direction results get MIXED label (weaker evidence).
