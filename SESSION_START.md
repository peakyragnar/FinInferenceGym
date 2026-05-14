# Session Start

When opening a new Claude Code session on this project, paste the message below as the first message. Do not modify it.

---

```
Project is FinInferenceGym. Before responding to anything else, read these files in full, in this order:

  1. DESIGN.md
  2. CLAUDE.md
  3. TECHNICAL.md
  4. BUILD.md
  5. PROGRESS.md
  6. DECISIONS.md
  7. BIAS_PATTERNS.md
  8. DEFINITIONS.md
  9. intuitions.md

(AGENTS.md is just a pointer to CLAUDE.md and can be skipped.)

PROGRESS.md is the source of truth for current phase and status. BUILD.md is the operational source for "what does this phase require." TECHNICAL.md is the engineering decisions (stack, database, mechanisms, deployment path). BIAS_PATTERNS.md is the named failure modes to challenge.

Then summarize back to me:

  - The 10 first-principles commitments from DESIGN.md (one line each).
  - The current build phase per PROGRESS.md, its exit criteria from BUILD.md, and the "Next Action" from PROGRESS.md.
  - The slippage watches for the current phase.
  - The three most relevant DECISIONS.md entries given the phase we're in.
  - The three most relevant BIAS_PATTERNS.md entries to watch for in the current phase.

Do not propose plans, expand scope, or produce design alternatives until you have done this and I have confirmed the summary is accurate.

If anything in the files is unclear or conflicts, ask before proceeding. Do not silently resolve conflicts.
```

---

## Why this protocol matters

A new Claude session starts with no memory of prior conversations. The architectural design and the rejected alternatives live only in the files. Without forcing the new session to read them in full and summarize them back, drift is highly likely — even with CLAUDE.md's standing rules. The summary-back step is the diagnostic: if Claude can't restate the 10 commitments and the current phase, it didn't read carefully enough, and you should not proceed until it has.

If a new Claude tries to start work without doing this, stop it and paste the protocol again.
