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
from fingym.toys.synthetic_market import Emission, ForecastOverBuckets

DEFAULT_SIGNAL_CLASS_ID: str = "llm_unset"


class LlmAgent:
    """Frontier-model-driven agent satisfying the `Agent` Protocol.

    Reads emissions via `observe(emission)`. Calls the LLM (lazily, on
    first `.forecast` access after new observations) and caches the
    structured response. The model's self-applied `signal_class_id`
    becomes the agent's signal_class_id (the Forecast Ledger key).
    """

    signal_class_id: str

    def __init__(
        self,
        client: ForecastClient,
        signal_class_id: str = DEFAULT_SIGNAL_CLASS_ID,
        name: str = "LlmAgent",
    ) -> None:
        self.client = client
        self.name = name
        self.signal_class_id = signal_class_id
        self._emissions: list[Emission] = []
        self._cached_forecast: ForecastOverBuckets | None = None
        self._cached_thesis: str = ""

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
        model's own categorization).
        """
        if self._cached_forecast is None:
            response = self.client.request_forecast(self._emissions)
            self._cached_forecast = response.distribution
            self.signal_class_id = response.signal_class_id
            self._cached_thesis = response.thesis_category
        return self._cached_forecast

    @property
    def thesis_category(self) -> str:
        """The model's prose thesis from the latest forecast.

        Empty string before the first `forecast` access. Useful for audit
        and for the future memory_update_proposal flow.
        """
        return self._cached_thesis


__all__ = ["DEFAULT_SIGNAL_CLASS_ID", "LlmAgent"]
