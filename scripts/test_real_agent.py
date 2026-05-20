"""Smoke-test the RealLlmAgent on AAPL at a recent decision date."""

import os
from datetime import date
from pathlib import Path

import psycopg

from fingym.agents.real_agent import (
    RealLlmAgent,
    format_evidence_as_prose,
    load_evidence,
)
from fingym.llm.anthropic import AnthropicClient


def _load_env_file(path: Path) -> None:
    """Manually parse .env. uv's env-file parser silently truncates values
    containing certain dash patterns in modern Anthropic-style keys."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        if key and value and key not in os.environ:
            os.environ[key] = value
        elif key and value:
            # Override if shell-loaded value is empty (uv parser stripped it)
            if not os.environ.get(key):
                os.environ[key] = value


_load_env_file(Path(__file__).resolve().parent.parent / ".env")

ticker = "AAPL"
decision_date = date(2025, 6, 1)

print("ANTHROPIC_API_KEY set:", bool(os.environ.get("ANTHROPIC_API_KEY")))
print("MASSIVE_API_KEY set:", bool(os.environ.get("MASSIVE_API_KEY")))
print("DATABASE_URL set:", bool(os.environ.get("DATABASE_URL")))

client = AnthropicClient(temperature=0.0)
agent = RealLlmAgent(client=client, horizon_days=30)

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    evidence = load_evidence(conn, ticker, decision_date)
    prose = format_evidence_as_prose(evidence, horizon_days=30)
    print("=" * 80)
    print(" EVIDENCE PROSE (first 1500 chars):")
    print("=" * 80)
    print(prose[:1500])
    print(f"\n  ... (full prose is {len(prose)} chars)")

    print("\n" + "=" * 80)
    print(" CALLING LLM...")
    print("=" * 80)
    contract = agent.forecast_for(conn, ticker, decision_date)

    print(f"\n  contract_id:       {contract.contract_id}")
    print(f"  agent_id:          {contract.agent_id}")
    print(f"  model_id:          {contract.model_id}")
    print(f"  decision_time:     {contract.decision_time}")
    print(f"  signal_class_id:   {contract.signal_class_id}")
    print(f"  thesis_category:   {contract.thesis_category}")
    print(f"  horizon:           {contract.horizon}")
    print(f"  evidence_ids:      {len(contract.evidence_ids)} refs")
    print(f"  data_sources:      {contract.data_sources_used}")
    print(f"  recommended:       {contract.recommended_action.action_type}", end="")
    if contract.recommended_action.action_type == "trade":
        print(
            f"  {contract.recommended_action.expression_type} "
            f"{contract.recommended_action.direction}"
        )
    else:
        print(f"  (reason: {contract.recommended_action.reason})")
    print(f"  falsifiers:        {len(contract.falsifiers)}")

    print("\n  Forecast distribution:")
    for bucket, prob in contract.forecast_distribution.probabilities.items():
        bar = "█" * int(prob * 40)
        print(f"    {bucket:<20} {prob:>6.3f} {bar}")
