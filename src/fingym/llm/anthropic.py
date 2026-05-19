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
    ToolChoiceAnyParam,
    ToolParam,
)

from fingym.llm.contract import ForecastClient, ForecastResponse
from fingym.memory.promotion import Proposal
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
realized log return at horizon. Then ALWAYS call the `submit_forecast`
tool with:

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

OPTIONALLY, if you've identified a generalizable insight worth
remembering (a pattern that should help future forecasts under the
same signal_class_id), ALSO call the `propose_memory_item` tool with:

  - `content`: the rule / heuristic / observation in 1-3 sentences
  - `signal_class_id`: which class of forecasts this applies to (often
    the same one you just submitted)
  - `horizons`: which horizon ticks the insight applies to (integers
    like [1] or [3, 6, 12])

The promotion gate decides whether to add proposals to the agent's
long-term memory. Most calls should NOT propose anything — propose only
when you genuinely see a generalizable pattern, not after every forecast."""

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


_PROPOSE_MEMORY_TOOL: ToolParam = {
    "name": "propose_memory_item",
    "description": (
        "OPTIONAL. Propose a memory item to be considered for promotion "
        "to the agent's long-term L3 memory. Use only when you have "
        "identified a generalizable insight worth remembering."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The rule / heuristic / observation in 1-3 sentences.",
            },
            "signal_class_id": {
                "type": "string",
                "description": "Which class of forecasts this insight applies to.",
            },
            "horizons": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Which horizon ticks the insight applies to, e.g., [1, 3, 6].",
            },
        },
        "required": ["content", "signal_class_id", "horizons"],
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

    def request_forecast(
        self,
        emissions: list[Emission],
        promoted_skills_text: str = "",
    ) -> ForecastResponse:
        """Call the model with the emission stream; return structured forecast.

        Uses tool calling to force structured output. The model MUST call
        `submit_forecast` (forced via tool_choice=any + system prompt
        instruction) and MAY also call `propose_memory_item`. Both tool
        calls are parsed; the proposal (if any) is returned in
        `ForecastResponse.memory_proposal`.

        `promoted_skills_text`, when non-empty, is appended to the system
        prompt as a separate (non-cached) block so the model sees the
        agent's promoted L3 skills at session start.

        Raises ValueError if the model failed to call submit_forecast,
        or returned a degenerate distribution (sum <= 0).
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
        if promoted_skills_text:
            system_blocks.append(
                {
                    "type": "text",
                    "text": promoted_skills_text,
                }
            )
        # tool_choice=any: model MUST call at least one tool, MAY call
        # multiple. System prompt instructs that submit_forecast is
        # always required; propose_memory_item is optional.
        tool_choice: ToolChoiceAnyParam = {"type": "any"}
        messages: list[MessageParam] = [{"role": "user", "content": user_message}]

        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_blocks,
            tools=[_SUBMIT_FORECAST_TOOL, _PROPOSE_MEMORY_TOOL],
            tool_choice=tool_choice,
            messages=messages,
        )

        # Collect all tool_use blocks; locate submit_forecast (required)
        # and propose_memory_item (optional).
        forecast_tool_use = None
        proposal_tool_use = None
        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "submit_forecast":
                forecast_tool_use = block
            elif block.name == "propose_memory_item":
                proposal_tool_use = block

        if forecast_tool_use is None:
            raise ValueError(
                f"Model did not call submit_forecast tool. Response content: {response.content!r}"
            )

        # --- parse submit_forecast --------------------------------------
        forecast_input = forecast_tool_use.input
        if not isinstance(forecast_input, dict):
            raise ValueError(f"submit_forecast input is not a dict: {forecast_input!r}")

        raw_distribution = forecast_input.get("distribution")
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

        signal_class_id = str(forecast_input.get("signal_class_id", "")).strip()
        if not signal_class_id:
            raise ValueError("signal_class_id missing or empty.")
        thesis_category = str(forecast_input.get("thesis_category", ""))

        # --- parse optional propose_memory_item -------------------------
        memory_proposal: Proposal | None = None
        if proposal_tool_use is not None:
            proposal_input = proposal_tool_use.input
            if isinstance(proposal_input, dict):
                content = str(proposal_input.get("content", "")).strip()
                proposal_sci = str(proposal_input.get("signal_class_id", "")).strip()
                raw_horizons = proposal_input.get("horizons", [])
                if content and proposal_sci and isinstance(raw_horizons, list) and raw_horizons:
                    horizons_tuple: tuple[int, ...] = tuple(
                        int(h) for h in raw_horizons if isinstance(h, int | float)
                    )
                    if horizons_tuple:
                        memory_proposal = Proposal(
                            content=content,
                            signal_class_id=proposal_sci,
                            horizons=horizons_tuple,
                        )

        return ForecastResponse(
            distribution=distribution,
            signal_class_id=signal_class_id,
            thesis_category=thesis_category,
            memory_proposal=memory_proposal,
        )


__all__ = ["DEFAULT_MODEL", "AnthropicClient"]
