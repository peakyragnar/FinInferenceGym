"""Stone 40 promotion gate (toy MVP — Phase 1 NEW Cluster G).

The four-check gate from memory-design.md:

  1. Held-out replay — improves calibration on held-out trajectories.
  2. Cross-model regression — improvement holds under >= 2 models.
  3. Survivorship check — calibrates against delisted universe.
  4. Domain-of-validity declared — non-empty signal_class_id + horizons.

Toy MVP wires up checks 1 and 4 with real evaluation. Checks 2 and 3
are stubbed in the constructed `PromotionCheckResults` with explicit
"pending" markers so the audit trail is honest about what was and was
not validated. Cluster H adds real check 2 (population variants);
Phase 2 NEW adds real check 3 (real delisted universe).

Check 1 toy-mode interpretation: a skill proposed for signal_class_id
`X` and horizons `H` passes if the scoreboard rows under (`X`, `H`)
have **better mean Brier** than the overall scoreboard mean. The
intuition: if forecasts tagged `X` at horizons `H` are systematically
better-calibrated than the agent's average, that tag captures
something real — and a skill anchoring that tag deserves promotion.
The toy bar is loose by design; real held-out replay (re-running the
LLM with the skill in the prompt) lands in Phase 2 NEW.

Check 4 toy-mode interpretation: literal — signal_class_id must be a
non-empty string and `horizons` must be a non-empty tuple.

A rejected proposal returns None. A promoted proposal returns a new
MemoryArtifact with tier="L3" and populated promotion_check_results.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from fingym.evaluator.scoreboard import Scoreboard
from fingym.memory.schema import (
    AuditEntry,
    CrossModelRegressionResult,
    DomainOfValidity,
    HeldOutReplayResult,
    MemoryArtifact,
    PromotionCheckResults,
    SurvivorshipCheckResult,
)


@dataclass(frozen=True)
class Proposal:
    """LLM-emitted candidate memory item (the tool-call output, pre-evaluation).

    Lightweight; constructed from the model's `propose_memory_item` tool
    call. The promotion gate wraps this in a tier="L2" MemoryArtifact
    internally and (if promoted) returns a tier="L3" MemoryArtifact.
    """

    content: str
    signal_class_id: str
    horizons: tuple[int, ...]
    proposed_by_agent: str = "LlmAgent"


# Minimum number of held-out scoreboard rows under the proposed
# signal_class_id required for check 1 to evaluate. Below this, the
# tag's mean Brier is too noisy to trust; promotion fails.
MIN_HELD_OUT_ROWS: int = 10

# The minimum calibration_delta (overall_brier - tag_brier) required
# for check 1 to pass. Positive value means tag-brier < overall-brier,
# i.e., the tag is better-calibrated than average.
MIN_CALIBRATION_DELTA: float = 0.01


def _evaluate_check_1_held_out_replay(
    proposal: Proposal,
    held_out_scoreboard: Scoreboard,
) -> HeldOutReplayResult:
    """Toy-mode check 1: do trajectories tagged with the proposed
    signal_class_id have better mean Brier than the overall scoreboard?"""
    tag_rows = held_out_scoreboard.filter_by_signal_class(proposal.signal_class_id)
    overall_rows = held_out_scoreboard.rows

    if len(tag_rows) < MIN_HELD_OUT_ROWS:
        # Too few held-out rows under this tag to evaluate.
        return HeldOutReplayResult(
            passed=False,
            splits_passed=0,
            calibration_delta=0.0,
        )

    if not overall_rows:
        return HeldOutReplayResult(
            passed=False,
            splits_passed=0,
            calibration_delta=0.0,
        )

    tag_brier = held_out_scoreboard.mean_brier(tag_rows)
    overall_brier = held_out_scoreboard.mean_brier(overall_rows)
    calibration_delta = overall_brier - tag_brier
    passed = calibration_delta >= MIN_CALIBRATION_DELTA
    return HeldOutReplayResult(
        passed=passed,
        splits_passed=1 if passed else 0,
        calibration_delta=calibration_delta,
    )


def _evaluate_check_4_domain_of_validity(proposal: Proposal) -> bool:
    """Toy-mode check 4: signal_class_id non-empty AND horizons non-empty."""
    return bool(proposal.signal_class_id.strip()) and len(proposal.horizons) > 0


def _toy_mode_stub_check_2() -> CrossModelRegressionResult:
    """Check 2 stub — Cluster H wires up real population variants."""
    return CrossModelRegressionResult(
        passed=False,  # explicit: not validated in toy mode
        models_validated=[],
    )


def _toy_mode_stub_check_3() -> SurvivorshipCheckResult:
    """Check 3 stub — Phase 2 NEW wires up real delisted-universe checks."""
    return SurvivorshipCheckResult(
        passed=False,  # explicit: not validated in toy mode
        delisted_sample_size=0,
    )


def evaluate_proposal(
    proposal: Proposal,
    held_out_scoreboard: Scoreboard,
    proposed_at_episode: int = 0,
) -> MemoryArtifact | None:
    """Run the toy-mode promotion gate. Returns an L3 MemoryArtifact if
    promoted, None if rejected.

    Toy-mode promotion rule: checks 1 AND 4 must both pass. Checks 2
    and 3 are stubbed (passed=False) and excluded from the promotion
    decision; their absence is recorded in promotion_check_results so
    the audit trail is honest about what was validated. Cluster H + Phase
    2 NEW wire up real checks 2 and 3, at which point promotion will
    require all four to pass.
    """
    check_1 = _evaluate_check_1_held_out_replay(proposal, held_out_scoreboard)
    check_4_passed = _evaluate_check_4_domain_of_validity(proposal)

    # Toy-mode promotion decision: checks 1 + 4 only.
    if not (check_1.passed and check_4_passed):
        return None

    horizons_as_str = tuple(str(h) for h in proposal.horizons)
    skill_id = f"{proposal.signal_class_id}_{uuid.uuid4().hex[:8]}"
    now = datetime.now()

    return MemoryArtifact(
        id=skill_id,
        tier="L3",
        content=proposal.content,
        domain_of_validity=DomainOfValidity(
            horizons=list(horizons_as_str),
            expression_types=[],
            sectors=[],
        ),
        derived_from=[],  # Phase 2 NEW will link to trajectory_ids
        supersedes=[],
        audit_trail=[
            AuditEntry(
                timestamp=now,
                action="proposed",
                by=proposal.proposed_by_agent,
                reason=f"Episode {proposed_at_episode}; toy-mode proposal.",
            ),
            AuditEntry(
                timestamp=now,
                action="promoted",
                by="system",
                reason=(
                    f"Toy-mode gate (checks 1 + 4). "
                    f"calibration_delta={check_1.calibration_delta:.4f}; "
                    f"checks 2 + 3 stubbed (cluster H / Phase 2 NEW)."
                ),
            ),
        ],
        promotion_check_results=PromotionCheckResults(
            held_out_replay=check_1,
            cross_model_regression=_toy_mode_stub_check_2(),
            survivorship_check=_toy_mode_stub_check_3(),
            domain_of_validity_declared=check_4_passed,
        ),
        promoted_at=now,
    )


__all__ = [
    "MIN_CALIBRATION_DELTA",
    "MIN_HELD_OUT_ROWS",
    "Proposal",
    "evaluate_proposal",
]
