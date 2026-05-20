"""Postgres read adapters for the data spine.

Each module here is a thin SQL layer that returns native Python objects
shaped for downstream consumers. Read-only by convention; writes go
through the ingest modules in `fingym.data.ingest`.

Submodules:
  - headline_observables: macro state lookup at a decision time
  - equity_returns: realized log returns per (ticker, horizon)
"""
