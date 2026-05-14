#!/usr/bin/env bash
# Claude Code PostToolUse hook: auto-format Python files after Edit/Write.
#
# Closes the feedback loop on formatting from "next commit" to "immediately
# after write," so the agent sees the formatted code as the source of truth.
#
# Wired via .claude/settings.json under hooks.PostToolUse, matched against
# Edit and Write tool calls.
#
# Reads tool-call JSON from stdin. If the tool was Edit or Write and the
# target was a .py file, runs `ruff format` on it. Silently exits otherwise.

set -euo pipefail

event_json="$(cat)"

tool_name="$(printf '%s' "$event_json" | jq -r '.tool_name // empty')"
file_path="$(printf '%s' "$event_json" | jq -r '.tool_input.file_path // empty')"

if [[ "$tool_name" != "Edit" && "$tool_name" != "Write" ]]; then
  exit 0
fi

if [[ -z "$file_path" || "$file_path" != *.py ]]; then
  exit 0
fi

if [[ ! -f "$file_path" ]]; then
  exit 0
fi

if command -v ruff >/dev/null 2>&1; then
  ruff format "$file_path" >/dev/null 2>&1 || true
fi

exit 0
