"""Operator dashboard — the inspectability layer (DESIGN.md #10).

Read-only command-line surface that reports on the Phase 1 NEW data
spine in a form a human auditor can read:

  - Per-agent Scoreboard summary
  - Track C attribution (`incremental_AI_edge`)
  - Memory state (L3 promoted + L2 probationary)
  - Recent gate activity (from artifact audit_trails)

DESIGN.md #10 puts the auditor (Michael) on the hook for watching two
things: bias creeping in, and any layer losing inspectability. The
dashboard IS the inspectability mechanism — without it, the Phase 1 NEW
data lives in YAML files and in-memory test objects with no human-facing
surface. The CLI gives the auditor a way to actually do the job.

Architectural note: this module is consumed ONLY by the CLI entry point
(`python -m fingym.operator`). It depends downstream on everything it
inspects (Scoreboard, memory, baseline) but no other module imports
from it. Same model-agnostic, read-only contract memory has.

Usage:
    uv run python -m fingym.operator report

Optional flags:
    --scoreboard-path  default: data_cache/scoreboard.jsonl
    --l3-dir           default: memory_registry/promoted
    --l2-dir           default: memory_registry/probationary
"""
