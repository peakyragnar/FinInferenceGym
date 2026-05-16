"""interface.py — typed Protocol for Contract-emitting agents.

The model interface: raw evidence in, structured Contract out. This is
DESIGN.md #5 (cognition/verification boundary) in code. Every concrete
agent — toy Bayesian, pure-code Phase-2 baseline, LLM-driven model
agent — satisfies this Protocol.

The Protocol is what makes models swappable (DESIGN.md #7): the evaluator
doesn't know or care which model is behind the agent; it consumes
Contracts and scores them. Swap `ClaudeAgent` for `GPTAgent` — the gym
doesn't notice.

The Protocol is GENERIC over the Evidence type so different agent kinds
can take different evidence shapes:
  - Toy agents: Evidence = list of emission labels (the synthetic-market
    stream).
  - Phase 2+ model-driven agents: Evidence = a richer typed pipe (raw
    transcripts, options chains, fundamentals — Stone 28).

Subclassing is not required. Structural conformance (the Protocol shape)
is checked at the type level by mypy.
"""

from typing import Protocol

from fingym.agents.contract import Contract


class Agent[Evidence](Protocol):
    """Minimum interface a Contract-emitting agent satisfies.

    Generic over the Evidence type. mypy enforces the Protocol structurally;
    concrete agents just need a matching `agent_id` attribute and an
    `emit_contract` method with the right signature.
    """

    agent_id: str

    def emit_contract(self, raw_evidence: Evidence) -> Contract:
        """Form a belief from raw evidence and emit a structured Contract.

        Inputs: raw evidence appropriate to the agent's universe.

        Outputs: a Contract the validator can accept or reject. If the
        Contract fails validation, it is recorded as a verifier-rejection
        (DESIGN.md #5) — not scored, not persisted to the trajectory store.
        """
        ...
