"""contract.py — the typed terminal output every agent emits.

The Contract is the cognition/verification boundary in code (DESIGN.md #5).
From CONTRACT.md: every cognitive output the system takes seriously must
take this shape. A model output that does not land in a valid Contract is
rejected at the verifier gate (contract_validator.py), not scored, and
recorded as a verifier-rejection in the operational log.

This file defines the pydantic model for the Contract and all nested types
required at Phase 0 + Phase 1 NEW under Constitution v5. Cognition fields
are populated by the agent (AI Core); verification fields are populated by
the Tradable-Edge Action Engine (Phase 1 NEW Cluster B). Deferred fields
(payoff_distribution, cost_estimate, capacity_estimate, etc.) are NOT yet
present; they will be added as Optional fields when their consuming
machinery ships. See CONTRACT.md "Deferred fields" for the full triggers
table.

Validation rules live in contract_validator.py, not on the pydantic types.
The types enforce shape (types, required-ness); the validator enforces
semantic invariants (forecast sums to 1, falsifiers non-empty, NoAction iff
size == 0, tradable_edge_score consistent with final_action, etc.).
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Leaf types — defined first so Contract can compose them without forward refs.
# ---------------------------------------------------------------------------


class EvidenceRef(BaseModel):
    """Pointer to a row in the L0 trajectory / emissions store.

    At Phase 0 (toys), `row_id` is any string the toy uses to track evidence
    in-memory. At Phase 1+, `row_id` becomes a UUID pointing to a real row
    in the emissions table, and the time-leak guard (Phase 1+) enforces
    `as_known <= decision_time` on the parent Contract.
    """

    model_config = ConfigDict(frozen=True)

    row_id: str
    as_known: datetime
    source: str


class ForecastDistribution(BaseModel):
    """Probability distribution over realized returns (Constitution v5).

    `probabilities` maps each bucket label (or parametric-shape parameter name)
    to its probability. Pydantic enforces shape (dict of str -> float);
    validation that the distribution is well-formed (sums to 1, no negative
    values, Cromwell) lives in contract_validator.py.

    Replaces the pre-v5 `BeliefDistribution` (which was over a hypothesis
    space of states). Under v5 the support is over realized returns directly.
    """

    model_config = ConfigDict(frozen=True)

    probabilities: dict[str, float]


# Expression categories — Stone 11. Broad category only; trade specifics
# (strike, expiration, premium, etc.) live inside TradeAction.
ExpressionType = Literal[
    "equity-long",
    "equity-short",
    "option-call",
    "option-put",
    "option-spread",
    "option-straddle",
    "option-strangle",
    "vol-long",
    "vol-short",
    "pair",
]


class TradeAction(BaseModel):
    """The agent decides to trade. One sub-type within action_or_no_action."""

    model_config = ConfigDict(frozen=True)

    action_type: Literal["trade"] = "trade"
    expression_type: ExpressionType
    underlying: str
    direction: Literal["long", "short"]
    size: int = Field(gt=0)
    notional: float = Field(gt=0.0)
    # Option-specific fields. Required iff expression_type is option-*.
    # Semantic enforcement lives in contract_validator.py.
    strike: float | None = None
    expiration: datetime | None = None
    premium_per_unit: float | None = None


class NoAction(BaseModel):
    """The agent declines to trade. Typed peer of TradeAction.

    NOT a degenerate TradeAction with size == 0. Carries its own scoring
    path (Stone 13). DESIGN.md Operational Constraints: NO-EDGE is a
    first-class output (BIAS_PATTERNS.md #12 — trade-for-trade's-sake).
    """

    model_config = ConfigDict(frozen=True)

    action_type: Literal["no_action"] = "no_action"
    reason: str


# Discriminated union over the action_type literal. Pydantic uses this to
# correctly deserialize JSON back into the right concrete type.
ActionOrNoAction = Annotated[TradeAction | NoAction, Field(discriminator="action_type")]


class Falsifier(BaseModel):
    """A future observation that would prove the forecast wrong.

    Required: at least one per Contract. A Contract with no falsifiers is
    unfalsifiable narrative, not a scoreable claim (BIAS_PATTERNS.md #11 —
    narrative as evidence).
    """

    model_config = ConfigDict(frozen=True)

    description: str
    pattern: str | None = None  # optional structured form for machine-check


class RealizedReturnPlan(BaseModel):
    """Which realized returns at which horizons will score this Contract.

    Constitution v5: replaces the pre-v5 `LabelPlan`. The labelling function
    is the rule that turns future price + corporate actions + payoff
    structure into the realized return at horizon. Phase 0 toy:
    `labelling_function = "toy_realized_return"`. Phase 2+: real labelling
    function over price / corporate-action / payoff-structure data.

    Choosing the labelling function is a load-bearing design choice —
    different functions produce different realized returns for the same
    future. PYRAMID Stone 2 (label, practically) discusses this.
    """

    model_config = ConfigDict(frozen=True)

    horizon: str
    labelling_function: str
    return_type: Literal["simple", "log", "expression-specific"] = "simple"
    point_in_time_anchor: datetime | None = None


class CognitiveStep(BaseModel):
    """One iteration of agent reasoning (Phase 4 VOI input).

    Phase 0 has one step per Contract (initial_forecast == updated_forecast,
    no iteration). Phase 4 reads this trail to compute "did more thinking
    change the action?"
    """

    model_config = ConfigDict(frozen=True)

    step_index: int = Field(ge=0)
    initial_forecast: ForecastDistribution
    additional_reasoning: str
    updated_forecast: ForecastDistribution
    action_changed: bool


class MemoryUpdateProposal(BaseModel):
    """L2 hypothesis proposal feeding the promotion gate (Phase 4).

    When an agent notices a pattern, it can propose a new memory artifact.
    The proposal is written as an L2 YAML to memory_registry/probationary/
    and tested by the promotion gate. Optional on every Contract — most
    Contracts don't propose memory.
    """

    model_config = ConfigDict(frozen=True)

    claim: str
    proposed_scope: dict[str, list[str]] = Field(default_factory=dict)
    derived_from: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# The Contract itself.
# ---------------------------------------------------------------------------


class Contract(BaseModel):
    """The structured terminal output every agent emits.

    The cognition/verification boundary in code under Constitution v5.
    Cognition fields are populated by the agent (AI Core); verification
    fields are populated by the Tradable-Edge Action Engine (Phase 1 NEW
    Cluster B). A model output that does not conform to this shape is
    rejected at the verifier gate (handled by contract_validator.py).

    Phase 0 required fields are populated by the agent. Phase 1 NEW Cluster
    B introduces the verification fields (calibrated_forecast, calibrated
    expected utility, tradable_edge_score, final_action, kelly_fraction,
    cost_estimate). Deferred fields (capacity_estimate, payoff_distribution,
    etc.) are NOT yet present; they will be added as Optional fields when
    their consuming machinery ships. CONTRACT.md "Deferred fields" lists
    the trigger phases.
    """

    model_config = ConfigDict(frozen=True)

    # Identity and timing
    contract_id: str
    decision_time: datetime
    agent_id: str
    model_id: str
    prompt_version: str

    # --- COGNITION FIELDS (agent-emitted) ---

    # What the agent looked at
    evidence_ids: list[EvidenceRef]
    data_sources_used: list[str] = Field(default_factory=list)

    # What the agent forecasts
    forecast_distribution: ForecastDistribution
    signal_class_id: str
    thesis_category: str = ""

    # What the agent recommends (raw; the engine may override final_action)
    horizon: str
    recommended_action: ActionOrNoAction
    recommended_size: float = Field(ge=0.0)

    # How the agent will be judged
    falsifiers: list[Falsifier]
    realized_return_plan: RealizedReturnPlan

    # How the agent thought
    cognitive_audit_trail: list[CognitiveStep]

    # Optional memory proposal
    memory_update_proposal: MemoryUpdateProposal | None = None

    # --- VERIFICATION FIELDS (Tradable-Edge Action Engine; Phase 1 NEW Cluster B+) ---
    # All optional at Phase 0; required from Phase 1 NEW Cluster B onward.

    calibrated_forecast: ForecastDistribution | None = None
    calibrated_expected_return: float | None = None
    calibrated_expected_utility: float | None = None
    tradable_edge_score: float | None = None
    kelly_fraction_applied: float | None = Field(default=None, ge=0.0)
    final_action: ActionOrNoAction | None = None
