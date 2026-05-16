"""contract_validator.py — gates Contracts at the cognition/verification boundary.

The validator runs the Phase 0 applicable checks from CONTRACT.md
"Validation". A Contract that fails any check is rejected — recorded as a
verifier-rejection in the operational log, not scored, not persisted to the
trajectory store. This is DESIGN.md #5 in code: the agent can propose any
output, but only valid Contracts enter the system.

The validator is intentionally separate from the pydantic types in
contract.py. The types enforce SHAPE (presence of required fields, basic
type constraints); the validator enforces SEMANTIC INVARIANTS (belief sums
to 1, falsifiers non-empty, NoAction iff size == 0, etc.).

Phase 0 applicable checks (this file):
  1. ai_belief is a valid probability distribution (sums to ~1, no negative
     values, no zero values on hypotheses in the declared support).
  2. If market_implied_belief is set, belief_delta must also be set.
  3. falsifiers is non-empty.
  4. label_plan declares at least one horizon.
  5. recommended_size == 0.0 iff action_or_no_action is NoAction.
  6. cognitive_audit_trail has at least one entry.

Phase 1+ adds (deferred — emission table doesn't exist yet at Phase 0):
  - Every evidence_id resolves to an L0 row.
  - Every evidence_id's as_known <= decision_time (time-leak guard).
"""

from dataclasses import dataclass

from fingym.agents.contract import Contract, NoAction, TradeAction

# Tolerance on belief-distribution sum. Pydantic accepts any list of floats;
# the validator allows tiny numerical noise around exactly 1.0.
_BELIEF_SUM_TOLERANCE = 1e-3


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of running the validator on a Contract.

    `accepted` is True iff all applicable checks passed. `rejection_reasons`
    enumerates each failure encountered (the validator collects all failures
    rather than short-circuiting on the first, so operators see the full
    picture in the verifier-rejection log entry).
    """

    accepted: bool
    rejection_reasons: list[str]


def validate_contract(contract: Contract) -> ValidationResult:
    """Run the Phase 0 applicable validation checks on a Contract.

    Returns ValidationResult.accepted = True if all checks pass. Otherwise
    returns accepted = False with a list of rejection_reasons. Each reason
    is a short human-readable string suitable for logging.

    The validator is deterministic and pure — same Contract in, same result
    out. No side effects. No model calls. No I/O.
    """
    reasons: list[str] = []

    _check_ai_belief_distribution(contract, reasons)
    _check_market_and_delta_coherence(contract, reasons)
    _check_falsifiers_non_empty(contract, reasons)
    _check_label_plan_horizon(contract, reasons)
    _check_action_size_coherence(contract, reasons)
    _check_cognitive_audit_trail(contract, reasons)

    return ValidationResult(accepted=not reasons, rejection_reasons=reasons)


def _check_ai_belief_distribution(contract: Contract, reasons: list[str]) -> None:
    probs = contract.ai_belief.probabilities
    if not probs:
        reasons.append("ai_belief.probabilities is empty")
        return

    total = sum(probs.values())
    if abs(total - 1.0) > _BELIEF_SUM_TOLERANCE:
        reasons.append(
            f"ai_belief.probabilities sums to {total:.6f}, not 1.0 "
            f"(tolerance {_BELIEF_SUM_TOLERANCE})"
        )

    negatives = [label for label, p in probs.items() if p < 0.0]
    if negatives:
        reasons.append(f"ai_belief.probabilities has negative values for: {negatives}")

    # Cromwell: hypotheses declared in the support must have strictly
    # positive probability. (Probabilities outside the declared support
    # are not penalised here; the agent may freely place 0 on hypotheses
    # it considers structurally absent.)
    declared_labels = {h.label for h in contract.hidden_state_hypotheses}
    cromwell_violations = [label for label in declared_labels if probs.get(label, 0.0) == 0.0]
    if cromwell_violations:
        reasons.append(
            f"ai_belief assigns 0 to hypotheses in the declared support "
            f"(Cromwell violation): {cromwell_violations}"
        )


def _check_market_and_delta_coherence(contract: Contract, reasons: list[str]) -> None:
    market_set = contract.market_implied_belief is not None
    delta_set = contract.belief_delta is not None
    if market_set and not delta_set:
        reasons.append(
            "market_implied_belief is set but belief_delta is None "
            "(when market is present, the gap must be computed)"
        )


def _check_falsifiers_non_empty(contract: Contract, reasons: list[str]) -> None:
    if not contract.falsifiers:
        reasons.append(
            "falsifiers is empty (Contract must be falsifiable; see BIAS_PATTERNS.md #11)"
        )


def _check_label_plan_horizon(contract: Contract, reasons: list[str]) -> None:
    if not contract.label_plan.horizon:
        reasons.append("label_plan.horizon is empty")


def _check_action_size_coherence(contract: Contract, reasons: list[str]) -> None:
    action = contract.action_or_no_action
    size = contract.recommended_size
    if isinstance(action, NoAction):
        if size != 0.0:
            reasons.append(f"NoAction must have recommended_size == 0.0; got {size}")
    elif isinstance(action, TradeAction):
        if size <= 0.0:
            reasons.append(f"TradeAction must have recommended_size > 0.0; got {size}")


def _check_cognitive_audit_trail(contract: Contract, reasons: list[str]) -> None:
    if not contract.cognitive_audit_trail:
        reasons.append(
            "cognitive_audit_trail is empty (must contain >=1 entry; "
            "Phase 0 entries are single-step)"
        )
