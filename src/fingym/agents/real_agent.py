"""RealLlmAgent — real AI Core (Stone 28 raw-evidence channel, Phase 2 NEW Step 2).

Reads real evidence at decision time from Postgres (macro state from
headline_observables, recent price history from equity_prices, corporate
actions, ticker reference), formats as natural language, calls Anthropic
via tool-call structured output, and emits a valid v5 Contract.

Under deterministic-first scope (real_data_ingest.md), the AI Core sees
only deterministic data for now: prices + macro + corporate actions +
ticker reference. Fundamentals / transcripts / news are deferred to
later stages with their own design passes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
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
from fingym.data.queries.equity_returns import RETURN_BUCKETS
from fingym.data.queries.headline_observables import BASELINE_SERIES
from fingym.llm.anthropic import AnthropicClient
from fingym.llm.contract import ForecastResponse

REAL_AGENT_ID = "real_llm_v1"
DEFAULT_HORIZON_DAYS = 30
DEFAULT_PRICE_LOOKBACK_DAYS = 60
DEFAULT_CORP_ACTION_LOOKBACK_DAYS = 180

# Series labels for the LLM prompt (human-readable; the IDs go to the Ledger).
_SERIES_LABELS: dict[str, str] = {
    "DFF": "Daily Federal Funds rate (%)",
    "DGS10": "10-Year Treasury yield (%)",
    "T10Y2Y": "10Y minus 2Y Treasury spread (%)",
    "T5YIFR": "5-Year 5-Year forward inflation expectation (%)",
    "VIXCLS": "CBOE VIX",
    "DTWEXBGS": "Broad US dollar index",
    "DCOILWTICO": "WTI crude oil ($/bbl)",
}

_REAL_SYSTEM_PROMPT = """\
You are a financial analyst forecasting an equity's realized log return
at a fixed horizon.

You will be given:
  - The TARGET TICKER and the DECISION DATE.
  - The current MACRO STATE (rates, vol, FX, oil, inflation expectations).
  - RECENT PRICE HISTORY for the target (daily OHLCV, most recent first).
  - Any CORPORATE ACTIONS in the lookback window (splits, dividends).
  - TICKER METADATA (name, exchange, listing status).

You must ALWAYS call the `submit_forecast` tool with:
  - `distribution`: probability over five log-return buckets at horizon:
        below_minus_5     (< -5%)
        minus_5_to_0      (between -5% and 0%)
        zero_to_plus_5    (between 0% and +5%)
        plus_5_to_plus_10 (between +5% and +10%)
        above_plus_10     (> +10%)
    Values must sum to exactly 1.
  - `signal_class_id`: a short slug naming THIS KIND of forecast (your
    own categorization). The verifier tracks empirical reliability under
    this tag over many forecasts. Examples: "macro_low_rates_high_vol_tech",
    "post_split_continuation", "delisted_endgame". Invent and evolve.
  - `thesis_category`: 1-2 sentences summarizing your view. For audit.

OPTIONALLY call `propose_memory_item` only when you've identified a
generalizable pattern worth promoting to long-term memory.

Important constraints:
  - Reason from the evidence you're shown. Do not assume facts not
    in the evidence (no insider knowledge, no future information).
  - Calibrate honestly. If the evidence is ambiguous, a flatter
    distribution is correct. If it's clear, concentrate appropriately.
  - This is a REAL forecast; the system will score your distribution
    against actual realized returns at horizon."""


@dataclass(frozen=True)
class PriceBar:
    date: date
    open_: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True)
class CorporateAction:
    date: date
    kind: str  # 'split' or 'dividend'
    detail: str  # e.g., '4-for-1' or '$1.05/share'


@dataclass(frozen=True)
class TickerMeta:
    ticker: str
    name: str | None
    primary_exchange: str | None
    active: bool
    delisted_utc: datetime | None


@dataclass(frozen=True)
class RealEvidence:
    ticker: str
    decision_date: date
    macro_state: dict[str, Decimal]
    price_history: list[PriceBar]
    corporate_actions: list[CorporateAction]
    ticker_meta: TickerMeta


def _load_macro_state(conn: psycopg.Connection[Any], decision_date: date) -> dict[str, Decimal]:
    """Load the latest known value per BASELINE_SERIES at decision_date.

    PIT note: Baseline-input series (DFF/DGS10/T10Y2Y/T5YIFR/VIXCLS/DTWEXBGS/
    DCOILWTICO) are daily market data that does not revise materially. Filter
    by as_of (not as_known) because FRED's realtime_start for non-revised
    series collapses to the ingest date — wrong as a PIT proxy. as_of is the
    correct anchor for non-revised market data.
    """
    state: dict[str, Decimal] = {}
    with conn.cursor() as cur:
        for series_id in BASELINE_SERIES:
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


def _load_price_history(
    conn: psycopg.Connection[Any], ticker: str, decision_date: date, lookback_days: int
) -> list[PriceBar]:
    earliest = decision_date - timedelta(days=lookback_days)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT as_of, open, high, low, close, volume
            FROM equity_prices
            WHERE ticker = %s AND as_of BETWEEN %s AND %s
            ORDER BY as_of DESC
            """,
            (ticker, earliest, decision_date),
        )
        rows = cur.fetchall()
    return [
        PriceBar(date=r[0], open_=r[1], high=r[2], low=r[3], close=r[4], volume=r[5] or 0)
        for r in rows
    ]


def _load_corporate_actions(
    conn: psycopg.Connection[Any], ticker: str, decision_date: date, lookback_days: int
) -> list[CorporateAction]:
    earliest = decision_date - timedelta(days=lookback_days)
    out: list[CorporateAction] = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ex_date, split_from, split_to FROM corporate_actions_splits
            WHERE ticker = %s AND ex_date BETWEEN %s AND %s
            ORDER BY ex_date DESC
            """,
            (ticker, earliest, decision_date),
        )
        for r in cur.fetchall():
            out.append(CorporateAction(date=r[0], kind="split", detail=f"{r[1]}:{r[2]}"))
        cur.execute(
            """
            SELECT ex_date, cash_amount FROM corporate_actions_dividends
            WHERE ticker = %s AND ex_date BETWEEN %s AND %s
            ORDER BY ex_date DESC
            """,
            (ticker, earliest, decision_date),
        )
        for r in cur.fetchall():
            out.append(CorporateAction(date=r[0], kind="dividend", detail=f"${r[1]}/share"))
    return sorted(out, key=lambda a: a.date, reverse=True)


def _load_ticker_meta(conn: psycopg.Connection[Any], ticker: str) -> TickerMeta:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ticker, name, primary_exchange, active, delisted_utc
            FROM tickers WHERE ticker = %s
            ORDER BY snapshot_date DESC LIMIT 1
            """,
            (ticker,),
        )
        row = cur.fetchone()
    if row is None:
        return TickerMeta(
            ticker=ticker, name=None, primary_exchange=None, active=True, delisted_utc=None
        )
    return TickerMeta(
        ticker=row[0],
        name=row[1],
        primary_exchange=row[2],
        active=bool(row[3]),
        delisted_utc=row[4],
    )


def load_evidence(
    conn: psycopg.Connection[Any],
    ticker: str,
    decision_date: date,
    price_lookback_days: int = DEFAULT_PRICE_LOOKBACK_DAYS,
    corp_action_lookback_days: int = DEFAULT_CORP_ACTION_LOOKBACK_DAYS,
) -> RealEvidence:
    """Load all evidence for one (ticker, decision_date) at PIT.

    All data filters use as_of <= decision_date. For our Baseline series
    (non-revised daily market data), as_of is the honest PIT anchor;
    as_known would be wrong because FRED's realtime_start for non-revised
    series collapses to the ingest date."""
    return RealEvidence(
        ticker=ticker,
        decision_date=decision_date,
        macro_state=_load_macro_state(conn, decision_date),
        price_history=_load_price_history(conn, ticker, decision_date, price_lookback_days),
        corporate_actions=_load_corporate_actions(
            conn, ticker, decision_date, corp_action_lookback_days
        ),
        ticker_meta=_load_ticker_meta(conn, ticker),
    )


def format_evidence_as_prose(evidence: RealEvidence, horizon_days: int) -> str:
    lines = [
        f"TARGET: {evidence.ticker}",
        f"DECISION DATE: {evidence.decision_date}",
        f"HORIZON: {horizon_days} days (forecast realized log return at this horizon)",
        "",
    ]

    meta = evidence.ticker_meta
    lines.append("TICKER METADATA:")
    lines.append(f"  Name: {meta.name or '(unknown)'}")
    lines.append(f"  Exchange: {meta.primary_exchange or '(unknown)'}")
    if meta.active:
        lines.append("  Status: active")
    else:
        delist = meta.delisted_utc.date() if meta.delisted_utc else "(unknown date)"
        lines.append(f"  Status: DELISTED on {delist}")
    lines.append("")

    lines.append("MACRO STATE (as of decision date):")
    if evidence.macro_state:
        for series_id in BASELINE_SERIES:
            val = evidence.macro_state.get(series_id)
            label = _SERIES_LABELS.get(series_id, series_id)
            if val is not None:
                lines.append(f"  {label}: {val}")
    else:
        lines.append("  (no macro data available)")
    lines.append("")

    lines.append(
        f"RECENT PRICE HISTORY (last {len(evidence.price_history)} trading days, "
        "most recent first):"
    )
    if evidence.price_history:
        lines.append(
            f"  {'date':<12} {'open':>10} {'high':>10} {'low':>10} {'close':>10} {'volume':>14}"
        )
        for bar in evidence.price_history[:60]:
            lines.append(
                f"  {bar.date!s:<12} "
                f"{float(bar.open_):>10.2f} {float(bar.high):>10.2f} "
                f"{float(bar.low):>10.2f} {float(bar.close):>10.2f} "
                f"{bar.volume:>14,}"
            )
    else:
        lines.append("  (no price history available)")
    lines.append("")

    lines.append("CORPORATE ACTIONS in lookback window:")
    if evidence.corporate_actions:
        for action in evidence.corporate_actions:
            lines.append(f"  {action.date}  {action.kind.upper():<8}  {action.detail}")
    else:
        lines.append("  (none)")

    return "\n".join(lines)


def _build_contract(
    evidence: RealEvidence,
    horizon_days: int,
    response: ForecastResponse,
) -> Contract:
    decision_ts = datetime(
        evidence.decision_date.year,
        evidence.decision_date.month,
        evidence.decision_date.day,
        21,
        0,
        0,
        tzinfo=UTC,
    )

    # Build evidence_ids — one synthetic ref per evidence row we showed the model.
    # Phase 0/early-Phase-2: row_ids are synthetic strings; the L0 trajectory store
    # comes in Step 3 and the refs will become real UUIDs pointing at rows.
    evidence_refs: list[EvidenceRef] = []
    for series_id in evidence.macro_state.keys():
        evidence_refs.append(
            EvidenceRef(
                row_id=f"macro:{series_id}:{evidence.decision_date}",
                as_known=decision_ts,
                source="FRED",
            )
        )
    for bar in evidence.price_history:
        evidence_refs.append(
            EvidenceRef(
                row_id=f"price:{evidence.ticker}:{bar.date}",
                as_known=decision_ts,
                source="massive",
            )
        )

    forecast_dist = ForecastDistribution(probabilities=dict(response.distribution))

    cognitive_step = CognitiveStep(
        step_index=0,
        initial_forecast=forecast_dist,
        additional_reasoning="",
        updated_forecast=forecast_dist,
        action_changed=False,
    )

    # Pick recommended action: long-equity if expected return > 0 under the
    # forecast; NoAction otherwise. The Action Engine downstream will gate
    # this against margin-of-safety.
    bucket_midpoints: dict[str, float] = {
        "below_minus_5": -0.08,
        "minus_5_to_0": -0.025,
        "zero_to_plus_5": 0.025,
        "plus_5_to_plus_10": 0.075,
        "above_plus_10": 0.12,
    }
    expected_log_return = sum(
        response.distribution.get(b, 0.0) * bucket_midpoints[b] for b in RETURN_BUCKETS
    )

    recommended_action: TradeAction | NoAction
    recommended_size = 0.0
    if expected_log_return > 0.0:
        recommended_action = TradeAction(
            expression_type="equity-long",
            underlying=evidence.ticker,
            direction="long",
            size=1,
            notional=1000.0,  # placeholder; Action Engine sizes by Kelly
        )
        recommended_size = 0.05  # placeholder fractional Kelly
    elif expected_log_return < 0.0 and evidence.ticker_meta.active:
        recommended_action = TradeAction(
            expression_type="equity-short",
            underlying=evidence.ticker,
            direction="short",
            size=1,
            notional=1000.0,
        )
        recommended_size = 0.05
    else:
        recommended_action = NoAction(reason="expected_return_near_zero")

    return Contract(
        contract_id=str(uuid.uuid4()),
        decision_time=decision_ts,
        agent_id=REAL_AGENT_ID,
        model_id="claude-haiku-4-5-20251001",  # AnthropicClient default; could be parameterized
        prompt_version="real_v1_deterministic_evidence",
        evidence_ids=evidence_refs,
        data_sources_used=["headline_observables", "equity_prices", "corporate_actions", "tickers"],
        forecast_distribution=forecast_dist,
        signal_class_id=response.signal_class_id,
        thesis_category=response.thesis_category,
        horizon=f"{horizon_days}d",
        recommended_action=recommended_action,
        recommended_size=recommended_size,
        falsifiers=[
            Falsifier(
                description=(
                    f"Realized log return of {evidence.ticker} at {horizon_days}d "
                    "falls in a bucket the forecast assigned <5% probability"
                ),
            )
        ],
        realized_return_plan=RealizedReturnPlan(
            horizon=f"{horizon_days}d",
            labelling_function="adjusted_close_log_return",
            return_type="log",
            point_in_time_anchor=decision_ts,
        ),
        cognitive_audit_trail=[cognitive_step],
        memory_update_proposal=None,
    )


class RealLlmAgent:
    """Real AI Core. Reads real evidence at decision time, emits a v5 Contract.

    Stateless across calls (each forecast loads its own evidence). Uses
    `AnthropicClient.request_forecast_from_text` so the system prompt and
    user message are tailored to real data rather than the toy emission stream.
    """

    def __init__(
        self,
        client: AnthropicClient,
        horizon_days: int = DEFAULT_HORIZON_DAYS,
        price_lookback_days: int = DEFAULT_PRICE_LOOKBACK_DAYS,
        corp_action_lookback_days: int = DEFAULT_CORP_ACTION_LOOKBACK_DAYS,
    ) -> None:
        self.client = client
        self.horizon_days = horizon_days
        self.price_lookback_days = price_lookback_days
        self.corp_action_lookback_days = corp_action_lookback_days

    def forecast_for(
        self,
        conn: psycopg.Connection[Any],
        ticker: str,
        decision_date: date,
    ) -> Contract:
        evidence = load_evidence(
            conn,
            ticker,
            decision_date,
            self.price_lookback_days,
            self.corp_action_lookback_days,
        )
        user_message = format_evidence_as_prose(evidence, self.horizon_days)
        response = self.client.request_forecast_from_text(
            user_message=user_message,
            system_prompt=_REAL_SYSTEM_PROMPT,
        )
        return _build_contract(evidence, self.horizon_days, response)


__all__ = [
    "DEFAULT_CORP_ACTION_LOOKBACK_DAYS",
    "DEFAULT_HORIZON_DAYS",
    "DEFAULT_PRICE_LOOKBACK_DAYS",
    "REAL_AGENT_ID",
    "CorporateAction",
    "PriceBar",
    "RealEvidence",
    "RealLlmAgent",
    "TickerMeta",
    "format_evidence_as_prose",
    "load_evidence",
]
