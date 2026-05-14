# Mechanisms

The enforcement layer. Per the harness-engineering principle:

> **Enforce quality with mechanisms, not prompts.**

Prose fails silently as it goes stale. Failed builds, failed type checks, and broken pointers fail loudly. This directory holds everything that turns DESIGN.md principles from prose into executable rules.

---

## Implemented now

Working today. Wired into `.pre-commit-config.yaml` and `.claude/settings.json`.

### Pre-commit lints (custom)

| File | Enforces |
|---|---|
| `lints/no_discretionary_references.py` | DESIGN.md #10 — no `michael` / `discretionary` / `my_view` references in production code. |
| `lints/no_hardcoded_models.py` | DESIGN.md #7 — no direct `anthropic` / `openai` / `google` imports outside `src/fingym/llm/`. |

### Pre-commit (third-party)

Configured in `.pre-commit-config.yaml`:

- `pre-commit-hooks` — check-yaml, check-json, check-toml, check-added-large-files, check-merge-conflict, end-of-file-fixer, trailing-whitespace, detect-private-key
- `detect-secrets` — scan for API keys, connection strings
- `ruff` — lint + format

### Claude Code hooks

| File | Event | Action |
|---|---|---|
| `hooks/post_write_format.sh` | PostToolUse: Edit / Write | Auto-run `ruff format` on `.py` files just written. |

Wired in `.claude/settings.json`.

---

## Queued for Phase 0

Described in [TECHNICAL.md](../TECHNICAL.md) and [.pre-commit-config.yaml](../.pre-commit-config.yaml). They require code (pydantic models, memory schema, src/fingym/, alembic) that gets built in Phase 0. Activate each by:

1. Creating the referenced script in `mechanisms/lints/` or `mechanisms/hooks/`.
2. Uncommenting the entry in `.pre-commit-config.yaml` or `.claude/settings.json`.
3. Verifying it passes on a clean repo.

### Pre-commit lints queued

| Planned file | Will enforce |
|---|---|
| `lints/validate_schemas.py` | All pydantic models in `src/fingym/` validate against fixture files. |
| `lints/validate_memory_artifacts.py` | YAML files in `memory_registry/` validate against the memory artifact schema. |
| `lints/check_alembic_migration.py` | Schema changes in `src/fingym/data/schema.py` require a matching alembic migration in the same commit. |
| `lints/progress_md_warn.py` | Non-blocking: PROGRESS.md unchanged when phase-deliverable files changed. |

### Third-party hooks queued

- `mypy --strict` — turn on once `pyproject.toml` and `src/fingym/` exist.
- `import-linter` — turn on once `src/fingym/` has packages and `importlinter.toml` defines boundaries.

### Claude Code hooks queued

| Planned file | Event | Action |
|---|---|---|
| `hooks/post_write_mypy.sh` | PostToolUse: Edit / Write | Auto-run `mypy` on changed `.py` files; surface errors immediately. |
| `hooks/pre_write_design_protected.sh` | PreToolUse: Edit / Write | Block writes to DESIGN.md, DECISIONS.md without explicit confirmation. |
| `hooks/pre_write_mechanisms.sh` | PreToolUse: Edit / Write | Block writes to `mechanisms/` itself without explicit confirmation. |
| `hooks/pre_bash_destructive.sh` | PreToolUse: Bash | Surface destructive commands (rm -rf, DROP TABLE, force-push) for confirmation. |
| `hooks/post_tool_progress_nudge.sh` | PostToolUse | Remind to update PROGRESS.md if phase deliverables changed. |

---

## Architectural import boundaries

Enforced by `import-linter` once it's enabled. Configuration will live in `importlinter.toml`.

```
data/      ←   evaluator/, beliefs/, agents/, cli/
evaluator/ ←   agents/, cli/
beliefs/   ←   agents/, cli/
memory/    ←   agents/, cli/
llm/       ←   agents/, cli/
```

Forbidden:
- `data/` → upper layers
- `evaluator/` → `agents/`, `beliefs/`, `llm/`, `memory/`
- `llm/` → anything outside its own package

This makes the cognition/verification boundary structural: `data/` cannot pre-engineer features that the model would consume, because it cannot import from layers that define features.

---

## Adding new mechanisms

A new mechanism enters this directory only when:

1. An existing rule could not be enforced via code (it was prose).
2. The rule has been violated or is at risk of violation.
3. Michael or Claude has explicitly proposed the mechanism in a turn that names it.

## Removing or weakening mechanisms

Mechanisms are protected against quiet relaxation. Two layers of defense:

1. The (queued) `pre_write_mechanisms.sh` Claude hook will require explicit confirmation for any write inside `mechanisms/`.
2. Any removal or relaxation must be accompanied by a DECISIONS.md entry explaining why.

If a mechanism becomes obsolete, document the obsolescence in DECISIONS.md before removing it.

---

## What mechanisms cover and don't cover

Mechanisms catch **structurally detectable** violations of DESIGN.md. Many forms of bias-import (e.g., thematic priors disguised as scope, prestigious frameworks proposed because prestigious) are not detectable by any lint. Michael's audit role (Layer 5) is what catches the residual. See [BIAS_PATTERNS.md](../BIAS_PATTERNS.md).
