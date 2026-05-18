"""Typed Protocol for the model client (PYRAMID Stone 30).

`ForecastClient` is the seam between agent code and any specific LLM
provider. Anywhere outside `src/fingym/llm/`, code depends on this
Protocol — never on `anthropic.Anthropic`, `openai.OpenAI`, etc. directly.
Pre-commit hook `no-direct-llm-sdk-imports` enforces this structurally.

`ForecastResponse` is the structured output: the model fills the same
five-bucket forecast space (Stone 7b's `RETURN_BUCKETS`) and self-tags
the forecast with a `signal_class_id` of its own choosing (Stone 11b's
per-signal-class-reliability key).

Model swap (per DESIGN.md #7) is a config change. A new provider goes
in `src/fingym/llm/<provider>.py`, satisfies `ForecastClient`, and the
agent code does not change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fingym.toys.synthetic_market import Emission, ForecastOverBuckets


@dataclass(frozen=True)
class ForecastResponse:
    """Structured output from a model client.

    `distribution` is the agent's forecast over the five return buckets;
    its values sum to 1 (caller validates).

    `signal_class_id` is the model's own categorization of *this kind*
    of forecast — the empirical reliability key the Forecast Ledger
    uses. The model invents and evolves these tags; they are searchable,
    not a fixed ontology.

    `thesis_category` is a short prose label the model attaches to the
    forecast (for audit / debugging / future memory-proposal flow). Free-
    form string; treated as opaque by the verifier.
    """

    distribution: ForecastOverBuckets
    signal_class_id: str
    thesis_category: str = ""


class ForecastClient(Protocol):
    """The model-interface contract.

    Concrete implementations live in `src/fingym/llm/<provider>.py` and
    are constructed by the agent at startup. The agent reads the response
    and consumes only `distribution` (for the forecast) and
    `signal_class_id` (for the Ledger key).
    """

    def request_forecast(self, emissions: list[Emission]) -> ForecastResponse:
        """Given an ordered stream of emissions, return a structured forecast.

        The Protocol does NOT constrain whether the provider uses tool
        calls / response format / structured outputs / function calling
        — that is an implementation detail of each provider's wrapper.
        What is guaranteed: the returned `ForecastResponse` has a
        well-formed `distribution` (5 buckets, values sum to 1) and a
        non-empty `signal_class_id`.

        Implementations may raise on provider errors (network, auth,
        rate limit, schema-violation). The agent / caller decides how
        to handle.
        """
        ...


__all__ = ["ForecastClient", "ForecastResponse"]
