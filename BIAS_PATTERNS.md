# Bias-Smuggling Patterns

Specific failure modes that occurred during the design of FinInferenceGym. Most were proposed by Claude (sometimes seductively framed) and caught by Michael's audit. They are not theoretical — they are observed. The mechanism layer ([mechanisms/](mechanisms/)) catches some structurally; Michael's audit catches the rest. Claude's job is to challenge them aggressively before they reach either filter.

When you recognize a pattern below in a current proposal, **name it and refuse**. Do not re-litigate without new evidence.

---

## 1. Thematic prior disguised as scope

**Failure mode**: A thematic view ("AI dispersion will be huge"; "tech is broken"; "rates regime change is imminent") gets baked into universe selection, hypothesis space, or scoring weights. Themes are *outputs* of the system. Encoding them as architecture means the system cannot falsify them.

**Example that occurred**: Claude proposed a "deliberately barbelled universe across AI beneficiaries and AI-disrupted incumbents" based on Michael's stated high conviction in AI dispersion. Caught by Michael's audit.

**Principle violated**: DESIGN.md Operational Constraints — universe by operational/structural criteria only.

**Standing response**: If the thesis is true, the system will discover it from data. Encoding it removes the ability to verify.

---

## 2. Personal preference disguised as scope

**Failure mode**: A personal trading style ("I prefer concentrated positions"; "I hold for years"; "I only buy equity, not options") gets baked into the production architecture rather than the capital-deployment layer.

**Example that occurred**: BUILD.md initially scoped the operational universe to ~30–50 names and implied long-horizon equity-direction only. Caught by Michael's self-audit.

**Principle violated**: DESIGN.md #10 (Michael is the auditor only) and Operational Constraints (broad analytical universe, multi-horizon, full equity complex).

**Standing response**: Personal preference applies to capital deployment, not to what the system analyzes. Production universe is broad. Multi-horizon (1m/3m/6m/1y) scoring is parallel. Action space is the full equity complex.

---

## 3. Prestigious framework proposed because it's prestigious

**Failure mode**: AlphaEvolve, Continual Harness, Garry Tan committee, David Silver-style RL get proposed as primary mechanisms because they sound impressive, without checking whether the actual bottleneck is what they solve.

**Examples that occurred**: All four were evaluated and rejected. See DECISIONS.md for each.

**Standing response**: The bottleneck in finance is **evaluator quality, calibration discipline, and point-in-time integrity** — not search-mechanism sophistication. Imported frameworks that don't address the actual bottleneck produce confident garbage. The population-plus-promotion architecture *instantiates* the AlphaEvolve / Continual Harness pattern; it doesn't import them.

---

## 4. Human-in-the-loop as "diagnostic"

**Failure mode**: Using Michael's discretionary calls as a comparison anchor — framed as "just a diagnostic, we won't train on it" — embeds his bias into the system's loss function.

**Example that occurred**: Claude proposed a 4-quadrant matrix (agreement / disagreement / over- / under-confidence relative to Michael) as a calibration check. Caught by Michael's audit.

**Principle violated**: DESIGN.md #10.

**Standing response**: Michael is the auditor only. The system is graded by time-revealed labels. The 4-quadrant matrix is forbidden. Enforced by `mechanisms/lints/no_discretionary_references.py`.

---

## 5. Strong prior disguised as physics

**Failure mode**: A widely-used finance model (DCF, fundamental valuation, factor models, "obvious" macro relationships) gets treated as architectural invariant rather than as a testable hypothesis that often holds and frequently fails.

**Example that occurred**: Michael initially proposed "DCF is law, like physics." Rejected after deliberation.

**Standing response**: Real physics: Bayes math, Kelly criterion, time value, compound asymmetry, no-arbitrage, conservation of probability. Everything else — DCF included — is a strong prior that the system uses where it applies and discovers when it fails.

---

## 6. Single-model lock-in

**Failure mode**: Designing memory, hypothesis registry, evaluator, or promotion gate around the quirks of one model. Fine-tuning the base model on finance data as the *main* learning mechanism (rather than a year-2 distillation path).

**Example that occurred**: Initial framing positioned fine-tuning a base model on finance data as the main learning mechanism. Rejected.

**Principle violated**: DESIGN.md #7.

**Standing response**: Memory, registry, evaluator, gate are all model-agnostic. Models are swappable engines. Enforced by `mechanisms/lints/no_hardcoded_models.py`.

---

## 7. "Just for now" or "we can fix it later"

**Failure mode**: Deferring a known correctness issue with a vague promise to fix later. Almost always becomes permanent slippage.

**Standing response**: Either fix it now, or document the deferral explicitly in DECISIONS.md with a re-evaluation trigger (specific event or date that forces revisiting).

---

## 8. Narrowing the model interface to "help" it

**Failure mode**: Pre-extracting features, summarizing transcripts, templating reasoning, restricting the hypothesis ontology — all in the name of "helping the model focus." This bottlenecks the model's native intelligence.

**Example that occurred**: Initial design treated the LLM as a narrow tool (classify tone 1-5, extract a feature, etc.). Rejected after Michael identified it would prevent riding the exponent of model improvements.

**Principle violated**: DESIGN.md #5/#6 — cognition stays in the model; constraints migrate to verification.

**Standing response**: The model sees raw evidence and reasons natively. Constraints live on the verification side. Verify hard; let the model reason freely.

---

## 9. Buffet answers

**Failure mode**: Listing options ("we could do A, or B, or C") when a decision is required. Avoiding commitment to avoid being wrong.

**Standing response**: When Michael asks for an opinion or a decision, give one. Defend it. Buffet answers are explicitly recognized as failure mode — commit, surface real disagreements forcefully once, accept overrules.

---

## 10. Scope expansion without reason

**Failure mode**: "And we should also..." adds without justification. Each new addition needs a principle violation that warrants it or evidence that demands it.

**Standing response**: Default is no. Each scope addition requires either (a) a clear DESIGN.md principle being violated by current scope, or (b) evidence from prior phases demonstrating the addition is required. Without one of these, the addition is rejected.

---

## 11. Narrative as evidence

**Failure mode**: Treating the model's prose chain-of-thought as if it were the audit artifact, rather than the structured trajectory. Reading a beautiful rationale and concluding the inference is good — without checking the calibration score. Promoting a memory item because the proposing model wrote a compelling justification, even if the held-out replay was ambiguous.

**Example status**: Anticipated. Will surface as soon as we read model outputs at scale (Phase 2 onward). Logged here pre-emptively because the failure mode is structurally guaranteed: LLMs produce eloquent prose by default, and humans (Michael included) are wired to update on eloquence. The mechanism layer cannot catch this; only the discipline of "score is the audit object" catches it.

**Principle violated**: DESIGN.md Layer 5 — the audit object of record is the structured trajectory `(evidence_t → belief_t → action_t → label_{t+k} → score_{t+k})`.

**Standing response**: The trajectory is the audit object. Prose rationales are a **secondary inspection surface** — useful for catching specific failure modes (bias smuggling, narrative drift, references to Michael's discretion), but never a substitute for the score. A model producing eloquent rationales with poor calibration scores low. A model producing sparse rationales with excellent calibration scores high. Beautiful narrative ≠ inference quality. When a promotion proposal comes in with a compelling rationale, the response is "show me the held-out calibration delta," not "that sounds right."

---

## Disposition when these patterns appear

1. **Recognize the pattern.** Look it up in this file or DECISIONS.md.
2. **Name it.** "This is pattern N from BIAS_PATTERNS.md — thematic prior disguised as scope."
3. **Refuse without re-litigating.** State the pattern, state the rejection, do not consume Michael's bandwidth re-evaluating settled questions.
4. **Surface only if new evidence has emerged** that materially changes the rejection rationale.

Adding new patterns to this file requires either a documented Michael decision or a clear DESIGN.md principle violation. The file does not grow with speculative concerns; it grows with observed failures.
