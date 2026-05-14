# FinInferenceGym

An AI-native financial inference gym. Evaluator-centered, model-pluggable, designed to absorb frontier AI improvements over time and generate calibrated, verifiable alpha in equity markets.

## Where to start

Read in this order:

1. **[DESIGN.md](DESIGN.md)** — architectural constitution; the 10 first-principles commitments.
2. **[CLAUDE.md](CLAUDE.md)** — primary AI behavior file.
3. **[TECHNICAL.md](TECHNICAL.md)** — engineering decisions (Python 3.12 / uv, Postgres on Neon, mechanism layer, deployment path).
4. **[BUILD.md](BUILD.md)** — 12-week execution plan.
5. **[PROGRESS.md](PROGRESS.md)** — current phase status and next action.

For starting a new session with Claude Code, paste the prompt from **[SESSION_START.md](SESSION_START.md)** as the first message.

## Other files

- **[DECISIONS.md](DECISIONS.md)** — alternatives proposed and rejected.
- **[BIAS_PATTERNS.md](BIAS_PATTERNS.md)** — named failure modes to challenge.
- **[DEFINITIONS.md](DEFINITIONS.md)** — glossary.
- **[intuitions.md](intuitions.md)** — running conceptual foundations.
- **[AGENTS.md](AGENTS.md)** — pointer to CLAUDE.md for non-Claude agents.
- **[mechanisms/README.md](mechanisms/README.md)** — enforcement layer.

## Repo layout

```
src/fingym/          # main package
  toys/              # toy worlds (coin, synthetic company)
  evaluator/         # scoreboard + scoring rules
  data/              # data spine (PIT, live, ingest)
  memory/            # versioned memory artifacts + promotion gate
  beliefs/           # belief recovery, market-implied DCF, edge
  agents/            # population of agents
  llm/               # model swap layer (anthropic/openai/google/openweights)
  cli/               # entry points

tests/
  unit/
  property/          # hypothesis-based math invariants
  integration/

mechanisms/          # enforcement layer (lints, hooks)
config/              # universe.yaml, vendors.yaml, agents/*.yaml
memory_registry/     # versioned skill/hypothesis YAML (in git)
migrations/          # alembic migrations (generated)
trajectory_store/    # append-only logs (gitignored)
data_cache/          # local data cache (gitignored)
toys/                # legacy toy location; coin.py migrates to src/fingym/toys/ in Phase 0
```

## License and ownership

Michael owns this project.
