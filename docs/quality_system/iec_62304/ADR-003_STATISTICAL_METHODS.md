# ADR-003: Statistical methods for experiment evaluation
Status: ACCEPTED

## Context
Scientific claims require statistical evidence, not just point estimates.
ProtonAI experiments must demonstrate that observed differences are
real, not random noise.

## Decision
Use three complementary methods:

1. **Wilcoxon signed-rank test** (non-parametric, paired)
   - Appropriate for small samples (n < 30)
   - Does not assume normality
   - Tests whether differences are systematically positive
   - Significance threshold: p < 0.05

2. **Bootstrap 95% confidence interval** (10,000 resamples)
   - Quantifies uncertainty in the mean difference
   - If CI excludes 0, difference is robust
   - Seed-fixed for reproducibility

3. **Multi-seed robustness check** (seeds: 42, 123, 999)
   - Tests whether result depends on weight initialization
   - All seeds must agree on verdict for "robust" label

## Consequences
- Claims are defensible against peer review
- Small deltas (+0.0006) can be proven real if consistent
- Negative results are also valuable (published as "no improvement")
