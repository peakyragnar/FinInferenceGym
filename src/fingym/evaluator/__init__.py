"""Evaluator (Layer 1).

The load-bearing primitive (DESIGN.md #1). Scores beliefs and actions
against time-revealed labels using proper scoring rules. Produces a
scoreboard (vector of metrics), not a single scalar.

Tracks: calibration (Brier, log score), process quality (Bayesian-update
vs price-chasing), decision-changing information per dollar (cost-aware
VoI), edge at deployable size (impact-adjusted), compound growth and
drawdown discipline (Kelly-objective), out-of-sample stability across
holdout / regime / sector / time splits.

Multi-horizon scoring from day 1: 1m / 3m / 6m / 1y in parallel (plus
shorter for toys). Action-space-aware: each action tagged with
expression_type (equity-long, option-call, vol-long, pair, etc.) and
per-expression performance tracked separately.

Architectural import boundary (DESIGN.md / import-linter):
  - This package is read by agents/, cli/.
  - This package MUST NOT import from agents/, beliefs/, llm/, memory/.
"""
