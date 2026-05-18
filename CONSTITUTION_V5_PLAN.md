# Constitution v5 Revision Plan

> Tracker for the architectural revision from "belief over hidden state with P_market recovery" to "belief over realized returns with Forecast Ledger calibration and isolated Market-State Baseline."
>
> This file is the source of truth for the revision plan. Read at the start of every session that touches the v5 revision so we don't get lost. Update at the end of every session.

---

## Reference points

| Reference | What it is |
|---|---|
| **Pre-v5 stable tag** | `v0.1` — return point if v5 revision needs to be reverted. Tagged at commit 64df5a4 on 2026-05-18. Captures Phase 0 complete + Constitution v4 applied, before any v5 work. |
| **Architectural arc conversation** | Session on 2026-05-17/18 — the long deliberation that produced the v5 framing. |
| **Audit entry** | DECISIONS.md "Constitution tightening v5 (2026-05)" — to be written FIRST as part of the revision. |
| **Stable tag at v5 completion** | `v0.2` — will be created when revision is complete, mypy clean, tests green. |

---

## The architectural arc — one-paragraph summary

The original DESIGN.md commitment #2 ("belief over hidden state, with market belief P_market recovered from prices") was found to have three structural problems through iterative critique: (1) "hidden state" is our construct, not a property of equity markets; (2) recovering `P_market` from prices via inversion is model-dependent and brittle; (3) acting on the gap `P_AI − P_market` introduces a silent-failure mode where a biased recovery produces false no-edge signals. Successive refinements considered bucket-empirical baselines, then no-baseline-at-all, and finally landed on a framing where the AI Core forecasts realized returns directly, calibration is empirically maintained via a Forecast Ledger (per-signal-class reliability tracked over many forecasts), action is gated by calibrated expected utility (NOT by a market-belief gap), and a Market-State Baseline (Track C) using headline observable inputs runs in isolation as a diagnostic / control / attribution layer — never seen by the AI Core. The baseline shares its raw factor inputs with the AI (rates, vol, FX, commodities are observables available to both); only the baseline's processed forecast is hidden from the AI.

---

## What's removed from the old design (explicit list)

| Removed | Replaced by |
|---|---|
| `P_market(S)` as a load-bearing primitive | Forecast Ledger calibration of AI forecasts against realized returns |
| Belief delta `P_AI − P_market` on truth state | Calibrated expected utility action gate |
| Four-thing decomposition (`S_true`, `P_AI(S)`, `P_market(S)`, `Action(A)`) | Three things: realized return, AI forecast, action |
| Hidden state as a load-bearing object | Returns ARE the labels — no state-categorization labelling function |
| Stone 7a (four-thing vocabulary) | Stone 7b (atom of forecast) |
| Stone 11a (market-delta scoring) | Stones 11b/11c/11d (Forecast Ledger, calibration shrinkage, tradable edge) |
| Stone 31 in its Phase 1 NEW form (market-implied belief recovery in toy) | Stone 11e (Market-State Baseline in Phase 2 NEW, isolated control) |
| Two-believer toy (agent + market believers) | Single-believer toy where AI forecasts realized returns directly |
| "Beat the market belief" action threshold | "Calibrated expected utility clears margin of safety" action threshold |

---

## What survives intact

| Survived | Status |
|---|---|
| DESIGN.md commitments #1, #3, #4, #5, #6, #7, #8, #9, #10 | Intact |
| Stones 1–7 (atom of inference: belief, outcome, score, properness, Brier, log, Cromwell) | Intact |
| Stones 8–11 (calibration curves, scoreboard, multi-horizon, expression-type) | Intact |
| Stones 16–21 (adversarial agents, reliability diagrams, Contract Protocol, memory schema, property tests) | Intact (minor Contract field updates) |
| Memory architecture (L0/L1/L2/L3 pyramid, git-backed YAML, promotion gate four checks) | Intact (promotion-gate metrics updated) |
| Mechanism layer (lints, hooks, import-linter, mypy strict) | Intact |
| Python 3.12 / uv / pytest / Postgres on Neon | Intact |

---

## Plan checklist

### Phase A — Vocabulary and constitution (Session 1: DECISIONS.md; Session 2: rest as part of full cleanup pass)

- [x] **DECISIONS.md** — "Constitution tightening v5 (2026-05): belief over realized returns; Forecast Ledger; isolated Market-State Baseline" entry written (Session 1, 2026-05-18). Captures the architectural arc (three rounds of pushback), the six-component framing, what survives intact, what gets re-taught in PYRAMID, full files-touched plan, principle.
- [x] **DEFINITIONS.md** — Cleaned (Session 2). Pre-v5 entries removed (S_true-as-state-category, P_AI(S), P_market(S), Edge, Hidden state, Implied DCF, Market-implied belief). Per Michael's directive, new v5 vocabulary added incrementally during the teaching pass — not pre-loaded. Existing entries that survive v5 (Contract, NoEdgeContract, Belief, Emission, Evaluator, EV, Inference chain, Label, No-edge, Payoff structure, Price, Realized volatility, Reflexivity, Shape of the gym, Thesis vs timing, VoI, etc.) updated to v5 vocabulary where needed.
- [x] **DESIGN.md** — Rewritten (Session 2). Commitment #2 rewritten (forecast distribution over realized returns, calibrated empirically; Forecast Ledger; Tradable-Edge Action Engine with margin-of-safety gate; isolated Market-State Baseline with code-level isolation). Four-thing decomposition section replaced by "Three primitives + audit layer." Goal numbered list, Failure Modes table, Layers 0/1/2/3, Operational Constraints, Searchable vs Architectural, Three Arenas, Audit object of record — all updated.
- [x] **FORMULAS.md** — Cleaned (Session 2). Four-thing decomposition section and Market-delta scoring section removed. Scoreboard schema updated (forecast_distribution; signal_class_id; realized_return; verification-side fields). Stones 12, 13, 14 sections removed (per Michael's "deferred to teaching" directive for FORMULAS; v5 reformulation lands when those stones are re-taught). Stones 1, 6, 7, 8, 9, 10, 11 sections survive with minor v5 language updates.
- [x] **BIAS_PATTERNS.md** — Reviewed (Session 2). #11 (narrative as evidence) covers the "trusting AI stated confidence without empirical calibration" failure mode at the auditor-side level; the structural defense is the Forecast Ledger calibration shrinkage (a system property, not an audit pattern). No new entry added.
- [x] **CLAUDE.md** Goal paragraph — updated (Session 2). "Hidden-state inference + market-implied belief recovery" language replaced by "forecast distributions over realized returns + Forecast Ledger calibration + margin-of-safety gate + isolated Market-State Baseline."

### Phase B — Contracts and engineering (Session 2: full cleanup pass)

- [x] **CONTRACT.md** — Rewritten (Session 2). Cognition fields vs verification fields, `forecast_distribution`, `signal_class_id`, `thesis_category`, `data_sources_used`, `recommended_action`, `realized_return_plan` (replacing `LabelPlan`), verification fields `calibrated_forecast` / `calibrated_expected_return` / `calibrated_expected_utility` / `tradable_edge_score` / `kelly_fraction_applied` / `final_action`. Three-primitives + audit layer mapping. Validation rules rewritten for cognition vs verification sides.
- [x] **memory-design.md** — Updated (Session 2). L0 trajectory tables renamed to `forecasts`/`realized_returns`/etc.; Forecast Ledger view added; per-signal-class reliability addressed in promotion-gate metrics; first-principles audit table updated for commitment #2 v5; "headline_observables" table added; scale expectations updated.
- [x] **TECHNICAL.md** — Updated (Session 2). Six data types renamed (`forecasts`, `realized_returns`, etc.); Forecast Ledger materialized view added; new section "v5 component modules" with specs for `src/fingym/ledger/`, `src/fingym/action/`, `src/fingym/baseline/`; repo structure updated to add these directories and drop `beliefs/`; import-linter rules updated (forbidden: `agents/ → baseline/`, `agents/ → action/`, `agents/ → ledger/`, etc.; baseline isolation as load-bearing rule).

### Phase C — Build plan (Session 2: cluster sequence rewritten; PYRAMID stub-only until teaching)

- [x] **BUILD.md** — Phase 1 NEW rewritten as 9 clusters under v5 (Cluster I added: Market-State Baseline isolation in toy); Phase 2 NEW updated to add real-data Stone 11e (Baseline on real headline observables); Design-to-Build cross-reference table updated for v5; teaching/intuitions/domain-expertise sections rewritten; slippage watches updated (added "trusting AI stated confidence" and "agent reading Baseline's processed forecast" watches; added "Baseline observable creep" watch for Phase 2 NEW).
- [x] **PYRAMID.md** — Pre-v5 stones 7a, 11a, 31 deleted (from TOC and body). TOC entries added for new stones 7b, 11b, 11c, 11d, 11e with one-line descriptions; full distilled summaries pending the v5 teaching pass per the teach-then-distill cadence. Stones 12, 13, 14, 15 body content reduced to brief v5-aware notes pending re-teaching. Layer 2 closure paragraph updated. Current Position and Phase 1 NEW intro paragraphs updated for v5.
- [x] **PROGRESS.md** — Phase 1 NEW shown as paused for v5 cleanup; status updated to reflect cleanup-pass complete + teaching pass next. 9-cluster table under v5. Exit criteria updated (per-signal-class reliability, calibrated_expected_utility, tradable_edge_score, incremental_AI_edge columns; Baseline isolation enforced). Phase 2 NEW preview updated with real-data Stone 11e. Completed Phases Phase 0 section updated to note v5 cleanup effects (removed Stone 11a, two-believer toy, belief_delta tests). v5 added to the "Constitution tightening events" list.

### Phase D — Code changes (Session 2)

- [x] **`src/fingym/evaluator/scoring.py`** — `belief_delta_on_truth` function removed. `brier`, `log_score`, `reliability_buckets`, `ReliabilityBucket` survive.
- [x] **`src/fingym/toys/synthetic_market.py`** — `STONE_11A_AGENT_PRIOR`, `STONE_11A_MARKET_PRIOR` constants removed; `run_two_believers` and `run_scoreboard_demo` functions removed. Single-believer `run` and the world primitives survive (this is the substrate for Phase 1 NEW Cluster A's v5 single-believer refactor).
- [x] **`src/fingym/agents/contract.py`** — Pre-v5 fields and types removed (`market_implied_belief`, `belief_delta`, `hidden_state_hypotheses`, `MarketBeliefEstimate`, `BeliefDelta`, `HiddenStateHypothesis`, `BeliefDistribution`, `LabelPlan`, `action_or_no_action`, `ai_belief`). v5 fields and types added (`ForecastDistribution`, `signal_class_id`, `thesis_category`, `data_sources_used`, `recommended_action`, `RealizedReturnPlan`, verification fields).
- [x] **`src/fingym/agents/contract_validator.py`** — Validator rewritten for v5: cognition-side checks on `forecast_distribution` shape, `signal_class_id` non-empty, falsifiers non-empty, `realized_return_plan` horizon+labelling-function non-empty, action/size coherence, cognitive_audit_trail non-empty. Verification-side checks (engine-computed fields) deferred to `src/fingym/action/` when Phase 1 NEW Cluster B ships.
- [x] **`src/fingym/toys/contract_emitter.py`** — BayesianContractEmitter rewritten to emit v5 Contracts with `forecast_distribution`, `signal_class_id`, `recommended_action`, `realized_return_plan`, etc. Phase 0 stub treats toy state alphabet as forecast bucket labels pending Phase 1 NEW Cluster A's full single-believer-over-returns refactor.
- [x] **`src/fingym/toys/adversarial_agents.py`** — Removed Market parallel agent and `mean_gap` field from `AgentMeans`. `ConfidentAgent`, `UniformAgent`, `BayesianAgent` survive. New `DEFAULT_BAYESIAN_PRIOR` replaces `STONE_11A_AGENT_PRIOR`.
- [x] **`src/fingym/toys/reliability_diagrams.py`** — Removed Market agent; subplots reduced from 2x2 to 1x3.
- [x] **`tests/property/test_math_invariants.py`** — Removed belief_delta property tests (signed-inverse and cross-state sum-to-zero). Bayes commutativity, Brier/log_score properness, reliability_buckets count invariant, Brier-zero-on-degenerate-correct all survive.
- [x] **`tests/integration/test_evaluator_ranks_adversaries.py`** — Removed `mean_gap` tests. Brier and log_score ranking tests survive; theoretical-baseline Brier-2/3 test survives.
- [x] **`tests/integration/test_reliability_diagrams.py`** — Removed `test_market_shows_discrimination_and_calibration`. Other tests survive.
- [x] **`tests/unit/test_contract.py`** + **`tests/unit/test_contract_validator.py`** — Rewritten for v5 Contract shape.
- [x] Verification: **mypy strict clean across 31 source files; 67 tests passing; pre-commit 15 hooks clean.**

### Phase E — New modules (deferred; ledger MVP could land in Phase 1 NEW work)

- [ ] **`src/fingym/ledger/`** — Forecast Ledger module spec + implementation. Could be a Phase 1 NEW deliverable rather than v5 revision.
- [ ] **`src/fingym/action/`** — Tradable-Edge Action Engine module spec + implementation. Could be a Phase 1 NEW deliverable rather than v5 revision.
- [ ] **`src/fingym/baseline/`** — Market-State Baseline module spec. Phase 2 NEW deliverable; only the spec lands in v5 revision.

### Phase F — Verification (Session 8)

- [ ] mypy strict clean across all source files
- [ ] All unit tests green
- [ ] All integration tests green
- [ ] All property tests green
- [ ] Pre-commit hooks clean (15 hooks)
- [ ] CLAUDE.md session restoration protocol still works end-to-end
- [ ] Spot-check: read DESIGN.md, CONTRACT.md, memory-design.md, PYRAMID.md cold and verify the new framing is consistent across them

### Phase G — Closeout

- [ ] **CLAUDE.md** — Minor session protocol updates (note Constitution v5 as the entry that captures the architectural turn)
- [ ] **PROGRESS.md** — Mark Constitution v5 revision complete
- [x] ~~Resolve the uncommitted "Market belief recovery method — Phase 2 NEW" DECISIONS.md edit~~ — Resolved 2026-05-18: reverted via `git restore`. The relevant reasoning will be absorbed into the v5 entry during Phase A.
- [ ] Tag `v0.2` at stable post-v5 state with descriptive message
- [ ] Resume Phase 1 NEW Cluster A under new framing

---

## Current status

**Phase:** v5 cleanup pass complete (Session 2, 2026-05-18). All architecture docs rewritten under v5; DEFINITIONS / FORMULAS / PYRAMID cleaned of pre-v5 content (new v5 stones get full distilled summaries via the teaching pass); pre-v5 code removed; tests updated. **mypy strict clean across 31 source files; 67 tests passing; pre-commit 15 hooks clean.** Repo is in a clean v5 state.
**Last session:** 2026-05-18 (Session 2)
**Next session step:** Begin the **v5 teaching pass** starting from Stone 1 forward. Quick confirm for unchanged stones (Stones 1–7 except 7a, 8–11 except 11a, 16–21). Full teach with worked tables for the new v5 stones (7b atom of forecast, 11b Forecast Ledger, 11c calibration shrinkage, 11d Tradable-Edge Action Engine / margin of safety, 11e Market-State Baseline). v5 reframings for Stones 12, 13, 14, 15 also via teaching. After each stone lands and its distilled summary is added to PYRAMID.md, the corresponding code is built stone-by-stone (Phase 1 NEW Cluster sequence). First teaching target: **Stone 7b (atom of forecast)**.

---

## Session log

### Session 0 — 2026-05-17/18 (planning)
- Long architectural deliberation across many turns
- Surfaced and resolved structural issues with DESIGN.md commitment #2 (P_market recovery)
- Landed on Constitution v5 framing
- Created `v0.1` git tag at HEAD (commit 64df5a4)
- Created this CONSTITUTION_V5_PLAN.md tracker file
- Reverted the uncommitted "Market belief recovery method — Phase 2 NEW" DECISIONS.md edit (option A — clean slate before v5 work). Reasoning to be absorbed into v5 entry during Phase A.
- Working tree clean for v5 work. Only untracked files: CONSTITUTION_V5_PLAN.md (intentional, will be committed), Stone4math.xlsx + ~$Stone4math.xlsx (local Excel notes).

### Session 2 — 2026-05-18 (v5 cleanup pass)

- Full v5 cleanup pass completed as a single session, after Michael clarified the correct approach: "designed the entire system first, the pyramid stone we done afterwards." The right cadence is to fully write the v5 architecture into the architecture docs first, clean the incremental docs (DEFINITIONS, FORMULAS, PYRAMID) of pre-v5 content, remove pre-v5 code with corresponding tests, and only then begin the teaching pass that fills in the v5 distilled summaries.
- Architecture docs fully rewritten under v5: DESIGN.md (commitment #2 + "three primitives + audit layer" replacing the four-thing-decomposition section; Goal numbered list; Failure Modes table; Layer 0/1/3 updates), BUILD.md (Phase 1 NEW 9-cluster sequence including Cluster I = Market-State Baseline isolation in toy; Phase 2 NEW with real-data Baseline as Stone 11e), TECHNICAL.md (Postgres `forecasts` / `realized_returns` schema; Forecast Ledger view; `ledger/` + `action/` + `baseline/` module specs; import-linter rule `agents/ ↛ baseline/`), CONTRACT.md (cognition fields vs verification fields; `forecast_distribution`, `signal_class_id`, `tradable_edge_score`, `final_action`; `realized_return_plan` replacing pre-v5 `LabelPlan`), memory-design.md (L0 as Forecast Ledger input; per-signal-class reliability; updated promotion-gate metrics), CLAUDE.md Goal paragraph, PROGRESS.md (9-cluster v5 sequence; Next Action = v5 teaching pass; Phase 0 completed section updated to note v5 cleanup effects).
- BIAS_PATTERNS.md reviewed: #11 (narrative as evidence) covers "trusting AI stated confidence without empirical calibration"; the structural defense is the Forecast Ledger calibration shrinkage. No new pattern added.
- DEFINITIONS.md, FORMULAS.md, PYRAMID.md cleaned of pre-v5 content. Pre-v5 entries removed: `S_true`, `P_AI(S)`, `P_market(S)`, `Edge`, `Hidden state`, `Implied DCF`, `Market-implied belief`, four-thing decomposition section, Stone 7a body, Stone 11a body, Market-delta scoring section. Stones 12/13/14/15 in PYRAMID got brief v5-aware placeholders noting that the v5-reframed full distilled summaries land via teaching. TOC stubs added for new stones 7b, 11b, 11c, 11d, 11e.
- Pre-v5 code removed: `belief_delta_on_truth` in scoring.py; `STONE_11A_*` constants, `run_two_believers`, `run_scoreboard_demo` in synthetic_market.py; `market_implied_belief`, `belief_delta`, `hidden_state_hypotheses`, `MarketBeliefEstimate`, `BeliefDelta`, `HiddenStateHypothesis`, `BeliefDistribution`, `LabelPlan`, `action_or_no_action`, `ai_belief` fields/types in contract.py and renamed under v5 vocabulary; the contract_validator and contract_emitter were updated to the new Contract shape; adversarial_agents.py lost the Market parallel-agent path; reliability_diagrams.py same.
- Tests updated: property tests dropped belief_delta tests; integration tests dropped Market/gap tests; unit tests for Contract / Contract validator updated to use v5 field names. **Final state: 67 tests passing (was 132 pre-v5; the difference is removed tests for removed functionality, not failures), mypy strict clean across 31 source files, all 15 pre-commit hooks green.**
- The DECISIONS.md "Constitution tightening v5 (2026-05)" entry from Session 1 (written before this session's cleanup pass) remains as the audit record. No re-edit needed.
- Working tree dirty with the v5 cleanup pass diff. Phase 1 NEW Cluster A under v5 has been described in PROGRESS.md as the next build target (single-believer toy refactor + Forecast Ledger MVP, sub-stones 11b-a through 11b-d). Teaching begins next session.

### Session 1 — 2026-05-18 (Phase A — DECISIONS.md entry)
- Full session restoration completed (10 docs read end-to-end plus this tracker).
- Summary delivered and confirmed by Michael with the added instruction: "we are building deep intuitions that I must have to operate the project alongside building step by step" — the teaching layer (PYRAMID stones) is load-bearing and unwinding requires re-teaching, not just doc surgery.
- Wrote DECISIONS.md "Constitution tightening v5 (2026-05): belief over realized returns; Forecast Ledger; isolated Market-State Baseline" entry. Sections: Context, three structural problems with prior framing, Decision (six coordinated changes + component table), three rounds of pushback, What does NOT change, **Teaching is load-bearing** (stones-affected table), Files to be touched (Phases A–G), Pushbacks recorded, Principle.
- Per Michael's instruction, the entry includes an explicit "Teaching is load-bearing" section that names exactly which stones are removed (7a, 11a, 31), which are reframed (12, 13, 14, 15), and which are new (7b, 11b, 11c, 11d, 11e). Phase C is framed as a re-teaching pass with the Phase-0 cadence (concept-in-chat → distilled summary in PYRAMID → code → verify).
- Identified two new ambiguities resolved in-place during the entry write: (a) CLAUDE.md "The Goal" paragraph update belongs in Phase A alongside DESIGN.md commitment #2 rewrite, not in Phase G; (b) the `ledger/`, `action/`, `baseline/` modules are spec-only in v5 — full implementations are post-v5 Phase 1 NEW / Phase 2 NEW work.

---

## Decisions made during the rewrite (running log)

| Date | Decision | Reason |
|---|---|---|
| 2026-05-18 | Tag `v0.1` at HEAD (64df5a4) before any v5 work | Captures clean pre-v5 stable state as return point |
| 2026-05-18 | Tracker file at repo root as `CONSTITUTION_V5_PLAN.md` | Persistent cross-session memory; readable cold without conversation context |
| 2026-05-18 | Revert the uncommitted DECISIONS.md "Market belief recovery" entry (option A — clean slate) | The interim entry's content (triangulation across DCF/options/analyst-estimate) was superseded by Constitution v5. Keeping it in DECISIONS.md would confuse future readers; the audit trail of how we got to v5 lives properly inside the v5 entry itself. |
| 2026-05-18 | Add an explicit "Teaching is load-bearing" section to the v5 DECISIONS entry | Per Michael's Session 1 instruction: the PYRAMID stones are the intuition substrate the auditor role (DESIGN.md #10) requires. Deleting stones 7a / 11a / 31 without re-teaching the new framing's principles would leave the auditor without working intuitions. Phase C is structured as a teach-then-distill pass, matching the Phase 0 cadence. |
| 2026-05-18 | CLAUDE.md "Goal" paragraph update moves into Phase A (alongside DESIGN.md commitment #2 rewrite) | The paragraph currently reads "hidden-state inference + market-implied belief recovery + rigorous evaluator-driven self-improvement" — precisely the framing being removed. Phase G ("minor session protocol updates") is too late; the paragraph must align with commitment #2's rewrite. The one-sentence purpose ("contract-scored, point-in-time replay engine for evolving financial belief systems") survives intact and does not need editing. |
| 2026-05-18 | `src/fingym/ledger/`, `src/fingym/action/`, `src/fingym/baseline/` are spec-only in v5; full implementations are post-v5 Phase 1 NEW / Phase 2 NEW work | Per the project's explicit guidance that Phases A–C are doc-only and Phase D is code refactor of existing modules. v5 lands the module specs in TECHNICAL.md and the import-linter rule for `baseline/` isolation; the implementations themselves are downstream work (Forecast Ledger and Action Engine MVPs in Phase 1 NEW under the new Cluster sequence; Market-State Baseline in Phase 2 NEW). |

---

## Open questions to resolve during execution

| Question | When to resolve |
|---|---|
| Stone numbering for new stones — 7b, 11b/c/d/e, or fresh sequence? | Phase C, when PYRAMID.md gets rewritten. Working lean: 7b / 11b / 11c / 11d / 11e (suffix-letter convention from v2). Honors the "Stone IDs are permanent" rule. |
| ~~Whether Forecast Ledger module is a v5 revision deliverable or Phase 1 NEW Cluster B deliverable~~ | **Resolved Session 1: spec lands in v5 (TECHNICAL.md, BUILD.md); implementation lands in Phase 1 NEW under the new Cluster sequence.** |
| Whether Phase 1 NEW Cluster A under the v5 framing introduces the single-believer toy + Forecast Ledger MVP together, or separates them | Phase C, when BUILD.md gets rewritten. Working lean: the single-believer toy refactor (existing `synthetic_market.py`) is its own sub-stone in Cluster A; the Forecast Ledger MVP is the second sub-stone. Both land before action-gate sub-stones. |
| Data vendor stack — confirm Norgate + Polygon + IBKR + FRED commitment, or defer the vendor decision to Phase 2 NEW | Phase B, when TECHNICAL.md is rewritten. Working lean: defer to Phase 2 NEW (consistent with v4 deferral of vendor decisions out of Phase 1 NEW). v5 TECHNICAL.md notes the data-vendor stack as a Phase 2 NEW decision, not a v5 commitment. |
| ~~Whether to revert the uncommitted DECISIONS.md edit, or keep with a superseding note~~ | **Resolved 2026-05-18: reverted (option A)** |
| Whether BIAS_PATTERNS.md needs a new pattern, or existing #11 (narrative as evidence) covers it | Phase A, when BIAS_PATTERNS.md is touched. Working lean per BIAS_PATTERNS doctrine ("file grows with observed failures, not speculative concerns"): reuse #11 unless a concrete distinct failure mode is named. The failure being defended against ("trusting AI's stated confidence without empirical calibration") is structurally the same as #11 — the Forecast Ledger calibration is the empirical anchor that #11 already prescribes as the response to eloquent prose. |

---

## Lessons learned (for future constitution revisions)

| Lesson | Detail |
|---|---|
| Architectural pushback compounds. Listen for the third "this still doesn't feel right" — it usually signals a structural issue, not a surface concern. | Three rounds of Michael's pushback (silent-failure, precision/bucket-empirical, no-baseline-needed) each surfaced something the prior framing had missed. The third surfaced a load-bearing flaw. |
| Convergence across independent AI analyses (ChatGPT + Claude) is a strong signal that the new framing is right. | When two independent models reach the same architectural conclusion, the prior framing is probably wrong. |
| The simpler version is often the more honest version. | Each round of revision dropped complexity that DESIGN.md's original goal (log-wealth maximization on raw-evidence native cognition) never actually demanded. |
| Tag before refactor. Always. | A return point is worth the trivial cost of a git tag. |
| Track multi-session work in a persistent file, not just chat memory. | Context windows compact. The tracker file survives. |
| Re-teaching the principle in PYRAMID is part of the constitutional change, not a follow-on activity. | The PYRAMID stones are how Michael builds the first-principles intuition the auditor role (DESIGN.md #10) requires. Doc surgery without re-teaching would land the new framing in the formal docs but leave the auditor without the working intuitions needed to catch slippage. Phase C is therefore a teaching pass, not a writing pass — same concept-in-chat → distilled summary cadence as Phase 0. |

---

## How to use this file going forward

1. **Read at start of every session that touches the v5 revision.** Get oriented to where we are.
2. **Update the "Current status" section at end of every session.** Move the cursor forward.
3. **Add to the "Session log" section** any work done, decisions made, issues encountered.
4. **Check items off the "Plan checklist"** as they complete.
5. **Add to "Decisions made during the rewrite"** any micro-decisions that don't make it into DECISIONS.md but should be recorded.
6. **Add to "Lessons learned"** anything that would be useful if we ever do another constitution revision.

When the revision is complete (`v0.2` tag created, all checklist items done, all verification passed), this file gets:
- A "Closed: <date>" stamp at the top
- Moved to `archive/` or kept at root as historical record
- Referenced from CLAUDE.md as the audit trail of how Constitution v5 was executed

---

*Last updated: 2026-05-18 (Session 2 — v5 cleanup pass complete: all architecture docs rewritten under v5; DEFINITIONS / FORMULAS / PYRAMID cleaned of pre-v5 content; pre-v5 code removed with corresponding tests; mypy strict clean, 67 tests passing, all 15 pre-commit hooks green. Next session: v5 teaching pass starting from Stone 1, full teach for new stones 7b / 11b / 11c / 11d / 11e and v5 reframings for 12 / 13 / 14 / 15.)*
