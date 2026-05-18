"""contract_emitter.py — Stone 19 demo: BayesianAgent wrapped to emit Contracts.

Proves the Agent Protocol (src/fingym/agents/interface.py) compiles against a
concrete v5 implementation. The BayesianAgent from adversarial_agents produces
a forecast distribution over realized-return BUCKETS; this adapter wraps it
to emit a valid pydantic Contract per CONTRACT.md (v5).

This is the test fixture for Phase 0 substep 6's exit criterion: "Model
interface contract is documented; a stub agent compiles against it." Under
Phase 1 NEW Cluster A, the stub now uses the actual v5 cognition path —
forecast over realized-return buckets, no state-cognition by the agent.

Run: `uv run python -m fingym.toys.contract_emitter`
"""

from datetime import UTC, datetime
from uuid import uuid4

from fingym.agents.contract import (
    CognitiveStep,
    Contract,
    Falsifier,
    ForecastDistribution,
    NoAction,
    RealizedReturnPlan,
)
from fingym.agents.contract_validator import validate_contract
from fingym.toys.adversarial_agents import BayesianAgent
from fingym.toys.synthetic_market import Emission, uniform_forecast_over_buckets


class BayesianContractEmitter:
    """Wraps a BayesianAgent to emit valid v5 Contracts.

    Satisfies the Agent[list[Emission]] Protocol structurally: has an
    `agent_id` attribute and an `emit_contract(raw_evidence)` method
    returning a Contract. mypy verifies structural conformance.
    """

    def __init__(self) -> None:
        self.agent_id = "BayesianContractEmitter@stone19"
        self.model_id = "fingym.bayesian.v1"
        self.prompt_version = "stone19_demo"
        # The BayesianAgent's hypothesis space is realized-return buckets.
        # Uniform prior — the agent has no prior information about the company.
        self._bayesian = BayesianAgent(uniform_forecast_over_buckets(), name="BayesianAgent")

    def emit_contract(self, raw_evidence: list[Emission]) -> Contract:
        """Form a forecast from the emission stream and emit a v5 Contract.

        The wrapped BayesianAgent observes each emission and updates its forecast
        over realized-return buckets via Bayes on the bucket-conditional emission
        likelihoods. After all emissions are processed, the agent's final
        forecast is packaged into a ForecastDistribution along with a
        signal_class_id tag, falsifier, realized return plan, and a single-step
        cognitive audit trail (Phase 0 — no iteration yet).
        """
        initial_probabilities = {b: p for b, p in uniform_forecast_over_buckets().items()}
        initial_forecast = ForecastDistribution(probabilities=initial_probabilities)
        for emission in raw_evidence:
            self._bayesian.observe(emission)
        final_forecast = ForecastDistribution(
            probabilities={b: p for b, p in self._bayesian.forecast.items()}
        )
        decision_time = datetime.now(UTC)

        return Contract(
            contract_id=str(uuid4()),
            decision_time=decision_time,
            agent_id=self.agent_id,
            model_id=self.model_id,
            prompt_version=self.prompt_version,
            evidence_ids=[],  # toy world; no L0 emissions table at Phase 0
            data_sources_used=["toy_synthetic_market"],
            forecast_distribution=final_forecast,
            signal_class_id=self._bayesian.signal_class_id,
            thesis_category="toy_phase_1_new_cluster_a",
            horizon="12_ticks",
            recommended_action=NoAction(
                reason=(
                    "Stone 19 demo emits NoAction; the stub doesn't yet decide"
                    " trades. The Tradable-Edge Action Engine (Phase 1 NEW"
                    " Cluster B) will populate final_action via calibrated"
                    " expected utility."
                )
            ),
            recommended_size=0.0,
            falsifiers=[
                Falsifier(
                    description=(
                        "If the realized log return at horizon falls in a bucket"
                        " other than the modal bucket of forecast_distribution,"
                        " the forecast's mode was wrong."
                    )
                )
            ],
            realized_return_plan=RealizedReturnPlan(
                horizon="12_ticks",
                labelling_function="toy_realized_return_at_horizon",
            ),
            cognitive_audit_trail=[
                CognitiveStep(
                    step_index=0,
                    initial_forecast=initial_forecast,
                    additional_reasoning=(
                        f"Observed {len(raw_evidence)} emissions from the toy"
                        f" world; updated forecast via Bayes on each, using the"
                        f" pre-computed bucket-conditional emission likelihoods."
                    ),
                    updated_forecast=final_forecast,
                    action_changed=False,
                )
            ],
            memory_update_proposal=None,
        )


def demo_emit_and_validate() -> None:
    """Build the emitter, feed a fixed emission stream, emit + validate."""
    emitter = BayesianContractEmitter()
    evidence: list[Emission] = [
        "strong",
        "strong",
        "strong",
        "mixed",
        "strong",
        "strong",
        "weak",
        "strong",
        "strong",
        "strong",
        "strong",
        "strong",
    ]
    contract = emitter.emit_contract(evidence)
    result = validate_contract(contract)

    print("\nStone 19 demo — BayesianContractEmitter emits a v5 Contract")
    print(f"  agent_id              = {contract.agent_id}")
    print(f"  decision_time         = {contract.decision_time.isoformat()}")
    print(f"  forecast_distribution = {contract.forecast_distribution.probabilities}")
    print(f"  signal_class_id       = {contract.signal_class_id}")
    print(f"  recommended_action    = {contract.recommended_action.action_type}")
    print(f"  horizon               = {contract.horizon}")
    print(f"  falsifiers count      = {len(contract.falsifiers)}")
    print(f"  cognitive_steps       = {len(contract.cognitive_audit_trail)}")
    print(f"  validator             = {'ACCEPTED' if result.accepted else 'REJECTED'}")
    if not result.accepted:
        for reason in result.rejection_reasons:
            print(f"    - {reason}")


if __name__ == "__main__":
    demo_emit_and_validate()
