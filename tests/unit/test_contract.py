"""Unit tests for the Contract pydantic model.

Stone 19 / CONTRACT.md. Covers constructing valid Contracts of various
shapes and confirming that pydantic enforces basic structural constraints
(required fields, type bounds, the TradeAction/NoAction discriminated union).

Semantic validation (belief sums to 1, falsifiers non-empty, etc.) is
tested separately in test_contract_validator.py — that's a different layer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from fingym.agents.contract import (
    BeliefDelta,
    BeliefDistribution,
    CognitiveStep,
    Contract,
    Falsifier,
    HiddenStateHypothesis,
    LabelPlan,
    MarketBeliefEstimate,
    NoAction,
    TradeAction,
)


def _valid_kwargs(**overrides: Any) -> dict[str, Any]:
    """Helper: a dict of valid Contract kwargs that tests can override."""
    base: dict[str, Any] = {
        "contract_id": str(uuid4()),
        "decision_time": datetime.now(UTC),
        "agent_id": "test_agent",
        "model_id": "test_model_v1",
        "prompt_version": "v1",
        "evidence_ids": [],
        "hidden_state_hypotheses": [
            HiddenStateHypothesis(label="strg"),
            HiddenStateHypothesis(label="stbl"),
            HiddenStateHypothesis(label="dec"),
        ],
        "ai_belief": BeliefDistribution(probabilities={"strg": 0.5, "stbl": 0.3, "dec": 0.2}),
        "market_implied_belief": None,
        "belief_delta": None,
        "horizon": "12_ticks",
        "action_or_no_action": NoAction(reason="test no action"),
        "recommended_size": 0.0,
        "falsifiers": [Falsifier(description="test falsifier")],
        "label_plan": LabelPlan(
            horizon="12_ticks",
            label_source="toy_ground_truth",
            labelling_function="identity",
        ),
        "cognitive_audit_trail": [
            CognitiveStep(
                step_index=0,
                initial_belief=BeliefDistribution(
                    probabilities={"strg": 0.33, "stbl": 0.33, "dec": 0.34}
                ),
                additional_reasoning="initial",
                updated_belief=BeliefDistribution(
                    probabilities={"strg": 0.5, "stbl": 0.3, "dec": 0.2}
                ),
                action_changed=False,
            )
        ],
        "memory_update_proposal": None,
    }
    base.update(overrides)
    return base


def test_contract_constructs_with_no_action() -> None:
    """A Contract with NoAction constructs cleanly."""
    contract = Contract(**_valid_kwargs())
    assert isinstance(contract.action_or_no_action, NoAction)
    assert contract.recommended_size == 0.0


def test_contract_constructs_with_trade_action() -> None:
    """A Contract with a TradeAction constructs cleanly."""
    contract = Contract(
        **_valid_kwargs(
            action_or_no_action=TradeAction(
                expression_type="equity-long",
                underlying="AAPL",
                direction="long",
                size=100,
                notional=15000.0,
            ),
            recommended_size=0.05,
        )
    )
    assert isinstance(contract.action_or_no_action, TradeAction)
    assert contract.action_or_no_action.underlying == "AAPL"
    assert contract.action_or_no_action.expression_type == "equity-long"


def test_contract_with_market_belief_and_delta() -> None:
    """A Contract with market_implied_belief and belief_delta populated."""
    contract = Contract(
        **_valid_kwargs(
            market_implied_belief=MarketBeliefEstimate(
                probabilities={"strg": 0.3, "stbl": 0.3, "dec": 0.4}
            ),
            belief_delta=BeliefDelta(gaps={"strg": 0.2, "stbl": 0.0, "dec": -0.2}),
        )
    )
    assert contract.market_implied_belief is not None
    assert contract.belief_delta is not None


def test_negative_recommended_size_rejected() -> None:
    """Pydantic rejects negative recommended_size (Field ge=0.0)."""
    with pytest.raises(ValidationError):
        Contract(**_valid_kwargs(recommended_size=-1.0))


def test_trade_action_zero_size_rejected_by_pydantic() -> None:
    """Pydantic rejects TradeAction with size <= 0 (Field gt=0)."""
    with pytest.raises(ValidationError):
        TradeAction(
            expression_type="equity-long",
            underlying="AAPL",
            direction="long",
            size=0,
            notional=15000.0,
        )


def test_trade_action_zero_notional_rejected_by_pydantic() -> None:
    """Pydantic rejects TradeAction with notional <= 0 (Field gt=0.0)."""
    with pytest.raises(ValidationError):
        TradeAction(
            expression_type="equity-long",
            underlying="AAPL",
            direction="long",
            size=100,
            notional=0.0,
        )


def test_contract_is_frozen() -> None:
    """Contract is immutable; reassigning a field raises ValidationError."""
    contract = Contract(**_valid_kwargs())
    # The pydantic mypy plugin correctly marks frozen-model fields as
    # read-only Properties at the static level. The type-ignore opts out
    # of that static check so we can verify the runtime raises.
    with pytest.raises(ValidationError):
        contract.agent_id = "different"  # type: ignore[misc]


def test_discriminated_union_serializes_round_trip() -> None:
    """A TradeAction Contract round-trips through JSON correctly.

    The action_type literal discriminates TradeAction vs NoAction so
    deserialization recovers the right concrete type.
    """
    contract = Contract(
        **_valid_kwargs(
            action_or_no_action=TradeAction(
                expression_type="option-call",
                underlying="MSFT",
                direction="long",
                size=10,
                notional=2000.0,
                strike=420.0,
            ),
            recommended_size=0.02,
        )
    )
    as_json = contract.model_dump_json()
    rehydrated = Contract.model_validate_json(as_json)
    assert isinstance(rehydrated.action_or_no_action, TradeAction)
    assert rehydrated.action_or_no_action.expression_type == "option-call"
    assert rehydrated.action_or_no_action.strike == 420.0
