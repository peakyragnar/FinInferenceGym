# Session Start

When opening a new Claude Code session on this project, paste the message below as the first message. Do not modify it.

---

```
Project is FinInferenceGym. Before responding to anything else, read these files in full, in this order:

  1. DESIGN.md
  2. CLAUDE.md
  3. BUILD.md
  4. PROGRESS.md
  5. DECISIONS.md
  6. AGENTS.md
  7. DEFINITIONS.md
  8. intuitions.md

PROGRESS.md is the source of truth for current phase and status — read it for "where are we." BUILD.md is the operational source for "what does this phase require." AGENTS.md provides curriculum framing; it does not override BUILD.md on execution.

Then summarize back to me:

  - The 10 first-principles commitments from DESIGN.md (one line each).
  - The current build phase per PROGRESS.md, its exit criteria from BUILD.md, and the "Next Action" from PROGRESS.md.
  - The slippage watches for the current phase.
  - The three most relevant DECISIONS.md entries given the phase we're in.

Do not propose plans, expand scope, or produce design alternatives until you have done this and I have confirmed the summary is accurate.

If anything in the files is unclear or conflicts, ask before proceeding. Do not silently resolve conflicts.
```

---

## Why this protocol matters

A new Claude session starts with no memory of prior conversations. The architectural design and the rejected alternatives live only in the files. Without forcing the new session to read them in full and summarize them back, drift is highly likely — even with CLAUDE.md's standing rules. The summary-back step is the diagnostic: if Claude can't restate the 10 commitments and the current phase, it didn't read carefully enough, and you should not proceed until it has.

If a new Claude tries to start work without doing this, stop it and paste the protocol again.
