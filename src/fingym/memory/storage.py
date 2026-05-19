"""Memory persistence layer (PYRAMID Stones 39 + 40, memory-design.md).

L3 promoted artifacts live as YAML files on disk at the path the caller
chooses (default: `memory_registry/promoted/<id>.yaml`). Each artifact is
its own file (per-item versioning via git). The directory is git-backed
so the artifact history is auditable: every promotion, demotion, or
retirement shows up as a git commit.

This module is intentionally simple — pydantic does the schema validation
on load; yaml does the serialization. The render_for_system_prompt helper
formats a list of promoted artifacts into a markdown block the LlmAgent
injects into its system prompt at session start.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from fingym.memory.schema import MemoryArtifact

DEFAULT_PROMOTED_DIR: Path = Path("memory_registry") / "promoted"
DEFAULT_PROBATIONARY_DIR: Path = Path("memory_registry") / "probationary"


def save_promoted_skill(artifact: MemoryArtifact, directory: Path | None = None) -> Path:
    """Write an L3 artifact to <directory>/<id>.yaml. Returns the path.

    Creates the directory if missing. The artifact's `id` becomes the
    filename stem. Uses pydantic's `model_dump(mode="json")` so dates and
    datetimes serialize correctly. Aliased fields (e.g., `pass` on
    HeldOutReplayResult) round-trip correctly via `by_alias=True`.

    L3-only — passing an L2 artifact raises. Use `save_probationary_skill`
    for L2.
    """
    if artifact.tier != "L3":
        raise ValueError(
            f"Only L3 artifacts are saved by save_promoted_skill; got tier={artifact.tier}"
        )
    directory = directory if directory is not None else DEFAULT_PROMOTED_DIR
    return _write_artifact(artifact, directory)


def save_probationary_skill(artifact: MemoryArtifact, directory: Path | None = None) -> Path:
    """Write an L2 (probationary) artifact to <directory>/<id>.yaml.

    L2-only — passing an L3 artifact raises. The L2 directory is the
    waiting room: artifacts here have passed at least check 4 + at least
    one variant's check 1, but not yet check 2 (cross-model regression).
    Re-validation cycles (Cluster H) periodically lift L2 artifacts to L3
    when subsequent Scoreboard rows tip enough variants into agreement,
    or retire them if they never gather cross-model support.
    """
    if artifact.tier != "L2":
        raise ValueError(
            f"Only L2 artifacts are saved by save_probationary_skill; got tier={artifact.tier}"
        )
    directory = directory if directory is not None else DEFAULT_PROBATIONARY_DIR
    return _write_artifact(artifact, directory)


def _write_artifact(artifact: MemoryArtifact, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{artifact.id}.yaml"
    data = artifact.model_dump(mode="json", by_alias=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return path


def load_promoted_skills(directory: Path | None = None) -> list[MemoryArtifact]:
    """Read all L3 `*.yaml` files in `directory`; validate via pydantic;
    return the artifacts sorted by id for deterministic ordering.

    Silently returns an empty list if the directory is missing. Invalid
    YAML or schema-violating content RAISES — corrupt promoted memory is
    a deploy-time failure, not a silent skip.
    """
    directory = directory if directory is not None else DEFAULT_PROMOTED_DIR
    return _load_artifacts(directory)


def load_probationary_skills(
    directory: Path | None = None,
) -> list[MemoryArtifact]:
    """Read all L2 `*.yaml` files in `directory`. Re-validation cycles
    iterate over the returned list and either promote each to L3 or retire it."""
    directory = directory if directory is not None else DEFAULT_PROBATIONARY_DIR
    return _load_artifacts(directory)


def _load_artifacts(directory: Path) -> list[MemoryArtifact]:
    if not directory.exists():
        return []
    artifacts: list[MemoryArtifact] = []
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        artifacts.append(MemoryArtifact.model_validate(data))
    return sorted(artifacts, key=lambda a: a.id)


def render_for_system_prompt(artifacts: list[MemoryArtifact]) -> str:
    """Render promoted artifacts as a markdown block for injection into
    the LlmAgent's system prompt at session start.

    Empty input -> empty string (caller handles the no-memory case).
    Each artifact contributes one block with its content + domain-of-
    validity. The block is intentionally compact — the agent reads many
    skills at once; verbose formatting wastes context.
    """
    if not artifacts:
        return ""
    blocks: list[str] = ["# Promoted skills (read at session start)"]
    for art in artifacts:
        horizons_str = ", ".join(art.domain_of_validity.horizons) or "(none)"
        blocks.append(f"\n## {art.id}\n- Domain: horizons={horizons_str}\n- Content: {art.content}")
    return "\n".join(blocks)


__all__ = [
    "DEFAULT_PROBATIONARY_DIR",
    "DEFAULT_PROMOTED_DIR",
    "load_probationary_skills",
    "load_promoted_skills",
    "render_for_system_prompt",
    "save_probationary_skill",
    "save_promoted_skill",
]
