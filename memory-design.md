# Memory Design — FinInferenceGym

## TL;DR

FinInferenceGym uses a **four-tier semantic pyramid** (L0 trajectory store → L1 observation atoms → L2 probationary hypotheses → L3 promoted skills), with **git as the per-item revision system** and **YAML in `memory_registry/` as the substrate** for L2/L3 artifacts. The promotion gate from L2 to L3 enforces DESIGN.md #4 via four checks: held-out replay calibration, cross-model regression, survivorship check, and domain-of-validity declaration. Memory artifacts carry **two edge types** in their schema (`derived_from`, `supersedes`); four more (`depends_on`, `contradicts`, `confidence`, `audit_trail` events) are reserved as optional fields for future use.

This is the lean MVP. It satisfies every DESIGN.md commitment. Six elaborations from the 2026 LLM-memory literature (NLI contradiction check at promotion, reversible-reconciliation cron, continuous per-use confidence scoring, etc.) are **explicitly deferred**, each with a documented trigger for revisiting.

We deliberately do not use vector retrieval over agent-writeable stores (FMP defense, DESIGN.md #6). We deliberately do not use a graph database (Postgres + YAML is sufficient at our scale).

---

## Purpose

This document is the source of truth for FinInferenceGym's memory architecture. It complements:

- **[DESIGN.md](DESIGN.md)** — the architectural commitments memory must honor
- **[TECHNICAL.md](TECHNICAL.md)** — the engineering decisions memory builds on (Python 3.12, Postgres 17 on Neon, alembic, YAML in git)
- **[BUILD.md](BUILD.md)** — the phase plan that determines when memory is built (substep 7 of Phase 0 for the schema; Phase 4 for population + promotion)
- **[PYRAMID.md](PYRAMID.md)** — the running teaching state; Layer 7 stones reference this document

It captures:

1. The **lean MVP architecture** we committed to
2. The **deferrals** — items evaluated, not adopted, with explicit revisit triggers
3. The **research evaluated** — what we learned from 2026 LLM-agent-memory literature and quant-fund research databases
4. The **first-principles audit** showing the architecture preserves every DESIGN.md commitment
5. The **empirical experiments** planned in later phases (uncommitted, evidence-driven)

This document is loaded at session start when memory-related work is on the table.

---

## What "memory" is in this project specifically

A terminology clarification, because most public LLM-memory research is about a different use case:

In FinInferenceGym, **memory is not user-session memory, not chat continuity, not personalization**. It is the system's **accumulated validated knowledge about how state translates to emissions in equity markets**. Memory items are structured hypotheses — claims like *"customer concentration > 15% predicts margin compression with 60% probability in subsequent year"* — with explicit domain-of-validity tags, justification chains, and audit history.

This is closer to a hedge fund's research knowledge base than to a chat agent's user memory. Most 2026 LLM-agent-memory research targets the chat-agent / coding-agent / personal-assistant use case; it required filtering for what actually applies to us.

---

## The lean MVP architecture

### Four-tier semantic pyramid

| Tier | What lives there | Storage | Retrievable into agent context? |
|---|---|---|---|
| **L0 — Trajectory store** | Raw beliefs, actions, labels, scores per agent run with full provenance (`as_of`, `as_known`, `source`, `version`) | Postgres tables, append-only, alembic-versioned schema | No — never retrieved into future agent context (FMP defense, DESIGN.md #6). Queryable by structured criteria. |
| **L1 — Observation atoms** | Agent's mid-session structured notes ("AAPL Q3 transcript mentioned 'pricing pressure' 7 times"). Foreign-keyed to L0 rows. | Postgres `observations` table, append-only | No — never retrieved into future agent context. |
| **L2 — Probationary hypotheses** | Structured claims under validation by the promotion gate | YAML files in `memory_registry/probationary/` | No — not until promoted. |
| **L3 — Promoted skills** | Validated, gated, model-agnostic skills the agent reads at session start | YAML files in `memory_registry/promoted/` | **Yes — read directly into context. No retrieval layer.** |

The pyramid supports **drill-down**: L3 items reference the L2 hypotheses they were promoted from; L2 items reference L1 observations they generalize; L1 observations reference L0 trajectory rows they were extracted from. The audit chain is end-to-end traceable.

### YAML schema for L2 / L3 artifacts

```yaml
# Memory artifact — schema for L2 (probationary) and L3 (promoted)
id: <uuid-string>            # stable, never reused; used as filename
tier: L2 | L3
content: |
  <markdown body — the claim itself, written for human and model readers>
domain_of_validity:          # required
  horizons: [1m, 3m, 6m, 1y]
  expression_types: [equity_long, equity_short, option_call, option_put, ...]
  sectors: [tech, financials, healthcare, ...]
  time_range_start: <as_of date or null>
  time_range_end: <as_of date or null>
derived_from:                # required for audit chain
  - trajectory_id: <l0 row id>      # if derived from raw evidence
  - observation_id: <l1 row id>     # if derived from session note
  - artifact_id: <l2/l3 uuid>       # if derived from higher-tier artifact
supersedes:                  # required when replacing an earlier artifact
  - <l2/l3 uuid of replaced artifact>
audit_trail:                 # required; lifecycle events
  - timestamp: <iso>
    action: proposed | promoted | demoted | retired
    by: <agent_id or system>
    reason: <markdown>
promotion_check_results:     # required for L3 only
  held_out_replay:
    pass: true
    splits_passed: 3
    calibration_delta: 0.04
  cross_model_regression:
    pass: true
    models_validated: [claude-opus-4-7, gpt-5-turbo]
  survivorship_check:
    pass: true
    delisted_sample_size: 240
  domain_of_validity_declared: true
promoted_at: <iso timestamp> # required for L3 only

# Optional fields — placeholders for deferred features. Not required.
# When deferred features land, these become populated. Schema migration is
# unnecessary because they are optional from the start.
contradicts: []              # list of artifact ids — populated when conflicts arise
depends_on: []               # list of artifact ids — populated when chains form
confidence: null             # float 0..1 — populated when continuous scoring lands
```

The schema lives in `src/fingym/memory/schema.py` as a pydantic v2 model (Phase 0 substep 7 deliverable). Validation runs at commit time via `mechanisms/lints/validate_memory_artifacts.py` (queued in [TECHNICAL.md](TECHNICAL.md)).

### Promotion gate — the four DESIGN.md checks

An L2 artifact promotes to L3 only after passing all four:

| Check | What it verifies | DESIGN.md reference |
|---|---|---|
| **Held-out replay calibration** | Adding this artifact to the agent's context improves calibration on a held-out set of trajectories the artifact was NOT derived from | DESIGN.md #4 |
| **Cross-model regression** | The calibration improvement holds when the agent uses a different model (≥2 model engines validated) | DESIGN.md #7 |
| **Survivorship check** | If the artifact uses transcript-derived signals, it still calibrates against the delisted shadow universe | DESIGN.md "Operational Constraints" |
| **Domain-of-validity declared** | The artifact specifies which horizons, expression types, sectors, and time ranges it applies to | BUILD.md, Phase 4 spec |

Failing any check → artifact stays in L2 (probationary) for further validation, or is retired with an audit-trail entry. Passing all four → artifact moves to `memory_registry/promoted/` with a git commit recording the promotion.

### Per-item versioning via git

Each L2 / L3 artifact is a single YAML file with a UUID-based stable filename. Git is the revision system:

- A new revision = a new commit to the YAML file
- The current file content = the current revision
- Old revisions remain accessible via `git log <file>` and `git show <commit>:<file>`
- No separate revision database

This gives us Kumiho's Item-Revision-Tag structure for free, without operational overhead of a graph database or custom revision system. The audit trail of a memory item is, literally, its git log.

### Reads, writes, and the agent's interaction with memory

**Reads (agent loads at session start):**

- All YAML files in `memory_registry/promoted/` (L3) — direct file read, no retrieval layer
- The agent's reasoning code optionally filters by `domain_of_validity` to focus on horizons/sectors/expression-types relevant to the current decision

**Reads on demand during a session:**

- Structured queries against L0 (e.g., "give me AAPL Q3 2018 transcript with `as_known ≤ 2023-09-30`")
- Drill-down: from any L3 artifact, traverse `derived_from` to inspect the L2 hypothesis, L1 observations, and L0 trajectory rows that produced it

**Writes the agent makes:**

- L1 observation atoms — written to the `observations` Postgres table during a session
- L2 hypothesis proposals — written as YAML files to `memory_registry/probationary/` with the agent's `produced_by` tag

**Writes the SYSTEM (not the agent) makes:**

- Promotion: L2 → L3 (a separate code path applies the gate and moves the file)
- Demotion / retirement: edits the audit trail and moves the file back to probationary or to a `retired/` subdirectory

**The cognition / verification boundary (DESIGN.md #5):**

The agent writes proposals. The system runs the gate and decides what enters L3. The agent never gates its own writes. Code-level enforcement: `src/fingym/agents/` must not import from `src/fingym/evaluator/` or from the promotion-gate module. Queued for enforcement by `import-linter` ([TECHNICAL.md](TECHNICAL.md), Phase 4).

### What we explicitly reject

| Rejected pattern | Why |
|---|---|
| **Vector retrieval into agent context over agent-writable stores** | Core FMP failure mode: agent writes hallucinations → vector similarity retrieves them → reasoning poisoned. DESIGN.md #6. |
| **Neo4j or other graph database for memory edges** | Postgres + YAML is sufficient at our 100s-1000s artifact scale. Operational overhead not justified. Kumiho uses Neo4j; we use git + YAML to get the same logical structure. |
| **Sakana-style hypernetwork-trained parametric memory** | Auditability matters more than speed. Year-2 own-model SFT (a planned DESIGN.md commitment) is a better parametric-memory path because full SFT is inspectable. |
| **Flat append-only memory** | UMG (uncontrolled memory growth) failure mode. The promotion gate prevents uncontrolled L3 growth; eviction handles slow decay. |
| **Recency-based eviction alone** | Would discard valid skills during slow markets. Our eviction is calibration-driven only. |
| **Wiki-compiled corpus as primary agent input** | Would violate DESIGN.md #6 (raw evidence in). Wiki-compilation is a Phase 1 A/B experiment — uncommitted. |
| **Agno or other ops platforms at MVP** | Phase 3+ decision when we deploy live. Rolling our own with Fly.io + Postgres is simpler for single-user. |
| **Embedding-based "similar situation" retrieval (auto-analogy)** | Real loss. Replaced by: (a) structured analogical queries against L0; (b) L3 skills that explicitly encode cross-name patterns with declared domain-of-validity. Validated analogy beats fuzzy analogy. |

---

## Deferrals — what's queued and what triggers each

These were evaluated, found principled and useful, and explicitly deferred. The trigger column specifies what evidence or condition would justify adopting each. The deferral list is itself part of the architecture — it preserves what we considered so future sessions don't re-litigate.

| Deferred item | What it is | Source | Trigger to revisit |
|---|---|---|---|
| **NLI contradiction check at promotion** | Automated NLI inference checking whether a new L3 artifact contradicts existing L3 artifacts | SSGM ([arxiv 2603.11768](https://arxiv.org/html/2603.11768v1)) | When promoted memory exceeds ~100 items, OR when a manual conflict is first detected |
| **`depends_on` edge type** | Tracks "if this is invalidated, downstream items need re-evaluation" — supports AnalyzeImpact traversal | Kumiho ([arxiv 2603.17244](https://arxiv.org/html/2603.17244)) | When an L3 artifact derives from another L3 artifact (i.e., when chains form) |
| **`contradicts` edge type** | Explicit conflict markers between artifacts | Kumiho | First detected conflict between L3 artifacts |
| **Reversible-reconciliation cron** | Nightly job that re-validates all L3 artifacts against current L0 trajectory data; demotes artifacts whose justification no longer holds | SSGM | When any L3 artifact has been promoted for >3 months without re-validation, OR market regime change suspected |
| **Continuous per-use confidence scoring** | Update each artifact's confidence after each use based on the calibration of the resulting belief | Mem0 state-of-2026 survey, your prior article | When promotion-gate periodic re-validation can't keep up with memory growth |
| **Capped index file (Claude-Code MEMORY.md style)** | A small, always-loaded markdown index of L3 artifacts; topic files load on demand | [Claude Code memory docs](https://code.claude.com/docs/en/memory) | When `memory_registry/promoted/` has >200 files |
| **Postgres index for typed-edge traversal** | Database-side index over YAML edge fields for fast AnalyzeImpact traversal | GBrain | When edge traversal takes >1 second on common queries |
| **Read-only vector retrieval over L0 raw evidence** | Embedding-similarity search over the trajectory store ONLY (never agent-writable); strictly read-only | None — open empirical question | When we have data showing structured-query analogical retrieval has hit a calibration ceiling AND vector search over read-only L0 would improve it |
| **Skill-as-method-call markdown procedures** | Procedural knowledge (how to investigate, how to diarize) encoded as parameterized markdown files | GBrain, Yegge/Tan | Phase 4+ refinement; current Python code is sufficient for now |

The principle: **build the smallest thing that honors DESIGN.md, then add complexity when evidence demands it.** The deferred features are real and the source references are validated; we add when triggered, not preemptively.

---

## Research evaluated

Summary of what we read and what we took from each, in roughly descending order of influence on our final design.

| Reference | What it is | What we took |
|---|---|---|
| **[Kumiho: Graph-Native Cognitive Memory (arxiv 2603.17244)](https://arxiv.org/html/2603.17244)** | Formal belief revision (AGM postulates) for LLM agent memory; Item-Revision-Tag model; six typed edges; AnalyzeImpact traversal; 93.3% on LoCoMo-Plus. Uses Neo4j + Redis. | **Most influential.** Adopted: typed edges as YAML fields (`derived_from`, `supersedes` at MVP); the revision model via git (instead of Neo4j); audit-trail discipline. Deferred: full Neo4j substrate (Postgres + YAML sufficient at our scale). |
| **[SSGM: Stability and Safety Governed Memory (arxiv 2603.11768)](https://arxiv.org/html/2603.11768v1)** | Governance middleware: truth-maintenance-gated writes, NLI consistency checks, dual storage (mutable active + immutable episodic ledger), reversible reconciliation, drift bounds. | Validated our promotion gate as the right framing. Deferred: NLI check, reconciliation cron. Confirmed: our L0 trajectory store IS the "immutable episodic ledger" SSGM cares about. |
| **[Tencent TencentDB-Agent-Memory](https://github.com/Tencent/TencentDB-Agent-Memory)** | Production memory system: four-tier semantic pyramid (L0 Conversation → L1 Atom → L2 Scenario → L3 Persona); symbolic memory via Mermaid; history offloading; drill-down by node_id. Concrete benchmarks: 61% token reduction, 51% pass rate improvement. | Adopted: four-tier semantic pyramid framing (with our specific tier names: Trajectory / Observation / Hypothesis / Skill, not Conversation/Atom/Scenario/Persona). Adopted: drill-down via reference IDs. Deferred: Mermaid symbolic memory (Phase 2+ session-context refinement). |
| **[ArcticDB — Man Group's research database](https://www.infoq.com/presentations/arcticdb/)** | Real hedge fund's actual research database: immutable versioning, time travel, pandas-compatible, 30K libraries, 40 GB/s. Built for research productivity (which IS our use case). | Validated our Postgres + alembic versioning direction. Confirmed: "isolation is expendable for research; versioning replaces locking." Lesson: lean harder on immutable versioning everywhere — trajectory rows append-only, memory artifacts revised via git, schema changes only via alembic. |
| **[MemMachine: Ground-Truth-Preserving Memory (arxiv 2604.04853)](https://arxiv.org/html/2604.04853v1)** | Three-layer (STM/LTM/Profile); sentence-level provenance inheritance; "never compress or infer facts during storage — only during retrieval." Explicitly acknowledges eviction is unsolved. | Validated: ground-truth preservation principle (L0 is immutable, distillation happens via separate write to L1/L2/L3, original always recoverable). Confirmed: even the best 2026 systems haven't solved eviction beyond temporal decay. |
| **[Claude Code memory docs](https://code.claude.com/docs/en/memory)** | Two-tier: human-written CLAUDE.md + auto-memory. Capped MEMORY.md index (200 lines / 25KB); topic files loaded on demand. Per-project, machine-local. | Inspired the deferred capped-index file pattern. Anthropic's own production system uses size-capped index — strong validation of the pattern when scale demands it. |
| **[GBrain (Garry Tan)](https://github.com/garrytan/gbrain)** | Self-wiring knowledge graph; typed edges built on write; hybrid search (vector + graph + BM25); 34 markdown skills; BrainBench eval framework. | Adopted: self-wiring typed edges concept (in YAML form, not graph DB). Adopted: BrainBench-style eval framework (deferred to Phase 4). Rejected: vector hybrid search (FMP risk). |
| **[Sakana doc-to-LoRA](https://pub.sakana.ai/doc-to-lora/)** | Hypernetwork that converts documents into LoRA adapters in <1s. Eliminates retrieval contamination but expensive to train (weeks of GPU). | Rejected as parametric-memory mechanism. Year-2 own-model SFT is the right parametric-memory route because full SFT is auditable; hypernetwork-internalized knowledge isn't. |
| **[Agno (agno-agi)](https://github.com/agno-agi/agno)** | SDK for agent platforms: API, RBAC, observability, scheduling. | Not relevant at MVP. Phase 3+ evaluation when we deploy live (probably overkill for single-user). |
| **[Codex memory PRs (10634, 10637)](https://github.com/openai/codex)** | Thread-scoped DB: trace_summary + memory_summary by thread_id. | Confirmed: Postgres + structured rows is the right substrate. Their thread-scoping is too thin for our use case. |
| **[AtomicStrata / llm-wiki-compiler](https://github.com/atomicstrata)** | Karpathy-pattern wiki compilation from raw documents. | Uncommitted. Will run as Phase 1 A/B experiment: wiki-compiled corpus vs raw evidence, calibration impact decides. |
| **[Hermes Agent (Nous)](https://hermes-agent.nousresearch.com/docs/)** | Agent-curated memory with periodic nudges, FTS5 cross-session recall, Honcho user modeling. | Less directly applicable (chat-agent shape). Concept "agent-curated memory" overlaps with our promotion gate. |
| **[Yegge / Garry Tan "thin harness, fat skills" essay](https://github.com/garrytan/gbrain)** | Skill files as parameterized markdown procedures; resolvers; latent-vs-deterministic split; diarization. | Adopted: latent-vs-deterministic discipline (where the model reasons vs where deterministic code runs). Deferred: skill-as-markdown procedures (Phase 4+ refinement of our Python-coded procedures). |
| **[Recursive Agent Optimization (arxiv 2605.06639)](https://arxiv.org/abs/2605.06639)** | Recursive agents that delegate sub-tasks to themselves. NOT about memory. | Phase 5+ technique for context-overload tasks. Park it. |
| **[State of AI Agent Memory 2026 (mem0.ai)](https://mem0.ai/blog/state-of-ai-agent-memory-2026)** | Overview of 2026 memory landscape: EverMemOS (93.05% LoCoMo), MemoryAgentBench (ICLR 2026), MAGMA (0.70 LoCoMo). | Confirmed: belief-revision-aware memory is the 2026 frontier, aligned with our direction. |

---

## First-principles audit (against DESIGN.md)

| Commitment | How the lean MVP preserves it |
|---|---|
| **#1 Evaluator load-bearing** | Promotion gate gates all writes to L3 (inference-affecting memory). Gate runs on the evaluator. |
| **#2 Belief over hidden state** | Memory artifacts are claims about how state translates to emissions — explicitly state-centric. |
| **#3 Time one-way valve** | L0 is point-in-time with `as_of` / `as_known`. Drill-down always honors as-of dates. Restated facts go in with their own `as_known`; derived artifacts reference specific L0 row IDs. |
| **#4 Verified updates only** | The promotion gate (held-out replay + cross-model + survivorship + domain-of-validity) is exactly this commitment in code. |
| **#5 Cognition/verification boundary** | Agent writes proposals (L1, L2); system runs the gate and decides what enters L3. Agent never gates its own writes. Code-level: `src/fingym/agents/` will not import from `src/fingym/evaluator/`. |
| **#6 Raw-evidence native reasoning** | Agent reads L3 (validated lessons) AND can drill to L0 (raw evidence) on demand. L1-L3 are aids to navigation, not filters. No vector RAG over agent-writable stores. |
| **#7 Intelligence in architecture, model-agnostic memory** | YAML / markdown is model-agnostic. Survives model swap. Cross-model regression check at promotion enforces this. |
| **#8 Two-axis improvement** | L0 trajectory store is the SFT-fit data spine. Year-2 own-model fine-tune reads from L0 (and labels and audit trail of memory artifacts). |
| **#9 Population, not single agent** | Each agent variant proposes memory artifacts; promotion gate validates against held-out data. Multiple variants compete on the evaluator scoreboard. |
| **#10 Michael as auditor** | Drill-down audit chain L3 → L2 → L1 → L0 + git history of every artifact + audit-trail field. Auditability is structural. |

The architecture preserves every DESIGN.md commitment without exception.

---

## Empirical experiments (uncommitted)

These are not architectural commitments. They are experiments we plan to run during specific phases to decide between architectural alternatives based on calibration impact.

### Experiment A — Wiki-compilation of the transcript corpus

**Phase:** 1 (Data Spine).
**Question:** Does pre-compiling the 1700-name transcript corpus into a structured interlinked wiki (Karpathy LLM Wiki pattern, à la AtomicStrata) improve agent calibration vs. having the agent read raw transcripts directly?
**Method:** Build two versions of the data spine — (a) raw transcripts only, (b) raw transcripts + compiled wiki. Run the same model-driven agent against both. Measure calibration on held-out trajectories.
**Decision rule:** If wiki improves calibration by ≥5% with no domain-of-validity regression, adopt the wiki layer. Else discard.

### Experiment B — Read-only vector retrieval over L0

**Phase:** 2 or 3.
**Question:** Does adding vector retrieval over the **read-only** trajectory store improve the agent's ability to find analogous past situations? (Restriction: vector index is over L0 ONLY, never over L1/L2/L3 which the agent has written to. This preserves the FMP defense.)
**Method:** Build vector index over L0 emissions corpus. Compare agent calibration with and without access to vector retrieval.
**Decision rule:** Same as above — calibration impact decides.

Both experiments are designed so the decision is empirical, not architectural. If neither helps, we don't adopt them.

---

## Operational notes

### Where things live

| Artifact | Location |
|---|---|
| Memory schema (pydantic model) | `src/fingym/memory/schema.py` (Phase 0 substep 7) |
| Memory artifact YAML validator | `mechanisms/lints/validate_memory_artifacts.py` (queued) |
| L2 artifacts (probationary) | `memory_registry/probationary/<uuid>.yaml` |
| L3 artifacts (promoted) | `memory_registry/promoted/<uuid>.yaml` |
| Retired artifacts | `memory_registry/retired/<uuid>.yaml` |
| L0 trajectory tables | Postgres: `beliefs`, `actions`, `labels`, `scores` |
| L1 observation table | Postgres: `observations` |
| Promotion-gate code | `src/fingym/evaluator/promotion_gate.py` (Phase 4 deliverable) |
| Agent memory reader | `src/fingym/agents/memory_reader.py` (Phase 2 deliverable) |
| Agent memory writer (L1/L2) | `src/fingym/agents/memory_writer.py` (Phase 2 deliverable) |

### Code-level boundary enforcement

`src/fingym/agents/` MUST NOT import from `src/fingym/evaluator/`. This is the cognition/verification boundary (DESIGN.md #5) in code. Enforced by `import-linter` (queued in [TECHNICAL.md](TECHNICAL.md), activates when both packages have content).

### Git workflow

- Proposing an L2 artifact: agent code writes YAML file with `tier: L2`. Commit message: `propose: <short claim title>`.
- Promotion gate decision: separate code path moves file from `probationary/` to `promoted/` and updates `tier`, `audit_trail`, `promotion_check_results`, `promoted_at`. Commit message: `promote: <id>`.
- Demotion / retirement: similar — move file, update audit trail. Commit message: `demote: <id>` or `retire: <id>`.
- All commits to `memory_registry/` are reviewable in git history. The audit trail is `git log memory_registry/`.

### Scale expectations

- Memory artifacts: 10s at end of Phase 0, 100s by end of Phase 4, perhaps low 1000s by year 2. Not a scale problem for YAML-in-git.
- Trajectory rows: ~272K belief records per pass through the universe × N agent variants × multiple revalidation passes. Millions of rows by year 1. Postgres territory with deliberate indexing.
- L1 observation atoms: similar order to belief records.

---

## Change control

This document is updated when:

1. **A deferred item gets adopted** — its trigger fired. Move the item from the deferral table to the appropriate part of the architecture, log the change in [DECISIONS.md](DECISIONS.md), update [TECHNICAL.md](TECHNICAL.md) and [BUILD.md](BUILD.md) substep specs as needed.
2. **An empirical experiment concludes** — calibration data is in. If a Phase 1/2 experiment adopts a new pattern, update this doc and DESIGN.md if a principle changes.
3. **A new external pattern emerges worth evaluating** — add to the research-evaluated table; either adopt, defer with trigger, or reject with reason.

This document does NOT change when:

- We hit a bug in implementation — that's a code fix, not an architectural change
- We tune parameters (e.g., the `>100 items` trigger threshold) — note in DECISIONS.md if material, but not a memory-design change
- We refine the YAML schema with new optional fields — update TECHNICAL.md's memory section

Substantive changes to this document require deliberation logged in [DECISIONS.md](DECISIONS.md) and Michael's sign-off, the same protocol that protects [DESIGN.md](DESIGN.md).
