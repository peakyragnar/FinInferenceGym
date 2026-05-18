"""contract_validator.py — gates Contracts at the cognition/verification boundary.

The validator runs the applicable cognition-side checks from CONTRACT.md
"Validation" (v5). A Contract that fails any check is rejected — recorded
as a verifier-rejection in the operational log, not scored, not persisted
to the trajectory store. This is DESIGN.md #5 in code: the agent can
propose any cognition output, but only valid Contracts enter the system.

Verification-side checks (Phase 1 NEW Cluster B onward) — coherence
between `final_action`, `tradable_edge_score`, `kelly_fraction_applied`,
and the engine's `calibrated_forecast` — live in `src/fingym/action/`
once the Tradable-Edge Action Engine ships. This file enforces only the
cognition-side checks.

The validator is intentionally separate from the pydantic types in
contract.py. The types enforce SHAPE (presence of required fields, basic
type constraints); the validator enforces SEMANTIC INVARIANTS (forecast
sums to 1, falsifiers non-empty, NoAction iff size == 0, etc.).

Phase 0 + Phase 1 NEW cognition-side checks (this file):
  1. forecast_distribution is a valid probability distribution (sums to ~1,
     no negative values, no zero values on the declared support).
  2. signal_class_id is non-empty.
  3. falsifiers is non-empty.
  4. realized_return_plan declares a horizon.
  5. recommended_size == 0.0 iff recommended_action is NoAction.
  6. cognitive_audit_trail has at least one entry.

Phase 1+ adds (deferred — emission table doesn't exist yet at Phase 0):
  - Every evidence_id resolves to an L0 row.
  - Every evidence_id's as_known <= decision_time (time-leak guard).
"""

from dataclasses import dataclass

from fingym.agents.contract import Contract, NoAction, TradeAction

# Tolerance on forecast-distribution sum. Pydantic accepts any dict of floats;
# the validator allows tiny numerical noise around exactly 1.0.
_FORECAST_SUM_TOLERANCE = 1e-3


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
    """Run the applicable cognition-side validation checks on a Contract.

    Returns ValidationResult.accepted = True if all checks pass. Otherwise
    returns accepted = False with a list of rejection_reasons. Each reason
    is a short human-readable string suitable for logging.

    The validator is deterministic and pure — same Contract in, same result
    out. No side effects. No model calls. No I/O.
    """
    reasons: list[str] = []

    _check_forecast_distribution(contract, reasons)
    _check_signal_class_id(contract, reasons)
    _check_falsifiers_non_empty(contract, reasons)
    _check_realized_return_plan(contract, reasons)
    _check_action_size_coherence(contract, reasons)
    _check_cognitive_audit_trail(contract, reasons)

    return ValidationResult(accepted=not reasons, rejection_reasons=reasons)


def _check_forecast_distribution(contract: Contract, reasons: list[str]) -> None:
    probs = contract.forecast_distribution.probabilities
    if not probs:
        reasons.append("forecast_distribution.probabilities is empty")
        return

    total = sum(probs.values())
    if abs(total - 1.0) > _FORECAST_SUM_TOLERANCE:
        reasons.append(
            f"forecast_distribution.probabilities sums to {total:.6f}, not 1.0 "
            f"(tolerance {_FORECAST_SUM_TOLERANCE})"
        )

    negatives = [label for label, p in probs.items() if p < 0.0]
    if negatives:
        reasons.append(f"forecast_distribution.probabilities has negative values for: {negatives}")

    # Cromwell: values declared in the support must have strictly positive
    # probability. The agent may freely place 0 on values it considers
    # structurally absent (i.e., outside its declared support, by omission).
    cromwell_violations = [label for label, p in probs.items() if p == 0.0]
    if cromwell_violations:
        reasons.append(
            f"forecast_distribution assigns 0 to values in the declared support "
            f"(Cromwell violation): {cromwell_violations}"
        )


def _check_signal_class_id(contract: Contract, reasons: list[str]) -> None:
    if not contract.signal_class_id:
        reasons.append("signal_class_id is empty (required for Forecast Ledger reliability lookup)")


def _check_falsifiers_non_empty(contract: Contract, reasons: list[str]) -> None:
    if not contract.falsifiers:
        reasons.append(
            "falsifiers is empty (Contract must be falsifiable; see BIAS_PATTERNS.md #11)"
        )


def _check_realized_return_plan(contract: Contract, reasons: list[str]) -> None:
    if not contract.realized_return_plan.horizon:
        reasons.append("realized_return_plan.horizon is empty")
    if not contract.realized_return_plan.labelling_function:
        reasons.append("realized_return_plan.labelling_function is empty")


def _check_action_size_coherence(contract: Contract, reasons: list[str]) -> None:
    action = contract.recommended_action
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
