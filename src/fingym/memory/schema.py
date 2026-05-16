"""schema.py — pydantic model for memory artifacts (L2 / L3).

The structured form of an L2 (probationary) or L3 (promoted) memory
artifact. See [memory-design.md](memory-design.md) for the full memory
architecture and the YAML schema this Python model corresponds to.

L2 artifacts are agent-proposed claims under validation by the
promotion gate. L3 artifacts have survived the four-check gate
(held-out replay + cross-model regression + survivorship check +
domain-of-validity declared) and are the validated, model-agnostic
skills the agent reads at session start.

L3 invariant: promotion_check_results and promoted_at MUST be set. L2
artifacts MAY have them absent (typically do). Enforced by the model
validator at the bottom of MemoryArtifact.

Deferred-but-typed-from-day-1 fields (contradicts, depends_on,
confidence) ship as Optional with empty / None defaults. When their
features land (memory-design.md "Deferrals"), populating them requires
no schema migration.

This file is the source of truth for the in-memory representation. YAML
files in memory_registry/{probationary,promoted,retired}/<id>.yaml are
the on-disk representation; the Phase 4 lint
mechanisms/lints/validate_memory_artifacts.py (deferred) will parse
YAML and validate against this schema at commit time.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AuditEntry(BaseModel):
    """One event in the artifact's lifecycle.

    Lifecycle actions: proposed (agent emits L2) -> promoted (passes
    gate, becomes L3) -> demoted (re-validation fails, drops back to
    L2 or retired) -> retired (removed from active memory).
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    action: Literal["proposed", "promoted", "demoted", "retired"]
    by: str  # agent_id or "system"
    reason: str  # markdown


class DomainOfValidity(BaseModel):
    """Where the artifact's claim is valid.

    Every L3 skill must declare its scope (memory-design.md "Promotion
    gate — the four DESIGN.md checks", item 4). Horizons /
    expression_types / sectors are list[str] using the project's
    vocabulary (e.g., "3m", "equity_long", "tech"). time_range_*
    bound when the skill applies; time_range_end == None means
    "still in effect."
    """

    model_config = ConfigDict(frozen=True)

    horizons: list[str] = Field(default_factory=list)
    expression_types: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    time_range_start: date | None = None
    time_range_end: date | None = None


class DerivedFromEdge(BaseModel):
    """One pointer to an upstream object this artifact was derived from.

    Exactly one of trajectory_id / observation_id / artifact_id is set
    per edge entry. derived_from on MemoryArtifact may contain multiple
    edges (derivation from multiple sources).
    """

    model_config = ConfigDict(frozen=True)

    trajectory_id: str | None = None
    observation_id: str | None = None
    artifact_id: str | None = None

    @model_validator(mode="after")
    def _exactly_one_set(self) -> "DerivedFromEdge":
        count = sum(
            x is not None for x in (self.trajectory_id, self.observation_id, self.artifact_id)
        )
        if count != 1:
            raise ValueError(
                "DerivedFromEdge must have exactly one of "
                "trajectory_id / observation_id / artifact_id set; "
                f"got {count}"
            )
        return self


class HeldOutReplayResult(BaseModel):
    """First of the four promotion-gate checks.

    Does adding this artifact to the agent's context improve calibration
    on a held-out set of trajectories the artifact was NOT derived from?
    `passed` carries the YAML alias `pass` (Python keyword).
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    passed: bool = Field(alias="pass")
    splits_passed: int = Field(ge=0)
    calibration_delta: float


class CrossModelRegressionResult(BaseModel):
    """Second of the four promotion-gate checks.

    Does the calibration improvement hold under at least two model
    engines? If a skill only works for one model, it's overfit to that
    model's quirks, not a real pattern.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    passed: bool = Field(alias="pass")
    models_validated: list[str]


class SurvivorshipCheckResult(BaseModel):
    """Third of the four promotion-gate checks.

    If the artifact uses transcript-derived signals, does it still
    calibrate against the delisted shadow universe? Survivor-only data
    biases toward winners; the skill must hold on losers too.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    passed: bool = Field(alias="pass")
    delisted_sample_size: int = Field(ge=0)


class PromotionCheckResults(BaseModel):
    """The four-check gate's outcomes (memory-design.md "Promotion gate").

    Required for L3 artifacts; absent for L2 artifacts. All four checks
    must pass for promotion to L3.
    """

    model_config = ConfigDict(frozen=True)

    held_out_replay: HeldOutReplayResult
    cross_model_regression: CrossModelRegressionResult
    survivorship_check: SurvivorshipCheckResult
    domain_of_validity_declared: bool


class MemoryArtifact(BaseModel):
    """An L2 (probationary) or L3 (promoted) memory artifact.

    Source of truth: memory-design.md "YAML schema for L2 / L3
    artifacts." On-disk form is YAML in
    memory_registry/{probationary,promoted,retired}/<id>.yaml (UUID
    filename per "Per-item versioning via git").

    L3 invariant enforced below: promotion_check_results AND
    promoted_at MUST be set on L3 artifacts.
    """

    model_config = ConfigDict(frozen=True)

    # Identity + tier
    id: str  # UUID string; the YAML filename
    tier: Literal["L2", "L3"]

    # The claim itself + scope
    content: str  # markdown body
    domain_of_validity: DomainOfValidity

    # Provenance
    derived_from: list[DerivedFromEdge]
    supersedes: list[str] = Field(default_factory=list)
    audit_trail: list[AuditEntry]

    # Promotion evidence (required for L3; None for L2)
    promotion_check_results: PromotionCheckResults | None = None
    promoted_at: datetime | None = None

    # Deferred-but-typed-from-day-1 fields (memory-design.md "Deferrals")
    contradicts: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    confidence: float | None = None

    @model_validator(mode="after")
    def _l3_requires_promotion_evidence(self) -> "MemoryArtifact":
        if self.tier == "L3":
            if self.promotion_check_results is None:
                raise ValueError(
                    "L3 artifact must carry promotion_check_results "
                    "(the gate results that justified promotion)"
                )
            if self.promoted_at is None:
                raise ValueError("L3 artifact must carry promoted_at timestamp")
        return self
