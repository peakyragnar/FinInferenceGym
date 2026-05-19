"""Population variants for the LLM cognition layer (PYRAMID Stone 38).

A population is a small set of `LlmAgentVariant` configurations that run in
parallel on the same emission stream. Each variant is a separate LlmAgent
instance with its own `agent_id` on Scoreboard rows. Variants share
everything downstream (calibrator, Action Engine, Scoreboard, gate); they
differ only in cognition (model + prompt style).

The Cluster H default mix combines:
- Cross-prompt agreement within Haiku (same model, different framing)
- Cross-architecture agreement (Haiku vs Sonnet)

Cost: ~$0.10 per full integration-test run (~30 API calls; ~10 episodes
times 3 variants). Future axes (deferred): temperature, promoted-skills
subset, additional architectures.

`build_population(variants, promoted_skills)` is the factory: constructs
one `LlmAgent` per variant, each with its own `AnthropicClient(model,
prompt_style)`. The same `promoted_skills` list is injected into every
variant — operator-controlled which variants see which skills.
"""

from __future__ import annotations

from dataclasses import dataclass

from fingym.llm.anthropic import AnthropicClient
from fingym.memory.schema import MemoryArtifact
from fingym.toys.llm_agent import LlmAgent

# Haiku and Sonnet model IDs used by the Cluster H default population.
HAIKU_MODEL: str = "claude-haiku-4-5-20251001"
SONNET_MODEL: str = "claude-sonnet-4-6"

# Cluster H prompt styles. Empty string = base system prompt only.
_VALUE_INVESTOR_STYLE: str = (
    "Additionally: adopt a VALUE-INVESTOR framing. Weight signs of durable "
    "moat, sustainable margins, and conservative balance-sheet metrics more "
    "heavily than recent momentum. Treat single-period STRONG signals with "
    "appropriate caution if the longer pattern is mixed."
)


@dataclass(frozen=True)
class LlmAgentVariant:
    """One operator-controlled configuration in the population.

    Variants differ only on `model` + `prompt_style`. The `name` is the
    `agent_id` used on Scoreboard rows so the gate can slice by variant.
    """

    name: str
    model: str
    prompt_style: str = ""


# Default 3-variant mix (Cluster H, confirmed 2026-05-18):
#   1. Haiku 4.5 with the base prompt only
#   2. Haiku 4.5 with a value-investor framing addendum
#   3. Sonnet 4.6 with the base prompt only
#
# Picked to combine cross-prompt agreement (within Haiku) with cross-
# architecture agreement (Haiku vs Sonnet). ~$0.10 per test run.
DEFAULT_VARIANTS: tuple[LlmAgentVariant, ...] = (
    LlmAgentVariant(name="haiku_default", model=HAIKU_MODEL, prompt_style=""),
    LlmAgentVariant(
        name="haiku_value_investor",
        model=HAIKU_MODEL,
        prompt_style=_VALUE_INVESTOR_STYLE,
    ),
    LlmAgentVariant(name="sonnet_default", model=SONNET_MODEL, prompt_style=""),
)


def build_population(
    variants: tuple[LlmAgentVariant, ...] = DEFAULT_VARIANTS,
    promoted_skills: list[MemoryArtifact] | None = None,
) -> list[LlmAgent]:
    """Construct one `LlmAgent` per variant. All variants see the same
    `promoted_skills` (operator can pass different subsets per variant if
    needed by calling this once per subset).

    Each LlmAgent's `name` matches its variant's `name`, which surfaces on
    Scoreboard rows as `agent_id` so the gate can slice by variant.
    """
    promoted = list(promoted_skills or [])
    population: list[LlmAgent] = []
    for variant in variants:
        client = AnthropicClient(model=variant.model, prompt_style=variant.prompt_style)
        agent = LlmAgent(
            client=client,
            name=variant.name,
            promoted_skills=promoted,
        )
        population.append(agent)
    return population


__all__ = [
    "DEFAULT_VARIANTS",
    "HAIKU_MODEL",
    "SONNET_MODEL",
    "LlmAgentVariant",
    "build_population",
]
