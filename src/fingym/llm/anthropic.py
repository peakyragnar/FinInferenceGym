"""Anthropic implementation of ForecastClient (PYRAMID Stone 30).

Wraps the `anthropic` SDK behind the `ForecastClient` Protocol. The ONLY
file in the codebase that imports `anthropic`. Pre-commit hook
`no-direct-llm-sdk-imports` enforces this structurally.

Design choices:

1. **Tool-call structured output.** The model is REQUIRED to call the
   `submit_forecast` tool. Free-form text parsing is impossible by
   construction; schema violations raise at the SDK boundary.

2. **Prompt caching.** The system prompt is marked
   `cache_control={"type": "ephemeral"}` so subsequent calls in a test
   session hit the cache. Saves cost on repeated runs.

3. **Toy emissions wrapped as natural language.** The model gets
   "On day 3, the company reported a STRONG fundamental signal" rather
   than `["strong", "weak", ...]`. Lets the model engage with its
   own priors. The toy structure is unchanged; only the prompt-side
   wrapping differs.

4. **Generic-analyst system prompt.** Does NOT tell the model the toy's
   likelihood table — that would be cheating (we are testing the
   verifier under a real-model cognitive layer, not the LLM doing
   optimal Bayesian inference). The model brings its priors; the
   verifier scores what comes back.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import anthropic
from anthropic.types import (
    MessageParam,
    TextBlockParam,
    ToolChoiceToolParam,
    ToolParam,
)

from fingym.llm.contract import ForecastClient, ForecastResponse
from fingym.toys.synthetic_market import RETURN_BUCKETS, Emission, ReturnBucket

DEFAULT_MODEL: str = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """You are a financial analyst forecasting an equity's
realized log return at a fixed horizon. You will be shown an ordered
stream of fundamental signals about a company. Each signal is one of:

  - STRONG (positive fundamental development; e.g., strong earnings,
    positive guidance, favorable competitive shift)
  - MIXED (neutral / ambiguous fundamental development)
  - WEAK (negative fundamental development; e.g., earnings miss,
    guidance cut, adverse competitive shift)

Read the full signal stream. Form your view of the company's likely
realized log return at horizon. Then call the `submit_forecast` tool
with:

  - `distribution`: your probability over the five return buckets:
        below_minus_5     (return below -5%)
        minus_5_to_0      (return between -5% and 0%)
        zero_to_plus_5    (return between 0% and +5%)
        plus_5_to_plus_10 (return between +5% and +10%)
        above_plus_10     (return above +10%)
    Values must sum to exactly 1.
  - `signal_class_id`: a short slug naming THIS KIND of forecast (your
    own categorization). The verifier uses this to track empirical
    reliability of forecasts under this tag over time. Examples:
    "fundamental_uniform_bullish", "earnings_beat_followthrough",
    "mixed_signal_stable". Invent and evolve these tags as you see fit.
  - `thesis_category`: a short prose label (1-2 sentences) summarizing
    your view. Free-form; for audit only.

You must call `submit_forecast` exactly once. Do not produce any other
output."""

_SUBMIT_FORECAST_TOOL: ToolParam = {
    "name": "submit_forecast",
    "description": (
        "Submit your structured forecast over the five realized-log-return "
        "buckets, your self-applied signal_class_id, and a short thesis_category."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "distribution": {
                "type": "object",
                "description": "Probability per return bucket; values sum to 1.",
                "properties": {bucket: {"type": "number"} for bucket in RETURN_BUCKETS},
                "required": list(RETURN_BUCKETS),
            },
            "signal_class_id": {
                "type": "string",
                "description": "Your own short tag for this kind of forecast.",
            },
            "thesis_category": {
                "type": "string",
                "description": "Short prose summary of your view.",
            },
        },
        "required": ["distribution", "signal_class_id", "thesis_category"],
    },
}

_EMISSION_TO_NATURAL: dict[Emission, str] = {
    "strong": "STRONG fundamental signal",
    "mixed": "MIXED fundamental signal",
    "weak": "WEAK fundamental signal",
}


def _wrap_emissions_as_prose(emissions: list[Emission]) -> str:
    if not emissions:
        return "(no signals observed yet)"
    lines = [f"  Day {i + 1}: {_EMISSION_TO_NATURAL[e]}" for i, e in enumerate(emissions)]
    return "Signal stream observed so far:\n" + "\n".join(lines)


@dataclass
class AnthropicClient(ForecastClient):
    """Concrete Anthropic implementation of ForecastClient.

    Reads `ANTHROPIC_API_KEY` from the environment by default (or accepts
    an explicit `api_key`). Calls the chosen model with tool-call
    structured output. Returns a typed `ForecastResponse`.
    """

    model: str = DEFAULT_MODEL
    api_key: str | None = None
    max_tokens: int = 1024
    temperature: float = 0.0
    _client: anthropic.Anthropic | None = None

    def _client_or_init(self) -> anthropic.Anthropic:
        if self._client is None:
            key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY not set; provide api_key or export the env var."
                )
            self._client = anthropic.Anthropic(api_key=key)
        return self._client

    def request_forecast(self, emissions: list[Emission]) -> ForecastResponse:
        """Call the model with the emission stream; return structured forecast.

        Uses tool calling to force structured output. Validates that the
        distribution sums to ~1 (within float tolerance) and renormalizes
        if the model's output is slightly off (e.g., 0.9999 due to rounding).
        Raises ValueError if the model failed to call the tool, or returned
        a degenerate distribution (sum <= 0).
        """
        client = self._client_or_init()
        user_message = _wrap_emissions_as_prose(emissions)

        system_blocks: list[TextBlockParam] = [
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        tool_choice: ToolChoiceToolParam = {
            "type": "tool",
            "name": "submit_forecast",
        }
        messages: list[MessageParam] = [{"role": "user", "content": user_message}]

        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_blocks,
            tools=[_SUBMIT_FORECAST_TOOL],
            tool_choice=tool_choice,
            messages=messages,
        )

        tool_use = next(
            (block for block in response.content if block.type == "tool_use"),
            None,
        )
        if tool_use is None:
            raise ValueError(
                f"Model did not call submit_forecast tool. Response content: {response.content!r}"
            )

        # Anthropic SDK returns tool input as a dict (already parsed).
        raw_input = tool_use.input
        if not isinstance(raw_input, dict):
            raise ValueError(f"Tool input is not a dict: {raw_input!r}")

        raw_distribution = raw_input.get("distribution")
        if not isinstance(raw_distribution, dict):
            raise ValueError(f"Missing or malformed distribution: {raw_distribution!r}")

        distribution: dict[ReturnBucket, float] = {}
        for bucket in RETURN_BUCKETS:
            value = raw_distribution.get(bucket)
            if not isinstance(value, int | float):
                raise ValueError(f"Bucket {bucket!r} missing or non-numeric: {value!r}")
            distribution[bucket] = float(value)

        total = sum(distribution.values())
        if total <= 0:
            raise ValueError(
                f"Forecast distribution has non-positive total {total}; cannot renormalize."
            )
        # Renormalize to handle small rounding errors from the model.
        distribution = {b: v / total for b, v in distribution.items()}

        signal_class_id = str(raw_input.get("signal_class_id", "")).strip()
        if not signal_class_id:
            raise ValueError("signal_class_id missing or empty.")
        thesis_category = str(raw_input.get("thesis_category", ""))

        return ForecastResponse(
            distribution=distribution,
            signal_class_id=signal_class_id,
            thesis_category=thesis_category,
        )


__all__ = ["DEFAULT_MODEL", "AnthropicClient"]
