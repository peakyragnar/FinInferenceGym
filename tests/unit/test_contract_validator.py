"""Unit tests for the contract_validator (Stone 19 / CONTRACT.md "Validation").

Tests the cognition-side validation checks under Constitution v5. Each
check has a passing case (validator accepts) and at least one failing
case (validator rejects with a specific reason).

The validator is deterministic, pure, no I/O — these tests run instantly.

Verification-side checks (tradable_edge_score consistency with final_action,
kelly_fraction coherence, cost_estimate presence for TradeAction) live in
the Tradable-Edge Action Engine's validator (Phase 1 NEW Cluster B) and are
tested there.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from fingym.agents.contract import (
    CognitiveStep,
    Contract,
    Falsifier,
    ForecastDistribution,
    NoAction,
    RealizedReturnPlan,
    TradeAction,
)
from fingym.agents.contract_validator import validate_contract


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
        "recommended_action": NoAction(reason="test"),
        "recommended_size": 0.0,
        "falsifiers": [Falsifier(description="test")],
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


def test_validator_accepts_well_formed_contract() -> None:
    """A well-formed Contract passes all cognition-side applicable checks."""
    result = validate_contract(Contract(**_valid_kwargs()))
    assert result.accepted, result.rejection_reasons
    assert result.rejection_reasons == []


def test_validator_rejects_forecast_not_summing_to_one() -> None:
    """forecast_distribution.probabilities that sum to != 1.0 is rejected."""
    contract = Contract(
        **_valid_kwargs(
            forecast_distribution=ForecastDistribution(
                probabilities={"up": 0.5, "flat": 0.3, "down": 0.5}  # sums to 1.3
            )
        )
    )
    result = validate_contract(contract)
    assert not result.accepted
    assert any("sums to" in r for r in result.rejection_reasons)


def test_validator_rejects_cromwell_violation() -> None:
    """forecast_distribution with 0.0 on a bucket in declared support is rejected."""
    contract = Contract(
        **_valid_kwargs(
            forecast_distribution=ForecastDistribution(
                probabilities={"up": 0.6, "flat": 0.4, "down": 0.0}
            )
        )
    )
    result = validate_contract(contract)
    assert not result.accepted
    assert any("Cromwell" in r for r in result.rejection_reasons)


def test_validator_rejects_empty_signal_class_id() -> None:
    """signal_class_id being empty is rejected (required for Forecast Ledger)."""
    contract = Contract(**_valid_kwargs(signal_class_id=""))
    result = validate_contract(contract)
    assert not result.accepted
    assert any("signal_class_id is empty" in r for r in result.rejection_reasons)


def test_validator_rejects_empty_falsifiers() -> None:
    """Empty falsifiers list is rejected (Contract must be falsifiable)."""
    contract = Contract(**_valid_kwargs(falsifiers=[]))
    result = validate_contract(contract)
    assert not result.accepted
    assert any("falsifiers is empty" in r for r in result.rejection_reasons)


def test_validator_rejects_empty_realized_return_plan_horizon() -> None:
    """realized_return_plan.horizon being empty string is rejected."""
    contract = Contract(
        **_valid_kwargs(
            realized_return_plan=RealizedReturnPlan(
                horizon="",
                labelling_function="toy_realized_state_at_horizon",
            )
        )
    )
    result = validate_contract(contract)
    assert not result.accepted
    assert any("realized_return_plan.horizon is empty" in r for r in result.rejection_reasons)


def test_validator_rejects_empty_labelling_function() -> None:
    """realized_return_plan.labelling_function being empty is rejected."""
    contract = Contract(
        **_valid_kwargs(
            realized_return_plan=RealizedReturnPlan(
                horizon="12_ticks",
                labelling_function="",
            )
        )
    )
    result = validate_contract(contract)
    assert not result.accepted
    assert any(
        "realized_return_plan.labelling_function is empty" in r for r in result.rejection_reasons
    )


def test_validator_rejects_no_action_with_nonzero_size() -> None:
    """NoAction with recommended_size != 0.0 is rejected."""
    contract = Contract(
        **_valid_kwargs(
            recommended_action=NoAction(reason="x"),
            recommended_size=0.5,
        )
    )
    result = validate_contract(contract)
    assert not result.accepted
    assert any("NoAction must have recommended_size == 0.0" in r for r in result.rejection_reasons)


def test_validator_rejects_trade_action_with_zero_size() -> None:
    """TradeAction with recommended_size == 0.0 is rejected."""
    contract = Contract(
        **_valid_kwargs(
            recommended_action=TradeAction(
                expression_type="equity-long",
                underlying="AAPL",
                direction="long",
                size=100,
                notional=15000.0,
            ),
            recommended_size=0.0,
        )
    )
    result = validate_contract(contract)
    assert not result.accepted
    assert any(
        "TradeAction must have recommended_size > 0.0" in r for r in result.rejection_reasons
    )


def test_validator_rejects_empty_cognitive_audit_trail() -> None:
    """Empty cognitive_audit_trail is rejected."""
    contract = Contract(**_valid_kwargs(cognitive_audit_trail=[]))
    result = validate_contract(contract)
    assert not result.accepted
    assert any("cognitive_audit_trail is empty" in r for r in result.rejection_reasons)


def test_validator_collects_multiple_failures() -> None:
    """The validator collects all failures rather than short-circuiting."""
    contract = Contract(
        **_valid_kwargs(
            falsifiers=[],
            cognitive_audit_trail=[],
            recommended_size=0.5,  # paired with NoAction → coherence failure
        )
    )
    result = validate_contract(contract)
    assert not result.accepted
    # Should see at least: empty falsifiers, empty cognitive_audit_trail,
    # NoAction with non-zero size.
    assert len(result.rejection_reasons) >= 3


def test_validation_result_is_frozen() -> None:
    """ValidationResult is a frozen dataclass — accepted is read-only."""
    result = validate_contract(Contract(**_valid_kwargs()))
    with pytest.raises(FrozenInstanceError):
        result.accepted = False  # type: ignore[misc]
