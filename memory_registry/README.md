# Memory Registry

Versioned, model-readable artifacts: skills, hypotheses, observations, lessons.

Each artifact is a YAML file. Stored in git for audit history (diffs, blame, version control). Not stored in Postgres because git's audit story is stronger for human review of memory evolution.

## Schema

Validated by `mechanisms/lints/validate_memory_artifacts.py` (queued for Phase 0).

Required fields (per the schema in `src/fingym/memory/schema.py`, also queued for Phase 0):

```yaml
id: <unique slug>
type: skill | hypothesis | observation | lesson
description: <one-line summary>
status: probationary | promoted | core | retired
proposer:
  model: <model name when LLM proposed it; "human" if Michael proposed>
  date: <ISO 8601>
evidence_basis: <reference to specific trajectory IDs or episodes>
validation_history:
  - timestamp: <ISO 8601>
    gate: held_out | live_calibration | cross_model | survivorship | domain_of_validity
    result: pass | fail
    notes: <free text>
domain_of_validity:
  horizons: [1m, 3m, 6m, 1y]  # or subset
  expression_types: [equity_long, equity_short, option_call, ...]  # or subset
  sectors: [all]  # or specific list
  regimes: [all]  # or specific list
content: <the actual rule / hypothesis / observation, as model-readable text>
```

## How items enter and exit

- **Enter**: an agent (or Claude during design) proposes a candidate. The promotion gate (Phase 4) decides whether it persists.
- **Promotion path**: probationary → promoted → core. Each transition requires the gate criteria from BUILD.md Phase 4.
- **Exit**: retired status when the artifact is superseded or shown to no longer help. Retirement is recorded in `validation_history`, never deleted.

## What lives here vs. elsewhere

- **memory_registry/** (this directory): the artifacts themselves.
- **promotion_log table** (Postgres): the running log of every proposal with outcome. Both promoted and rejected.
- **trajectory_store**: the raw episodes that feed the gate.

## Phase 0 status

Empty. The schema and validator are Phase 0 deliverables. First real memory artifacts arrive in Phase 4 (LLM-as-proposer).
