"""contract_emitter.py — Stone 19 demo: BayesianAgent wrapped to emit Contracts.

Proves the Agent Protocol (src/fingym/agents/interface.py) compiles against
a concrete implementation. The existing BayesianAgent from adversarial_agents
produces a 3-state distribution; this adapter wraps it to emit a valid
pydantic Contract per CONTRACT.md (v5).

This is the test fixture for Phase 0 substep 6's exit criterion: "Model
interface contract is documented; a stub agent compiles against it."

Under Constitution v5 (2026-05-18) the Contract's cognition fields hold a
forecast distribution over the toy's three states (treated as bucket labels
for the toy's realized-return analog). The full v5 single-believer-over-
realized-returns refactor lands in Phase 1 NEW Cluster A; this stub uses
the surviving Phase 0 toy world (three states {strengthening, stable,
decaying}) as the bucket alphabet for the forecast.

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
from fingym.toys.synthetic_market import Emission

# Phase 0 stub uses a uniform prior over the three toy states. Under v5, the
# pre-Phase-1-Cluster-A stub treats the toy state alphabet as the forecast
# bucket labels; Cluster A will refactor the toy to emit realized returns
# directly and forecast over them.
_STUB_FORECAST_PRIOR: dict[str, float] = {
    "strengthening": 1.0 / 3.0,
    "stable": 1.0 / 3.0,
    "decaying": 1.0 / 3.0,
}


class BayesianContractEmitter:
    """Wraps a BayesianAgent to emit valid Contracts per CONTRACT.md (v5).

    Satisfies the Agent[list[Emission]] Protocol structurally: has an
    `agent_id` attribute and an `emit_contract(raw_evidence)` method
    returning a Contract. mypy verifies structural conformance.
    """

    def __init__(self) -> None:
        self.agent_id = "BayesianContractEmitter@stone19"
        self.model_id = "fingym.bayesian.v1"
        self.prompt_version = "stone19_demo"
        # BayesianAgent uses the toy state alphabet as its prior keys.
        # The contract emitter treats those same keys as forecast bucket labels.
        self._bayesian = BayesianAgent(
            {"strengthening": 1.0 / 3.0, "stable": 1.0 / 3.0, "decaying": 1.0 / 3.0},
            name="BayesianAgent",
        )

    def emit_contract(self, raw_evidence: list[Emission]) -> Contract:
        """Form a forecast from the emission stream and emit a Contract.

        Each emission is observed via the wrapped BayesianAgent. After all
        emissions are processed, the agent's final belief over the toy state
        alphabet is packaged into a ForecastDistribution along with a
        signal_class_id tag, falsifier, realized return plan, and a single-
        step cognitive audit trail (Phase 0 — no iteration yet).
        """
        initial_forecast = ForecastDistribution(probabilities=dict(_STUB_FORECAST_PRIOR))
        for emission in raw_evidence:
            self._bayesian.observe(emission)
        final_forecast = ForecastDistribution(
            probabilities={str(s): p for s, p in self._bayesian.belief.items()}
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
            signal_class_id="toy_synthetic_market_3state",
            thesis_category="toy_phase_0_stub",
            horizon="12_ticks",
            recommended_action=NoAction(
                reason=(
                    "Stone 19 demo emits NoAction; the stub doesn't yet"
                    " decide trades. The Tradable-Edge Action Engine"
                    " (Phase 1 NEW Cluster B) will populate the engine's"
                    " final_action verdict from calibrated expected utility."
                )
            ),
            recommended_size=0.0,
            falsifiers=[
                Falsifier(
                    description=(
                        "If the realized state at the horizon is not the"
                        " highest-probability bucket in forecast_distribution,"
                        " the forecast's mode was wrong."
                    )
                )
            ],
            realized_return_plan=RealizedReturnPlan(
                horizon="12_ticks",
                labelling_function="toy_realized_state_at_horizon",
            ),
            cognitive_audit_trail=[
                CognitiveStep(
                    step_index=0,
                    initial_forecast=initial_forecast,
                    additional_reasoning=(
                        f"Observed {len(raw_evidence)} emissions from the"
                        f" toy world; updated forecast via Bayes on each."
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
