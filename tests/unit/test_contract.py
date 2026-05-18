"""Unit tests for the Contract pydantic model.

Stone 19 / CONTRACT.md (v5). Covers constructing valid Contracts of various
shapes and confirming that pydantic enforces basic structural constraints
(required fields, type bounds, the TradeAction/NoAction discriminated union).

Semantic validation (forecast sums to 1, falsifiers non-empty, etc.) is
tested separately in test_contract_validator.py — that's a different layer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from fingym.agents.contract import (
    CognitiveStep,
    Contract,
    Falsifier,
    ForecastDistribution,
    NoAction,
    RealizedReturnPlan,
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
        "data_sources_used": ["toy"],
        "forecast_distribution": ForecastDistribution(
            probabilities={"up": 0.5, "flat": 0.3, "down": 0.2}
        ),
        "signal_class_id": "toy_3bucket",
        "thesis_category": "test",
        "horizon": "12_ticks",
        "recommended_action": NoAction(reason="test no action"),
        "recommended_size": 0.0,
        "falsifiers": [Falsifier(description="test falsifier")],
        "realized_return_plan": RealizedReturnPlan(
            horizon="12_ticks",
            labelling_function="toy_realized_state_at_horizon",
        ),
        "cognitive_audit_trail": [
            CognitiveStep(
                step_index=0,
                initial_forecast=ForecastDistribution(
                    probabilities={"up": 0.33, "flat": 0.33, "down": 0.34}
                ),
                additional_reasoning="initial",
                updated_forecast=ForecastDistribution(
                    probabilities={"up": 0.5, "flat": 0.3, "down": 0.2}
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
    assert isinstance(contract.recommended_action, NoAction)
    assert contract.recommended_size == 0.0


def test_contract_constructs_with_trade_action() -> None:
    """A Contract with a TradeAction constructs cleanly."""
    contract = Contract(
        **_valid_kwargs(
            recommended_action=TradeAction(
                expression_type="equity-long",
                underlying="AAPL",
                direction="long",
                size=100,
                notional=15000.0,
            ),
            recommended_size=0.05,
        )
    )
    assert isinstance(contract.recommended_action, TradeAction)
    assert contract.recommended_action.underlying == "AAPL"
    assert contract.recommended_action.expression_type == "equity-long"


def test_contract_verification_fields_default_to_none() -> None:
    """v5 verification fields are None at Phase 0 (engine not yet built)."""
    contract = Contract(**_valid_kwargs())
    assert contract.calibrated_forecast is None
    assert contract.tradable_edge_score is None
    assert contract.final_action is None


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
            recommended_action=TradeAction(
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
    assert isinstance(rehydrated.recommended_action, TradeAction)
    assert rehydrated.recommended_action.expression_type == "option-call"
    assert rehydrated.recommended_action.strike == 420.0
