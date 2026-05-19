"""Unit tests for the memory artifact schema (Stone 20 / memory-design.md).

Covers:
  - Construction of well-formed L2 and L3 artifacts.
  - L3 invariant: promotion_check_results AND promoted_at required.
  - DerivedFromEdge invariant: exactly one of trajectory_id /
    observation_id / artifact_id set per edge.
  - The illustrative sample artifact in memory_registry/promoted/
    parses cleanly from YAML and validates via the schema.
  - YAML alias `pass` works on the promotion-result inner types.
  - artifact -> YAML -> artifact round-trip preserves content.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from fingym.memory.schema import (
    AuditEntry,
    CrossModelRegressionResult,
    DerivedFromEdge,
    DomainOfValidity,
    HeldOutReplayResult,
    MemoryArtifact,
    PromotionCheckResults,
    SurvivorshipCheckResult,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
# The illustrative L3 fixture used by this schema-validation test. Kept
# under tests/fixtures/ so it does NOT pollute `memory_registry/promoted/`
# (which the operator dashboard reads as the live promoted-skills directory).
SAMPLE_PATH = REPO_ROOT / "tests" / "fixtures" / "memory" / "illustrative_l3_skill.yaml"


def _l2_kwargs(**overrides: Any) -> dict[str, Any]:
    """Helper: valid L2 artifact kwargs, overridable by tests."""
    base: dict[str, Any] = {
        "id": "test-l2-001",
        "tier": "L2",
        "content": "Test claim under validation.",
        "domain_of_validity": DomainOfValidity(horizons=["3m"], sectors=["test"]),
        "derived_from": [DerivedFromEdge(trajectory_id="test-traj-001")],
        "audit_trail": [
            AuditEntry(
                timestamp=datetime.now(UTC),
                action="proposed",
                by="test-agent",
                reason="test proposal",
            )
        ],
    }
    base.update(overrides)
    return base


def _l3_kwargs(**overrides: Any) -> dict[str, Any]:
    """Helper: valid L3 artifact kwargs, overridable by tests."""
    base: dict[str, Any] = {
        "id": "test-l3-001",
        "tier": "L3",
        "content": "Test promoted skill.",
        "domain_of_validity": DomainOfValidity(horizons=["6m"], sectors=["test"]),
        "derived_from": [DerivedFromEdge(trajectory_id="test-traj-002")],
        "audit_trail": [
            AuditEntry(
                timestamp=datetime.now(UTC),
                action="proposed",
                by="test-agent",
                reason="proposal",
            ),
            AuditEntry(
                timestamp=datetime.now(UTC),
                action="promoted",
                by="system",
                reason="passed gate",
            ),
        ],
        "promotion_check_results": PromotionCheckResults(
            held_out_replay=HeldOutReplayResult(
                passed=True, splits_passed=3, calibration_delta=0.05
            ),
            cross_model_regression=CrossModelRegressionResult(
                passed=True, models_validated=["model-a", "model-b"]
            ),
            survivorship_check=SurvivorshipCheckResult(passed=True, delisted_sample_size=20),
            domain_of_validity_declared=True,
        ),
        "promoted_at": datetime.now(UTC),
    }
    base.update(overrides)
    return base


def test_l2_artifact_constructs() -> None:
    """A well-formed L2 artifact constructs cleanly."""
    artifact = MemoryArtifact(**_l2_kwargs())
    assert artifact.tier == "L2"
    assert artifact.promotion_check_results is None
    assert artifact.promoted_at is None


def test_l3_artifact_constructs() -> None:
    """A well-formed L3 artifact constructs cleanly."""
    artifact = MemoryArtifact(**_l3_kwargs())
    assert artifact.tier == "L3"
    assert artifact.promotion_check_results is not None
    assert artifact.promoted_at is not None


def test_l3_rejected_without_promotion_check_results() -> None:
    """L3 artifact missing promotion_check_results is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        MemoryArtifact(**_l3_kwargs(promotion_check_results=None))
    assert "promotion_check_results" in str(exc_info.value)


def test_l3_rejected_without_promoted_at() -> None:
    """L3 artifact missing promoted_at is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        MemoryArtifact(**_l3_kwargs(promoted_at=None))
    assert "promoted_at" in str(exc_info.value)


def test_l2_allowed_without_promotion_evidence() -> None:
    """L2 artifacts don't require promotion_check_results or promoted_at."""
    artifact = MemoryArtifact(**_l2_kwargs())
    assert artifact.promotion_check_results is None
    assert artifact.promoted_at is None


def test_derived_from_requires_exactly_one_field() -> None:
    """DerivedFromEdge must have exactly one of the three ids set."""
    with pytest.raises(ValidationError):
        DerivedFromEdge()  # zero ids set
    with pytest.raises(ValidationError):
        DerivedFromEdge(trajectory_id="a", observation_id="b")  # two ids set


def test_audit_action_constrained_to_literal() -> None:
    """audit_trail action must be one of the four lifecycle actions."""
    with pytest.raises(ValidationError):
        AuditEntry(
            timestamp=datetime.now(UTC),
            action="invalid_action",
            by="x",
            reason="x",
        )


def test_invalid_tier_rejected() -> None:
    """tier must be L2 or L3; arbitrary strings are rejected."""
    with pytest.raises(ValidationError):
        MemoryArtifact(**_l2_kwargs(tier="L1"))


def test_memory_artifact_is_frozen() -> None:
    """MemoryArtifact is immutable; reassigning a field raises."""
    artifact = MemoryArtifact(**_l2_kwargs())
    # The pydantic mypy plugin correctly marks frozen-model fields as
    # read-only Properties at the static level. The type-ignore opts out
    # of that static check so we can verify the runtime raises.
    with pytest.raises(ValidationError):
        artifact.tier = "L3"  # type: ignore[misc]


def test_held_out_replay_pass_alias_works() -> None:
    """HeldOutReplayResult accepts `pass` as YAML alias for `passed`."""
    from_yaml_style = HeldOutReplayResult.model_validate(
        {"pass": True, "splits_passed": 3, "calibration_delta": 0.04}
    )
    assert from_yaml_style.passed is True


def test_sample_artifact_parses_from_yaml() -> None:
    """The illustrative sample in memory_registry/promoted/ validates.

    This is the exit-criterion proof for Phase 0 substep 7: "Memory
    schema is documented and validates a sample skill artifact."
    """
    assert SAMPLE_PATH.exists(), f"Sample artifact missing at {SAMPLE_PATH}"
    with SAMPLE_PATH.open() as f:
        data = yaml.safe_load(f)
    artifact = MemoryArtifact.model_validate(data)
    assert artifact.tier == "L3"
    assert artifact.promotion_check_results is not None
    assert artifact.promotion_check_results.held_out_replay.passed is True
    assert artifact.promotion_check_results.cross_model_regression.passed is True
    assert artifact.promotion_check_results.survivorship_check.passed is True
    assert artifact.promotion_check_results.domain_of_validity_declared is True
    assert len(artifact.audit_trail) >= 2  # proposed + promoted at minimum
    assert artifact.id == "00000000-0000-0000-0000-000000000001"


def test_yaml_round_trip_preserves_structure() -> None:
    """artifact -> YAML -> artifact round-trip preserves content.

    Uses by_alias=True on dump so YAML carries `pass:` (the canonical
    on-disk form). On load, the alias maps back to `passed`.
    """
    original = MemoryArtifact(**_l3_kwargs())
    as_dict = original.model_dump(mode="json", by_alias=True)
    as_yaml = yaml.safe_dump(as_dict)
    rehydrated_data = yaml.safe_load(as_yaml)
    rehydrated = MemoryArtifact.model_validate(rehydrated_data)
    assert rehydrated.id == original.id
    assert rehydrated.tier == original.tier
    assert rehydrated.content == original.content
    assert (
        rehydrated.promotion_check_results is not None
        and original.promotion_check_results is not None
    )
    assert (
        rehydrated.promotion_check_results.held_out_replay.passed
        == original.promotion_check_results.held_out_replay.passed
    )
