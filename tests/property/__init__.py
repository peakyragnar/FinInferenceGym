"""Property-based tests using hypothesis.

Math invariants that must hold for any implementation:
  - Bayesian update commutativity (order of evidence doesn't matter
    for the final posterior, given conditional independence)
  - Brier and log score properness (optimal under reporting true
    belief)
  - Kelly fraction monotonicity in edge
  - Compound asymmetry math (drawdown D requires gain D/(1-D))

Per BUILD.md Phase 0 exit criterion: property tests must demonstrate
these invariants before any higher layer depends on them.
"""
