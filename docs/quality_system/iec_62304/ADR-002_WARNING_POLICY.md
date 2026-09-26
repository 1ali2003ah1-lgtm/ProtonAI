# ADR-002: Third-party deprecation warnings are tracked, never suppressed
Status: ACCEPTED

## Context
The full pytest suite surfaces warnings originating from SOUP components
(pydicom, scikit-learn). First-party code must be warning-free; SOUP
warnings cannot be fixed inside ProtonAI.

## Decision
- First-party code: zero warnings enforced; any new ProtonAI warning is
  a defect (SDLC_PLAN section 5).
- SOUP warnings: never suppressed via pytest filters; tracked in
  SOUP_REGISTER with upgrade plans (e.g., pydicom v4 migration for the
  is_implicit_VR / is_little_endian deprecations).
- Historical IDE warning on monte_carlo_physics.py: environment-specific,
  non-reproducible in current environment (Problems = 0, grep = empty).
  Closed as non-issue with this record.

## Consequences
- Warning visibility preserved (safety signal for a SaMD).
- SOUP upgrade work is planned and visible, not hidden.
