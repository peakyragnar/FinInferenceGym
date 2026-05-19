"""Re-validation cycles for the memory pyramid (PYRAMID Stone 40, Cluster H).

Cluster G's L3 was "promote and forget" — once a skill graduated, it stayed
in L3 regardless of subsequent evidence. Cluster H makes memory continuous:
periodically re-run the gate on every existing artifact (both L2 and L3),
promoting / demoting / retiring based on the current Scoreboard state.

Trigger: **every `REVALIDATION_INTERVAL_ROWS` new Scoreboard rows**
(default 50; operator-tunable module constant). The orchestrator calls
`should_revalidate(...)` to check; if True, calls `revalidate(...)` which
returns a `RevalidationReport` summarizing what changed.

The four transition outcomes (per artifact):

| Starting tier | Re-validation result | Action |
|---|---|---|
| L3 | Still passes checks 1 + 2 + 4 | Stays L3 |
| L3 | Now fails check 1 or check 2 | Demoted to L2; status stays "promoted" but tier flips |
| L2 | Now passes checks 1 + 2 + 4 | Promoted to L3 |
| L2 | Has been L2 for ≥ `MAX_L2_CYCLES` without graduating | Retired |

Demoted artifacts have an "demoted" entry appended to their audit_trail
explaining the reason. Retired artifacts get a "retired" entry and their
`status` flips to "retired"; the file stays in git for audit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from fingym.evaluator.scoreboard import Scoreboard
from fingym.memory.promotion import (
    DEFAULT_MIN_VARIANTS_PASSING,
    Proposal,
    _check_1_per_variant,
    _evaluate_check_4_domain_of_validity,
    _toy_mode_stub_check_3,
)
from fingym.memory.schema import (
    AuditEntry,
    CrossModelRegressionResult,
    MemoryArtifact,
    PromotionCheckResults,
)
from fingym.memory.storage import (
    DEFAULT_PROBATIONARY_DIR,
    DEFAULT_PROMOTED_DIR,
    load_probationary_skills,
    load_promoted_skills,
    save_probationary_skill,
    save_promoted_skill,
)

# Default re-validation cadence (operator-tunable).
REVALIDATION_INTERVAL_ROWS: int = 50

# Maximum number of consecutive re-validation cycles an artifact may
# remain in L2 without being promoted before being retired. Counted via
# the artifact's audit_trail entries.
MAX_L2_CYCLES: int = 5


@dataclass
class RevalidationReport:
    """Summary of one `revalidate(...)` call.

    Returned to the caller (and useful for tests). Reports the IDs of
    artifacts whose status changed; the underlying YAML files on disk
    are already updated by `revalidate` itself.
    """

    promoted_l2_to_l3: list[str] = field(default_factory=list)
    demoted_l3_to_l2: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)


def should_revalidate(
    new_rows_since_last: int,
    interval_rows: int = REVALIDATION_INTERVAL_ROWS,
) -> bool:
    """Return True when enough new Scoreboard rows have accumulated to
    justify another re-validation pass. The caller is responsible for
    tracking `new_rows_since_last` (typically the difference between the
    current Scoreboard size and the size at the previous revalidation)."""
    return new_rows_since_last >= interval_rows


def _proposal_for_artifact(artifact: MemoryArtifact) -> Proposal:
    """Reconstruct a synthetic Proposal from an existing artifact so the
    gate's per-variant check 1 can re-evaluate it.

    The reconstructed Proposal carries the artifact's content, sci, and
    horizons. The proposer field is set to "system_revalidation" — the
    distinguishable audit marker that this is a revalidation pass, not a
    fresh LLM proposal.
    """
    horizons_int: tuple[int, ...] = tuple(
        int(h) for h in artifact.domain_of_validity.horizons if h.isdigit()
    )
    return Proposal(
        content=artifact.content,
        signal_class_id=_signal_class_id_from_artifact(artifact),
        horizons=horizons_int or (1,),
        proposed_by_agent="system_revalidation",
    )


def _signal_class_id_from_artifact(artifact: MemoryArtifact) -> str:
    """Recover the signal_class_id from the artifact's id.

    The promotion gate sets `id = f"{signal_class_id}_{uuid_hex8}"`. Strip
    the trailing 8-char uuid suffix to recover the signal_class_id."""
    # The id has the form "<sci>_<8hex>". Strip the last 9 chars (underscore + 8 hex).
    if len(artifact.id) > 9 and artifact.id[-9] == "_":
        return artifact.id[:-9]
    # Fallback: use the whole id (shouldn't happen for artifacts created
    # by `evaluate_proposal*`, but be defensive).
    return artifact.id


def _count_l2_cycles(artifact: MemoryArtifact) -> int:
    """Return the number of times this artifact has been re-evaluated
    while in L2 without being promoted. Counted from audit_trail entries
    with action="proposed" and by="system_revalidation"."""
    return sum(
        1
        for entry in artifact.audit_trail
        if entry.action == "proposed" and entry.by == "system_revalidation"
    )


def _is_retired(artifact: MemoryArtifact) -> bool:
    """An artifact is retired iff its most recent audit_trail entry has
    action == "retired". The schema preserves the full history; retirement
    is a status marker via audit, not a deleted file."""
    for entry in reversed(artifact.audit_trail):
        if entry.action == "retired":
            return True
        if entry.action in ("promoted", "demoted"):
            return False
    return False


def revalidate(
    scoreboard: Scoreboard,
    l3_dir: Path | None = None,
    l2_dir: Path | None = None,
    *,
    min_variants_passing: int = DEFAULT_MIN_VARIANTS_PASSING,
    max_l2_cycles: int = MAX_L2_CYCLES,
) -> RevalidationReport:
    """Re-run the Cluster H gate on every existing L2 and L3 artifact.

    Side effects:
      - L3 artifacts that no longer pass checks 1 + 2 + 4 get demoted:
        their L3 YAML is removed and they are written to L2 with a
        "demoted" audit_trail entry appended.
      - L2 artifacts that now pass checks 1 + 2 + 4 get promoted:
        their L2 YAML is removed and they are written to L3 with a
        "promoted" audit_trail entry.
      - L2 artifacts that have remained probationary for `max_l2_cycles`
        re-validation passes without graduating are retired (status
        flipped to "retired"; YAML rewritten with the new status).

    Returns a RevalidationReport summarizing what changed.
    """
    l3_dir = l3_dir if l3_dir is not None else DEFAULT_PROMOTED_DIR
    l2_dir = l2_dir if l2_dir is not None else DEFAULT_PROBATIONARY_DIR
    report = RevalidationReport()
    now = datetime.now()

    # ---- L3 re-validation: demote if checks 1 + 2 + 4 no longer pass ----
    for artifact in load_promoted_skills(l3_dir):
        proposal = _proposal_for_artifact(artifact)
        check_4_passed = _evaluate_check_4_domain_of_validity(proposal)
        per_variant = _check_1_per_variant(scoreboard, proposal.signal_class_id)
        variants_passing = sorted(agent_id for agent_id, r in per_variant.items() if r.passed)
        check_2_passed = len(variants_passing) >= min_variants_passing
        if check_4_passed and check_2_passed and variants_passing:
            report.unchanged.append(artifact.id)
            continue
        # Demote: build new L2 artifact with audit entry.
        new_audit = [
            *artifact.audit_trail,
            AuditEntry(
                timestamp=now,
                action="demoted",
                by="system_revalidation",
                reason=(
                    f"L3 re-validation failed. "
                    f"variants_passing={variants_passing} "
                    f"(needed >= {min_variants_passing}); "
                    f"check_4_passed={check_4_passed}."
                ),
            ),
        ]
        demoted = artifact.model_copy(
            update={
                "tier": "L2",
                "audit_trail": new_audit,
                "promotion_check_results": None,
                "promoted_at": None,
            }
        )
        save_probationary_skill(demoted, l2_dir)
        (l3_dir / f"{artifact.id}.yaml").unlink(missing_ok=True)
        report.demoted_l3_to_l2.append(artifact.id)

    # ---- L2 re-validation: promote or retire ----
    for artifact in load_probationary_skills(l2_dir):
        if _is_retired(artifact):
            continue  # already retired; skip
        proposal = _proposal_for_artifact(artifact)
        check_4_passed = _evaluate_check_4_domain_of_validity(proposal)
        per_variant = _check_1_per_variant(scoreboard, proposal.signal_class_id)
        variants_passing = sorted(agent_id for agent_id, r in per_variant.items() if r.passed)
        check_2_passed = len(variants_passing) >= min_variants_passing

        if check_4_passed and check_2_passed and variants_passing:
            # Graduate to L3.
            best_variant_id = max(per_variant, key=lambda a: per_variant[a].calibration_delta)
            aggregate_check_1 = per_variant[best_variant_id]
            new_audit = [
                *artifact.audit_trail,
                AuditEntry(
                    timestamp=now,
                    action="promoted",
                    by="system_revalidation",
                    reason=(
                        f"L2 -> L3 graduation. "
                        f"variants_passing={variants_passing} "
                        f"(>= {min_variants_passing}). "
                        f"calibration_delta_best={aggregate_check_1.calibration_delta:.4f}."
                    ),
                ),
            ]
            promoted = artifact.model_copy(
                update={
                    "tier": "L3",
                    "audit_trail": new_audit,
                    "promotion_check_results": PromotionCheckResults(
                        held_out_replay=aggregate_check_1,
                        cross_model_regression=CrossModelRegressionResult(
                            passed=True, models_validated=variants_passing
                        ),
                        survivorship_check=_toy_mode_stub_check_3(),
                        domain_of_validity_declared=check_4_passed,
                    ),
                    "promoted_at": now,
                }
            )
            save_promoted_skill(promoted, l3_dir)
            (l2_dir / f"{artifact.id}.yaml").unlink(missing_ok=True)
            report.promoted_l2_to_l3.append(artifact.id)
            continue

        # Add a probationary "proposed" entry so we can count cycles.
        new_audit = [
            *artifact.audit_trail,
            AuditEntry(
                timestamp=now,
                action="proposed",
                by="system_revalidation",
                reason=(
                    f"L2 re-validation: variants_passing={variants_passing}; still probationary."
                ),
            ),
        ]
        rechecked = artifact.model_copy(update={"audit_trail": new_audit})
        cycles_so_far = _count_l2_cycles(rechecked)
        if cycles_so_far >= max_l2_cycles:
            # Retire: status flip, file stays for audit.
            retired_audit = [
                *rechecked.audit_trail,
                AuditEntry(
                    timestamp=now,
                    action="retired",
                    by="system_revalidation",
                    reason=(f"L2 for {cycles_so_far} cycles without graduating; retired."),
                ),
            ]
            retired = rechecked.model_copy(update={"audit_trail": retired_audit})
            save_probationary_skill(retired, l2_dir)
            report.retired.append(artifact.id)
        else:
            save_probationary_skill(rechecked, l2_dir)
            report.unchanged.append(artifact.id)

    return report


__all__ = [
    "MAX_L2_CYCLES",
    "REVALIDATION_INTERVAL_ROWS",
    "RevalidationReport",
    "revalidate",
    "should_revalidate",
]
