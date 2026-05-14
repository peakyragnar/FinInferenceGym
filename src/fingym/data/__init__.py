"""Data spine (Layer 0).

Immutable, point-in-time, versioned data. The single source of truth for
the six explicit data types: raw emissions, derived features, beliefs,
actions, labels, scores. Every record carries as_of, as_known, source,
version, and corpus_bias (when applicable).

Live feed and historical replay are structurally identical pipelines —
only the as-of date moves. Trajectory store is in SFT-fit format from
day 1 (DESIGN.md #8 — year-2 own-model path).

Architectural import boundary (DESIGN.md / import-linter):
  - This package is read by evaluator/, beliefs/, agents/, cli/.
  - This package MUST NOT import from those layers. Data is read by
    upper layers, never the reverse.
  - The model interface (DESIGN.md #6) requires that data is delivered
    raw — no pre-engineered features at this layer.
"""
