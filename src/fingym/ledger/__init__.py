"""Forecast Ledger (Layer 2 — verification side of v5).

The empirical anchor for calibration. Records every (forecast, realized
return) pair indexed by signal class, and computes per-signal-class
empirical reliability: "when the agent claims X% in signal class Y for
bucket B, what fraction of those forecasts realized B?"

This is the v5 commitment #2 made concrete on the verification side: the
agent's raw forecast is not trusted; it is anchored to the agent's own
historical claimed-vs-realized track record per signal class. The
Tradable-Edge Action Engine (Phase 1 NEW Cluster B, `src/fingym/action/`)
consumes this Ledger to shrink raw forecasts toward empirical reliability.

Phase 1 NEW Cluster A scope (Stone 11b): in-memory append-only MVP. The
real-data version (Phase 2 NEW) writes through the data spine (`forecasts`
+ `realized_returns` tables) and presents the same read API.

Architectural import boundary (DESIGN.md / import-linter):
  - This package is read by agents/, action/, evaluator/, cli/.
  - This package MUST NOT import from agents/, action/.
"""
