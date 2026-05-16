"""Unit tests for the contract_validator (Stone 19 / CONTRACT.md "Validation").

Tests the six Phase 0 applicable validation checks. Each check has a
passing case (validator accepts) and at least one failing case (validator
rejects with a specific reason).

The validator is deterministic, pure, no I/O — these tests run instantly.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

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
        "hidden_state_hypotheses": [
            HiddenStateHypothesis(label="strg"),
            HiddenStateHypothesis(label="stbl"),
            HiddenStateHypothesis(label="dec"),
        ],
        "ai_belief": BeliefDistribution(probabilities={"strg": 0.5, "stbl": 0.3, "dec": 0.2}),
        "market_implied_belief": None,
        "belief_delta": None,
        "horizon": "12_ticks",
        "action_or_no_action": NoAction(reason="test"),
        "recommended_size": 0.0,
        "falsifiers": [Falsifier(description="test")],
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


def test_validator_accepts_well_formed_contract() -> None:
    """A well-formed Contract passes all six Phase 0 applicable checks."""
    result = validate_contract(Contract(**_valid_kwargs()))
    assert result.accepted, result.rejection_reasons
    assert result.rejection_reasons == []


def test_validator_rejects_belief_not_summing_to_one() -> None:
    """ai_belief.probabilities that sum to != 1.0 is rejected."""
    contract = Contract(
        **_valid_kwargs(
            ai_belief=BeliefDistribution(
                probabilities={"strg": 0.5, "stbl": 0.3, "dec": 0.5}  # sums to 1.3
            )
        )
    )
    result = validate_contract(contract)
    assert not result.accepted
    assert any("sums to" in r for r in result.rejection_reasons)


def test_validator_rejects_cromwell_violation() -> None:
    """ai_belief with 0.0 on a hypothesis in declared support is rejected."""
    contract = Contract(
        **_valid_kwargs(
            ai_belief=BeliefDistribution(probabilities={"strg": 0.6, "stbl": 0.4, "dec": 0.0})
        )
    )
    result = validate_contract(contract)
    assert not result.accepted
    assert any("Cromwell" in r for r in result.rejection_reasons)


def test_validator_rejects_market_without_delta() -> None:
    """market_implied_belief set without belief_delta is rejected."""
    contract = Contract(
        **_valid_kwargs(
            market_implied_belief=MarketBeliefEstimate(
                probabilities={"strg": 0.3, "stbl": 0.3, "dec": 0.4}
            ),
            belief_delta=None,
        )
    )
    result = validate_contract(contract)
    assert not result.accepted
    assert any(
        "market_implied_belief is set but belief_delta is None" in r
        for r in result.rejection_reasons
    )


def test_validator_accepts_market_with_delta() -> None:
    """market_implied_belief AND belief_delta both set is accepted."""
    contract = Contract(
        **_valid_kwargs(
            market_implied_belief=MarketBeliefEstimate(
                probabilities={"strg": 0.3, "stbl": 0.3, "dec": 0.4}
            ),
            belief_delta=BeliefDelta(gaps={"strg": 0.2, "stbl": 0.0, "dec": -0.2}),
        )
    )
    result = validate_contract(contract)
    assert result.accepted, result.rejection_reasons


def test_validator_rejects_empty_falsifiers() -> None:
    """Empty falsifiers list is rejected (Contract must be falsifiable)."""
    contract = Contract(**_valid_kwargs(falsifiers=[]))
    result = validate_contract(contract)
    assert not result.accepted
    assert any("falsifiers is empty" in r for r in result.rejection_reasons)


def test_validator_rejects_empty_label_plan_horizon() -> None:
    """label_plan.horizon being empty string is rejected."""
    contract = Contract(
        **_valid_kwargs(
            label_plan=LabelPlan(
                horizon="",
                label_source="toy_ground_truth",
                labelling_function="identity",
            )
        )
    )
    result = validate_contract(contract)
    assert not result.accepted
    assert any("label_plan.horizon is empty" in r for r in result.rejection_reasons)


def test_validator_rejects_no_action_with_nonzero_size() -> None:
    """NoAction with recommended_size != 0.0 is rejected."""
    contract = Contract(
        **_valid_kwargs(
            action_or_no_action=NoAction(reason="x"),
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
            action_or_no_action=TradeAction(
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
