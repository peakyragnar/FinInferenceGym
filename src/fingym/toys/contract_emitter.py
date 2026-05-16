"""contract_emitter.py — Stone 19 demo: BayesianAgent wrapped to emit Contracts.

Proves the Agent Protocol (src/fingym/agents/interface.py) compiles against
a concrete implementation. The existing BayesianAgent from adversarial_agents
produces a 3-state belief; this adapter wraps it to emit a valid pydantic
Contract per CONTRACT.md.

This is the test fixture for Phase 0 substep 6's exit criterion: "Model
interface contract is documented; a stub agent compiles against it."

Run: `uv run python -m fingym.toys.contract_emitter`
"""

from datetime import UTC, datetime
from uuid import uuid4

from fingym.agents.contract import (
    BeliefDistribution,
    CognitiveStep,
    Contract,
    Falsifier,
    HiddenStateHypothesis,
    LabelPlan,
    NoAction,
)
from fingym.agents.contract_validator import validate_contract
from fingym.toys.adversarial_agents import BayesianAgent
from fingym.toys.synthetic_market import (
    STATES,
    STONE_11A_AGENT_PRIOR,
    Emission,
)


class BayesianContractEmitter:
    """Wraps a BayesianAgent to emit valid Contracts per CONTRACT.md.

    Satisfies the Agent[list[Emission]] Protocol structurally: has an
    `agent_id` attribute and an `emit_contract(raw_evidence)` method
    returning a Contract. mypy verifies structural conformance.
    """

    def __init__(self) -> None:
        self.agent_id = "BayesianContractEmitter@stone19"
        self.model_id = "fingym.bayesian.v1"
        self.prompt_version = "stone19_demo"
        self._bayesian = BayesianAgent(STONE_11A_AGENT_PRIOR, name="BayesianAgent")

    def emit_contract(self, raw_evidence: list[Emission]) -> Contract:
        """Form a belief from the emission stream and emit a Contract.

        Each emission is observed via the wrapped BayesianAgent. After all
        emissions are processed, the agent's final belief is packaged into
        a Contract along with hypothesis space, falsifier, label plan, and
        a single-step cognitive audit trail (Phase 0 — no iteration yet).
        """
        # CompanyState is a Literal subtype of str; dict[Literal, float] is not
        # dict[str, float] under mypy invariance. Comprehension widens the
        # key type explicitly. The BeliefDistribution schema is generic over
        # the hypothesis label space; toys label by state name.
        initial_belief = BeliefDistribution(
            probabilities={str(s): p for s, p in STONE_11A_AGENT_PRIOR.items()}
        )
        for emission in raw_evidence:
            self._bayesian.observe(emission)
        final_belief = BeliefDistribution(
            probabilities={str(s): p for s, p in self._bayesian.belief.items()}
        )
        decision_time = datetime.now(UTC)

        hypotheses = [
            HiddenStateHypothesis(label=state, description=f"company state: {state}")
            for state in STATES
        ]

        return Contract(
            contract_id=str(uuid4()),
            decision_time=decision_time,
            agent_id=self.agent_id,
            model_id=self.model_id,
            prompt_version=self.prompt_version,
            evidence_ids=[],  # toy world; no L0 emissions table at Phase 0
            hidden_state_hypotheses=hypotheses,
            ai_belief=final_belief,
            market_implied_belief=None,
            belief_delta=None,
            horizon="12_ticks",
            action_or_no_action=NoAction(
                reason=(
                    "Stone 19 demo emits NoAction; the stub doesn't yet"
                    " decide trades. Stone 13 (decision quality) lights"
                    " up here in Phase 2+ when the model agent picks"
                    " expressions."
                )
            ),
            recommended_size=0.0,
            falsifiers=[
                Falsifier(
                    description=(
                        "If the realized hidden state at the horizon is"
                        " not the highest-probability state in ai_belief,"
                        " the agent's call was wrong on truth."
                    )
                )
            ],
            label_plan=LabelPlan(
                horizon="12_ticks",
                label_source="toy_ground_truth",
                labelling_function="identity",
            ),
            cognitive_audit_trail=[
                CognitiveStep(
                    step_index=0,
                    initial_belief=initial_belief,
                    additional_reasoning=(
                        f"Observed {len(raw_evidence)} emissions from the"
                        f" toy world; updated belief via Bayes on each."
                    ),
                    updated_belief=final_belief,
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

    print("\nStone 19 demo — BayesianContractEmitter emits a Contract")
    print(f"  agent_id            = {contract.agent_id}")
    print(f"  decision_time       = {contract.decision_time.isoformat()}")
    print(f"  ai_belief           = {contract.ai_belief.probabilities}")
    print(f"  action_type         = {contract.action_or_no_action.action_type}")
    print(f"  horizon             = {contract.horizon}")
    print(f"  falsifiers count    = {len(contract.falsifiers)}")
    print(f"  cognitive_steps     = {len(contract.cognitive_audit_trail)}")
    print(f"  validator           = {'ACCEPTED' if result.accepted else 'REJECTED'}")
    if not result.accepted:
        for reason in result.rejection_reasons:
            print(f"    - {reason}")


if __name__ == "__main__":
    demo_emit_and_validate()
