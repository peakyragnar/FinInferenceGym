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
from fingym.data.queries.contracts import (
    count_contracts,
    list_recent_contracts,
    load_contract,
    save_contract,
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

    # ---- Step 3: persist to trajectory store, then round-trip verify ----
    print("\n" + "=" * 80)
    print(" PERSISTENCE — write to contracts table + round-trip via pydantic")
    print("=" * 80)
    before = count_contracts(conn)
    print(f"  contracts in DB before save: {before}")

    save_contract(conn, contract, ticker)
    conn.commit()

    after = count_contracts(conn)
    print(f"  contracts in DB after save:  {after}")

    loaded = load_contract(conn, contract.contract_id)
    if loaded is None:
        print("  ✗ FAILED: load_contract returned None")
    else:
        print("  ✓ load_contract returned a Contract")
        # Verify a few key fields round-tripped
        ok_id = loaded.contract_id == contract.contract_id
        ok_sci = loaded.signal_class_id == contract.signal_class_id
        ok_dist = (
            loaded.forecast_distribution.probabilities
            == contract.forecast_distribution.probabilities
        )
        ok_action = (
            type(loaded.recommended_action).__name__ == type(contract.recommended_action).__name__
        )
        ok_evidence = len(loaded.evidence_ids) == len(contract.evidence_ids)
        print(f"    contract_id round-trip:        {'✓' if ok_id else '✗'}")
        print(f"    signal_class_id round-trip:    {'✓' if ok_sci else '✗'}")
        print(f"    forecast_distribution match:   {'✓' if ok_dist else '✗'}")
        print(f"    recommended_action type match: {'✓' if ok_action else '✗'}")
        print(f"    evidence_ids count match:      {'✓' if ok_evidence else '✗'}")

    print("\n  Recent contracts (denormalized fields):")
    for r in list_recent_contracts(conn, limit=5):
        print(
            f"    {r['decision_time'].date()}  {r['ticker']:<5}  "
            f"{r['agent_id']:<14}  {r['signal_class_id']:<36}  "
            f"{r['recommended_action_type']:<9}  {r['recommended_expression'] or '-':<14}"
        )
