"""Agents (Layer 3 / Layer 4 — population mechanics).

The population. Each agent is a (model x memory subset x prompt
structure x reasoning approach) tuple. Agents vary across all four
dimensions and compete on the evaluator scoreboard.

Two starting agent types in Phase 2:
  - pure_code: hand-coded Bayesian with hardcoded likelihoods, used
    ONLY for plumbing validation on the learning universe. Not the
    production agent shape.
  - model_driven: receives raw evidence, reasons natively, produces
    structured terminal output (belief over state + recommended
    expression + sizing + horizon-of-edge + uncertainty + memory
    updates). This IS the production agent shape (DESIGN.md #5, #6).

Per DESIGN.md #9: there is no single-agent commitment. Population is
the unit of search; selection is by evaluator scoreboard.

This is the top of the architectural pyramid — agents consume from
data/, evaluator/, beliefs/, llm/, memory/, never the reverse.
"""
