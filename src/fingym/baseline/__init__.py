"""Market-State Baseline — Track C attribution (PYRAMID Stone 11e).

The ONLY module in the codebase that consumes headline observables and
emits a forecast distribution from them in isolation. The AI Core, the
agent layer, the memory pyramid, the action engine, the forecast ledger,
and the evaluator MUST NOT import from this package — see
`mechanisms/lints/no_baseline_imports.py` for the structural rule.

The Baseline runs the same Action Engine + structured cost model +
realized_edge pipeline as the AI; the only difference is what it
consumes (3 macro observables vs. the full emission stream) and where
the rows land on the Scoreboard (`agent_id="market_state_baseline"`).

`Scoreboard.incremental_AI_edge(ai_agent_id, baseline_agent_id)` is the
attribution helper that subtracts the Baseline's mean realized_edge from
the AI's. That difference — not the AI's absolute edge — is the only
honest answer to "is the AI doing real work?"

Submodules:
  - market_state: `MarketStateBaseline` class — Bayesian Ledger over
    headline-observable buckets.

Architectural import boundary:
  - This package is read by NOTHING upstream. Code outside this package
    cannot import from it (enforced by the no-baseline-imports lint).
  - This package does import from fingym.toys.synthetic_market (the
    `HeadlineObservables` and `ReturnBucket` types live there) and from
    fingym.ledger.forecast_ledger (reuses the ForecastOverBuckets type).
    Those are downstream-of-baseline-input shapes, not the AI's outputs.
"""
