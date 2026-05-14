"""Command-line entry points.

Operational commands for ingesting data, running the evaluator on toys,
running historical replay, and running live operation.

Each entry point is a thin wrapper that wires up the underlying
packages (data/, evaluator/, beliefs/, agents/, llm/, memory/) into a
specific workflow.

This package may import from any other package in src/fingym/ —
nothing imports from it.
"""
