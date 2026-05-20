"""RealBaselineAgent — Market-State Baseline (Track C) wrapper that emits v5 Contracts.

The Baseline is information-poor by design (PYRAMID Stone 11e). It sees
only the 7-series macro state — never company-specific evidence — and
emits a forecast distribution over realized return buckets via its
trained Bayesian Ledger.

This wrapper takes a trained RealMarketStateBaseline and produces v5
Contracts on the same (ticker, decision_date) shape as the AI Core's
RealLlmAgent. Saved alongside AI Contracts in the trajectory store, the
two are paired by (ticker, decision_date) for Track C `incremental_AI_edge`
attribution.

PIT note: training the Baseline before deploying it on historical decision
dates introduces look-ahead bias if the training set includes realizations
whose horizon extends beyond the decision date. For v1 we train once on
the full available history and accept this leak — the AI Core gets the
same benefit when re-trained on full history, and the comparison stays
apples-to-apples per (ticker, decision_date). Proper time-walk training
(retrain at each decision date) is future work when the replay scales.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import psycopg

from fingym.agents.contract import (
    CognitiveStep,
    Contract,
    EvidenceRef,
    Falsifier,
    ForecastDistribution,
    NoAction,
    RealizedReturnPlan,
    TradeAction,
)
from fingym.baseline.real_market_state import (
    REAL_BASELINE_AGENT_ID,
    RealMarketStateBaseline,
)
from fingym.data.queries.equity_returns import RETURN_BUCKETS

# Midpoints used to compute expected return from the bucketed distribution.
# Matches the convention in src/fingym/agents/real_agent.py.
_BUCKET_MIDPOINTS: dict[str, float] = {
    "below_minus_5": -0.08,
    "minus_5_to_0": -0.025,
    "zero_to_plus_5": 0.025,
    "plus_5_to_plus_10": 0.075,
    "above_plus_10": 0.12,
}


def _load_macro_state_for_baseline(
    conn: psycopg.Connection[Any],
    decision_date: date,
    series_order: tuple[str, ...],
) -> dict[str, Decimal]:
    """Load latest known value per Baseline series at decision_date.

    Filter on as_of <= decision_date because the Baseline-input series
    don't materially revise (see src/fingym/agents/real_agent.py for the
    same PIT correction)."""
    state: dict[str, Decimal] = {}
    with conn.cursor() as cur:
        for series_id in series_order:
            cur.execute(
                """
                SELECT value FROM headline_observables
                WHERE series_id = %s AND as_of <= %s AND value IS NOT NULL
                ORDER BY as_of DESC, vintage DESC LIMIT 1
                """,
                (series_id, decision_date),
            )
            row = cur.fetchone()
            if row:
                state[series_id] = row[0]
    return state


class RealBaselineAgent:
    """Baseline agent producing v5 Contracts.

    Stateless after construction (the trained Bayesian Ledger lives in
    the wrapped RealMarketStateBaseline). One Contract per call. Same
    (ticker, decision_date) interface as RealLlmAgent so Track C
    attribution is a direct join on those keys.
    """

    def __init__(
        self,
        baseline: RealMarketStateBaseline,
        horizon_days: int = 30,
    ) -> None:
        self.baseline = baseline
        self.horizon_days = horizon_days

    def forecast_for(
        self,
        conn: psycopg.Connection[Any],
        ticker: str,
        decision_date: date,
    ) -> Contract:
        macro_state = _load_macro_state_for_baseline(
            conn, decision_date, self.baseline.series_order
        )
        forecast = self.baseline.forecast(macro_state)

        decision_ts = datetime(
            decision_date.year,
            decision_date.month,
            decision_date.day,
            21,
            0,
            0,
            tzinfo=UTC,
        )

        forecast_dist = ForecastDistribution(probabilities=dict(forecast))

        # Evidence refs: only macro series (Baseline doesn't see prices /
        # corporate actions / news / fundamentals). This is the structural
        # information-poor commitment.
        evidence_refs: list[EvidenceRef] = []
        for series_id in self.baseline.series_order:
            if series_id in macro_state:
                evidence_refs.append(
                    EvidenceRef(
                        row_id=f"macro:{series_id}:{decision_date}",
                        as_known=decision_ts,
                        source="FRED",
                    )
                )

        # Signal class — Baseline's tag is deterministic from the macro
        # state bucket vector. Format: "baseline:LLLLLHHH" where each
        # character is L/H per series in canonical order.
        bucketed = []
        for series_id in self.baseline.series_order:
            val = macro_state.get(series_id)
            cp = self.baseline.cutpoints.get(series_id)
            if val is None or cp is None:
                bucketed.append("?")
            else:
                bucketed.append("L" if val < cp else "H")
        signal_class_id = "baseline:" + "".join(bucketed)

        expected_log_return = sum(
            forecast.get(b, 0.0) * _BUCKET_MIDPOINTS[b] for b in RETURN_BUCKETS
        )

        recommended_action: TradeAction | NoAction
        recommended_size = 0.0
        if expected_log_return > 0.0:
            recommended_action = TradeAction(
                expression_type="equity-long",
                underlying=ticker,
                direction="long",
                size=1,
                notional=1000.0,
            )
            recommended_size = 0.05
        elif expected_log_return < 0.0:
            recommended_action = TradeAction(
                expression_type="equity-short",
                underlying=ticker,
                direction="short",
                size=1,
                notional=1000.0,
            )
            recommended_size = 0.05
        else:
            recommended_action = NoAction(reason="baseline_expected_return_zero")

        cognitive_step = CognitiveStep(
            step_index=0,
            initial_forecast=forecast_dist,
            additional_reasoning="",
            updated_forecast=forecast_dist,
            action_changed=False,
        )

        return Contract(
            contract_id=str(uuid.uuid4()),
            decision_time=decision_ts,
            agent_id=REAL_BASELINE_AGENT_ID,
            model_id="market_state_bayesian_ledger_v1",
            prompt_version="baseline_n_dim_2bucket_median_v1",
            evidence_ids=evidence_refs,
            data_sources_used=["headline_observables"],
            forecast_distribution=forecast_dist,
            signal_class_id=signal_class_id,
            thesis_category=(
                "Information-poor macro baseline. Conditioned only on the "
                "7-series headline observables bucketed at median split."
            ),
            horizon=f"{self.horizon_days}d",
            recommended_action=recommended_action,
            recommended_size=recommended_size,
            falsifiers=[
                Falsifier(
                    description=(
                        f"Realized log return of {ticker} at {self.horizon_days}d "
                        "falls in a bucket the Baseline assigned <5% probability"
                    ),
                )
            ],
            realized_return_plan=RealizedReturnPlan(
                horizon=f"{self.horizon_days}d",
                labelling_function="adjusted_close_log_return",
                return_type="log",
                point_in_time_anchor=decision_ts,
            ),
            cognitive_audit_trail=[cognitive_step],
            memory_update_proposal=None,
        )


__all__ = ["RealBaselineAgent"]
