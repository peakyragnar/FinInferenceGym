"""LlmAgent — the first model-driven agent (PYRAMID Stone 30).

Replaces the hand-coded BayesianAgent / ConfidentAgent / UniformAgent with
a real frontier model as the cognitive engine. The model reads the
emission stream as text, self-tags its forecast with a `signal_class_id`
it chooses, and emits a forecast distribution over the five return
buckets via tool-call structured output.

Satisfies the same `Agent` Protocol used by Clusters A-E. Downstream
(calibrator -> Action Engine -> realized_edge -> Scoreboard) is unchanged.
Model swap is a config change, not a code change (DESIGN.md #7).

The agent caches the forecast: each call to `forecast` invalidates only
if new emissions arrived since the last call. This reduces API spend in
test loops that read `forecast` multiple times per episode.
"""

from __future__ import annotations

from fingym.llm.contract import ForecastClient
from fingym.memory.promotion import Proposal
from fingym.memory.schema import MemoryArtifact
from fingym.memory.storage import render_for_system_prompt
from fingym.toys.synthetic_market import Emission, ForecastOverBuckets

DEFAULT_SIGNAL_CLASS_ID: str = "llm_unset"


class LlmAgent:
    """Frontier-model-driven agent satisfying the `Agent` Protocol.

    Reads emissions via `observe(emission)`. Calls the LLM (lazily, on
    first `.forecast` access after new observations) and caches the
    structured response. The model's self-applied `signal_class_id`
    becomes the agent's signal_class_id (the Forecast Ledger key).

    Cluster G: the agent accepts `promoted_skills: list[MemoryArtifact]`
    at construction. Promoted L3 skills are rendered into the system
    prompt at every LLM call (cached at the client level). The agent
    also captures the model's optional `memory_proposal` from each
    response and exposes it via the `latest_proposal` property — the
    promotion gate consumes that.
    """

    signal_class_id: str

    def __init__(
        self,
        client: ForecastClient,
        signal_class_id: str = DEFAULT_SIGNAL_CLASS_ID,
        name: str = "LlmAgent",
        promoted_skills: list[MemoryArtifact] | None = None,
    ) -> None:
        self.client = client
        self.name = name
        self.signal_class_id = signal_class_id
        self._emissions: list[Emission] = []
        self._cached_forecast: ForecastOverBuckets | None = None
        self._cached_thesis: str = ""
        self._latest_proposal: Proposal | None = None
        self._promoted_skills: list[MemoryArtifact] = list(promoted_skills or [])
        self._promoted_skills_text: str = render_for_system_prompt(self._promoted_skills)

    def observe(self, emission: Emission) -> None:
        """Append an emission to the agent's stream. Invalidates the cached
        forecast — the next `.forecast` access will re-call the LLM."""
        self._emissions.append(emission)
        self._cached_forecast = None

    @property
    def forecast(self) -> ForecastOverBuckets:
        """Return the agent's current forecast.

        Lazy: calls the LLM only if new emissions arrived since the last
        access. The LLM's self-applied `signal_class_id` overwrites the
        agent's signal_class_id (so the Forecast Ledger keys match the
        model's own categorization). Any optional `memory_proposal` from
        this call is captured for the promotion gate.
        """
        if self._cached_forecast is None:
            response = self.client.request_forecast(
                self._emissions,
                promoted_skills_text=self._promoted_skills_text,
            )
            self._cached_forecast = response.distribution
            self.signal_class_id = response.signal_class_id
            self._cached_thesis = response.thesis_category
            self._latest_proposal = response.memory_proposal
        return self._cached_forecast

    @property
    def thesis_category(self) -> str:
        """The model's prose thesis from the latest forecast.

        Empty string before the first `forecast` access. Useful for audit
        and for the memory-proposal flow.
        """
        return self._cached_thesis

    @property
    def latest_proposal(self) -> Proposal | None:
        """The memory_proposal from the latest forecast call, if the model
        emitted one. None on calls where the model didn't propose.

        Consumed by the promotion gate (`evaluate_proposal`) — never by
        the verifier directly.
        """
        return self._latest_proposal

    @property
    def promoted_skills(self) -> list[MemoryArtifact]:
        """The L3 promoted skills this agent was constructed with.

        Read-only snapshot — the agent does not modify L3 in-flight.
        Skill promotion happens out-of-band via the promotion gate
        (`evaluate_proposal`); next agent construction picks up the
        updated L3.
        """
        return list(self._promoted_skills)


__all__ = ["DEFAULT_SIGNAL_CLASS_ID", "LlmAgent"]
