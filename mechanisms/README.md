# Mechanisms

The enforcement layer. Per the harness-engineering principle:

> **Enforce quality with mechanisms, not prompts.**

Documented prose fails silently as it goes stale. Failed builds, failed type checks, and broken pointers fail loudly. This directory contains everything that turns DESIGN.md principles from prose into executable rules.

## Structure

```
mechanisms/
├── README.md
├── lints/                                   # custom pre-commit lints
│   ├── no_discretionary_references.py      # DESIGN.md #10
│   ├── no_hardcoded_models.py              # DESIGN.md #7
│   ├── validate_schemas.py
│   ├── validate_memory_artifacts.py
│   ├── check_alembic_migration.py
│   └── progress_md_warn.py
└── hooks/                                   # Claude Code hooks
    ├── post_write_format.sh
    ├── post_write_mypy.sh
    ├── pre_write_design_protected.sh
    ├── pre_write_mechanisms.sh
    ├── pre_bash_destructive.sh
    └── post_tool_progress_nudge.sh
```

## What each mechanism enforces

### Pre-commit lints

| Lint | Enforces |
|---|---|
| `no_discretionary_references.py` | DESIGN.md #10 — Michael is the auditor only. No `michael`/`discretionary`/`my_view` references in production code. |
| `no_hardcoded_models.py` | DESIGN.md #7 — Intelligence in architecture. No direct `anthropic`/`openai`/`google` imports outside `src/fingym/llm/`. |
| `validate_schemas.py` | All pydantic models in `src/fingym/` validate against fixture files. |
| `validate_memory_artifacts.py` | YAML files in `memory_registry/` validate against the memory artifact schema. |
| `check_alembic_migration.py` | If `src/fingym/data/schema.py` changed in a commit, a matching alembic migration must also be present. |
| `progress_md_warn.py` | Non-blocking warning: PROGRESS.md unchanged when phase-deliverable files changed. |

Other pre-commit hooks (from third-party repos, configured in `.pre-commit-config.yaml`):
- `mypy --strict` — cognition/verification boundary at the type level (DESIGN.md #5)
- `ruff` — lint + format
- `detect-secrets` — no API keys / connection strings in commits
- `check-added-large-files` — no accidental trajectory commits
- `import-linter` — architectural import boundaries

### Claude Code hooks

| Hook | Event | Action |
|---|---|---|
| `pre_write_design_protected.sh` | PreToolUse: Edit/Write | Block writes to DESIGN.md, DECISIONS.md, AGENTS.md without explicit user confirmation. |
| `pre_write_mechanisms.sh` | PreToolUse: Edit/Write | Block writes to `mechanisms/` itself without explicit user confirmation. Prevents Claude from quietly relaxing its own enforcement. |
| `post_write_format.sh` | PostToolUse: Edit/Write | Auto-run `ruff format` on `.py` files just written. |
| `post_write_mypy.sh` | PostToolUse: Edit/Write | Auto-run `mypy` on changed `.py` files; surface errors immediately. |
| `pre_bash_destructive.sh` | PreToolUse: Bash | Pattern-match destructive commands (rm -rf, DROP TABLE, force-push, git reset --hard). Surface for confirmation. |
| `post_tool_progress_nudge.sh` | PostToolUse | If a phase-deliverable file was touched and PROGRESS.md was not, print a reminder. |

### Architectural import boundaries (import-linter)

Configured in `importlinter.toml`. Allowed direction of imports:

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

This makes the cognition/verification boundary structural: by construction, `data/` cannot pre-engineer features that the model would consume, because it cannot import from layers that define features.

## Adding new mechanisms

A new mechanism enters this directory only when:

1. An existing rule could not be enforced via code (it was prose).
2. The rule has been violated or is at risk of violation.
3. Michael or Claude has explicitly proposed the mechanism in a turn that names it.

## Removing or weakening mechanisms

Mechanisms are protected against quiet relaxation. Two layers of defense:

1. The `pre_write_mechanisms.sh` Claude hook requires explicit confirmation for any write inside `mechanisms/`.
2. Any removal or relaxation must be accompanied by a DECISIONS.md entry explaining why.

If a mechanism becomes obsolete (the rule it enforced is no longer needed), document the obsolescence in DECISIONS.md before removing the mechanism.

## Mechanisms catch DESIGN.md drift; they do not replace it

The mechanisms here enforce specific, structurally detectable violations of DESIGN.md. They do not replace the audit principle — many forms of bias-import (e.g., thematic priors disguised as scope) are not detectable by any lint. Michael's audit role (Layer 5) is what catches the residual.
