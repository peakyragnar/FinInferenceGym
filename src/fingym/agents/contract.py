"""contract.py — the typed terminal output every agent emits.

The Contract is the cognition/verification boundary in code (DESIGN.md #5).
From CONTRACT.md: every cognitive output the system takes seriously must
take this shape. A model output that does not land in a valid Contract is
rejected at the verifier gate (contract_validator.py), not scored, and
recorded as a verifier-rejection in the operational log.

This file defines the pydantic model for the Contract and all nested types
required at Phase 0. Deferred fields (cost_model, slippage_model, capacity,
payoff_distribution, etc.) are NOT yet present; they will be added as
Optional fields when their consuming machinery ships (Phase 2+). See
CONTRACT.md "Deferred fields" for the full triggers table.

Validation rules live in contract_validator.py, not on the pydantic types.
The types enforce shape (types, required-ness); the validator enforces
semantic invariants (belief sums to 1, falsifiers non-empty, NoAction iff
size == 0, etc.).
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


class HiddenStateHypothesis(BaseModel):
    """One element of the hypothesis space the agent reasons over.

    The model defines its own hypothesis space — no fixed ontology
    (DESIGN.md Layer 2). Coarse states (healthy / deteriorating / fraud)
    and fine-grained states are equally valid.
    """

    model_config = ConfigDict(frozen=True)

    label: str
    description: str = ""


class BeliefDistribution(BaseModel):
    """Probability distribution over the hypothesis space.

    `probabilities` maps each hypothesis label to its probability. Pydantic
    enforces shape (dict of str -> float); validation that the distribution
    is well-formed (sums to 1, no negative values, Cromwell) lives in
    contract_validator.py.
    """

    model_config = ConfigDict(frozen=True)

    probabilities: dict[str, float]


class MarketBeliefEstimate(BaseModel):
    """Estimate of the market's belief over the same hypothesis space.

    Recovered by inverting price / options / spreads (Stone 31, Phase 2+).
    None at Phase 0 toys without a market. Same shape as BeliefDistribution.
    """

    model_config = ConfigDict(frozen=True)

    probabilities: dict[str, float]


class BeliefDelta(BaseModel):
    """Signed gap P_AI(s) - P_market(s) per state (Stone 11a).

    Derived from ai_belief and market_implied_belief. The evaluator focuses
    on belief_delta[S_true] — the gap on the realized truth.
    """

    model_config = ConfigDict(frozen=True)

    gaps: dict[str, float]


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
    """A future observation that would prove the belief wrong.

    Required: at least one per Contract. A Contract with no falsifiers is
    unfalsifiable narrative, not a scoreable claim (BIAS_PATTERNS.md #11 —
    narrative as evidence).
    """

    model_config = ConfigDict(frozen=True)

    description: str
    pattern: str | None = None  # optional structured form for machine-check


class LabelPlan(BaseModel):
    """Which labels at which horizons will score this Contract.

    Phase 0 (toy): label_source = "toy_ground_truth", labelling_function =
    "identity", proxies = []. Phase 1+: real labelling function over proxy
    observations from the data spine.

    The labelling function is a HYPOTHESIS about how state translates to
    emissions (PYRAMID Stone 2). Choosing it is alpha-adjacent design;
    different functions produce different labels for the same future.
    """

    model_config = ConfigDict(frozen=True)

    horizon: str
    label_source: str
    labelling_function: str
    proxies: list[str] = Field(default_factory=list)
    thresholds: dict[str, float] = Field(default_factory=dict)
    point_in_time_anchor: datetime | None = None


class CognitiveStep(BaseModel):
    """One iteration of agent reasoning (Phase 4 VOI input).

    Phase 0 has one step per Contract (initial_belief == updated_belief,
    no iteration). Phase 4 reads this trail to compute "did more thinking
    change the action?"
    """

    model_config = ConfigDict(frozen=True)

    step_index: int = Field(ge=0)
    initial_belief: BeliefDistribution
    additional_reasoning: str
    updated_belief: BeliefDistribution
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

    The cognition/verification boundary in code. A model output that does
    not conform to this shape is rejected at the verifier gate (handled by
    contract_validator.py).

    Phase 0 required fields are populated. Deferred fields (cost_model,
    slippage_model, capacity_estimate, payoff_distribution, etc.) are NOT
    yet present; they will be added as Optional fields when their consuming
    machinery ships in Phase 2+. CONTRACT.md "Deferred fields" lists the
    trigger phases.
    """

    model_config = ConfigDict(frozen=True)

    # Identity and timing
    contract_id: str
    decision_time: datetime
    agent_id: str
    model_id: str
    prompt_version: str

    # What the agent looked at
    evidence_ids: list[EvidenceRef]

    # What the agent thinks the world is
    hidden_state_hypotheses: list[HiddenStateHypothesis]
    ai_belief: BeliefDistribution

    # What the agent thinks the market thinks (Phase 0: None allowed)
    market_implied_belief: MarketBeliefEstimate | None = None
    belief_delta: BeliefDelta | None = None

    # What the agent does
    horizon: str
    action_or_no_action: ActionOrNoAction
    recommended_size: float = Field(ge=0.0)

    # How the agent will be judged
    falsifiers: list[Falsifier]
    label_plan: LabelPlan

    # How the agent thought (for VOI — Phase 4)
    cognitive_audit_trail: list[CognitiveStep]

    # Optional memory proposal
    memory_update_proposal: MemoryUpdateProposal | None = None
