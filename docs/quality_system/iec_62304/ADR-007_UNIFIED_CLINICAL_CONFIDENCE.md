# ADR-007: Unified clinical confidence score
Status: ACCEPTED

## Context
A clinician needs ONE conservative number per plan. ProtonAI has two
independent uncertainty sources: segmentation epistemic uncertainty
(seed-ensemble vote entropy, ADR-006) and dose physics uncertainty
(clinical range + MC statistical, mc_uncertainty.MCUncertainty).

## Decision
1. Model confidence = 1 - vote_entropy / ln(2)  (entropy in [0, ln 2]).
2. Physics confidence = 1 - combined relative uncertainty at E=150 MeV,
   N histories targeting 1% MC statistical error.
3. Unified confidence = model * physics (multiplicative conjunction,
   conservative AND: a weak layer cannot be compensated).
4. Threshold = minimum in-domain unified confidence (evidence-derived,
   mirror of CLIN-001 theta); confidence below threshold => physicist
   review per CLIN-001.
5. Additive module confidence_score.py; mc_uncertainty untouched.

## Consequences
- Single auditable number per plan; both components logged.
- Threshold recomputed only under change control (CLIN-001 governance).
