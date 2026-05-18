"""Tradable-Edge Action Engine (Layer 2 — verification side of v5).

Converts an agent's raw forecast into a gated action via two stages:

  1. **Calibration shrinkage** (`calibrator.py`, PYRAMID Stone 11c). Rewrite
     the agent's raw forecast `F_AI` toward per-signal-class empirical
     reliability from the Forecast Ledger, producing `F_AI_calibrated`.
     Empty Ledger = identity; dense Ledger = empirical overwrites raw.

  2. **Calibrated expected utility + margin-of-safety gate**
     (`action_engine.py`, PYRAMID Stone 11d — not yet built). Compute the
     Kelly-equivalent under `F_AI_calibrated` and the cost model. Emit a
     `TradeAction` only when calibrated expected utility clears the
     margin-of-safety threshold; otherwise emit `NoAction`.

Phase 1 NEW Cluster B scope. Cluster A built the Ledger (the empirical
anchor); Cluster B is the layer that turns Ledger reliability into action.

Architectural import boundary (DESIGN.md / import-linter):
  - This package is read by `agents/`, `cli/`.
  - This package MAY read `ledger/` (for empirical reliability), `data/`
    (for cost models when they land in Cluster C).
  - This package MUST NOT import from `agents/` or `baseline/`. The
    Market-State Baseline (`baseline/`, Cluster I) is structurally isolated;
    its processed forecast must never flow into the AI Core's action path.
"""
