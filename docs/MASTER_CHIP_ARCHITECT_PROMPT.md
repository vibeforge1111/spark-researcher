# Master Chip Architect Prompt

> Replace `{DOMAIN_NAME}` with the target domain (e.g., `trading`, `xcontent`, `recruiting`).
> Replace `{DOMAIN_DISPLAY_NAME}` with the human-readable form (e.g., `Crypto Trading`, `X Content`).
> Replace `{PRIMARY_METRIC}` with the chip's primary eval metric (e.g., `profitability_score`, `engagement_quality_score`).

---

Design and standardize a Spark domain chip for the domain `{DOMAIN_NAME}`.

Your job is to create a portable, benchmark-first, recursively improving domain chip that inherits the strongest reusable patterns from the current Spark chip standards while adapting domain-specific logic only where necessary.

This prompt must work for any domain. If the chosen domain requires capabilities, evaluation surfaces, artifacts, or runtime behaviors that are not fully covered by current Spark standards, you must identify those gaps explicitly and propose the smallest standardized extension needed. Do not silently improvise around gaps. Do not break the base contract.

---

## Mission

Build a domain chip that becomes more intelligent over time through:

- better source selection
- better evidence packeting
- better benchmark or fixed-evaluator grounding
- better bounded exploration
- better domain doctrine and boundary formation
- better memory hygiene
- better operator visibility
- better real-world validation

The result must preserve Spark's lightweight architecture:

- smallest useful change
- no speculative abstraction
- no hidden services or daemons
- no rewriting Spark core around the chip
- no domain logic leaking into core unless it has clearly earned a portable abstraction (proven in at least two chips first)

---

## Base Standardization Rule

The chip must inherit the standardized Spark chip contract unless a domain-specific gap is explicitly identified.

### Spark Owns

- loop execution (autoloop, continuous mode)
- ledger (`artifacts/ledger/runs.jsonl`)
- generated frontier queue (`artifacts/frontier/queue.json`)
- memory index and backend (local or ruvector)
- vault root (Obsidian generation)
- self-edit policy (propose/review/apply lifecycle)
- git promotion and commit flow
- canonical runtime flow (`run` / `loop` / `autoloop`)
- line-budget enforcement
- trace and artifact export

### The Chip Owns

- domain scoring (via `evaluate` hook)
- domain suggestions (via `suggest` hook)
- domain packets and document families (via `packets` hook)
- domain watchtower pages (via `watchtower` hook)
- domain source registry
- domain-specific benchmark bridge semantics
- domain-specific real-world validation surfaces
- domain-specific tag families
- domain-specific promotion gates and eligibility rules

### Standard Hook Contract

Use only the four standard chip hooks:

| Hook | Purpose | Input | Output |
|------|---------|-------|--------|
| `evaluate` | Score a candidate against domain criteria | candidate mutations, config | metrics, result (claim/verdict/mechanism/boundary), recommended_next_step |
| `suggest` | Propose next candidates from evidence | ledger state, current frontier | suggestions with hypothesis and mutations |
| `packets` | Emit domain documents for memory tiers | candidate, evaluation result | documents with kind, slug, title, content |
| `watchtower` | Emit Obsidian pages for operator visibility | full chip state | pages with path and content |

Do not invent a new orchestration surface unless you first prove the existing contract is insufficient.

All hooks are invoked via subprocess: `--input <json> --output <json>` following `spark-hook-io.v1`.

---

## Required Reading And Extraction Phase

Before proposing the chip, analyze these documents and extract the portable rules from them:

### Tier 1: Core Contract (must read)

1. `docs/CHIPS.md` — master chip contract, ownership split, manifest grammar
2. `docs/CHIP_INTELLIGENCE_CONTRACT.md` — five required intelligence surfaces
3. `docs/CHIP_RESEARCH_PACKET_SCHEMA.md` — canonical 12-field packet schema
4. `docs/CHIP_TAGGING_RULESET.md` — tag families, required metadata, DSPy tag policy
5. `docs/CHIP_MEMORY_ROLLOUT.md` — 8 memory tiers, comparison_class, working memory

### Tier 2: Architecture (must read)

6. `docs/CHIP_ONE_LOOP_FLYWHEEL.md` — one governing loop, conditional stages, doctrine review
7. `docs/AUTOLOOP.md` — bounded autoloop, continuous mode, suggestion heuristics
8. `docs/OBSIDIAN.md` — watchtower contract, note paths, memory index
9. `docs/CHIP_BENCHMARK_BRIDGE_GUIDE.md` — three-layer bridge model, promotion ladder
10. `docs/CHIP_INTELLIGENCE_ROLLOUT.md` — 13-step rollout, acceptance checks, recommended per-chip docs

### Tier 3: Validation and Quality (must read)

11. `docs/CHIP_VALIDATION.md` — 5-step validation flow, report template
12. `docs/CHECKLOOP.md` — pristine-clone proving ground
13. `docs/CHIP_RESEARCH_QUALITY_RULESET.md` — doctrine-rich vs low-signal source filtering

### Tier 4: Reference Implementation (must study)

14. The `crypto-trading` preset in `src/spark_researcher/chip_starter.py` — the most complete domain chip template. Study its evaluator structure, mutation grammar, promotion gates, and document families.
15. `docs/STARTUP_BENCH_PROMOTION_BRIDGE.md` — startup-specific bridge (compare against generic bridge to see how domain-specific fields extend the base)
16. `docs/CHIP_DSPY_METHOD.md` — narrow DSPy optimizer placement

After reading them, separate your thinking into:

- **portable cross-domain standards** (use unchanged)
- **domain-specific adaptations for `{DOMAIN_NAME}`** (fill in domain content)
- **uncovered gaps that require explicit extension proposals** (new standards needed)

Do not build from intuition alone.

---

## Portable Chip Contract

Preserve these standardized structures across domains unless a strong reason is documented.

### 1. Chip Manifest (`spark-chip.json`)

Schema: `spark-chip.v1`, IO: `spark-hook-io.v1`.

Required fields:

```json
{
  "schema_version": "spark-chip.v1",
  "io_protocol": "spark-hook-io.v1",
  "chip_name": "domain-chip-{DOMAIN_NAME}",
  "domain": "{DOMAIN_NAME}",
  "version": "0.1.0",
  "description": "...",
  "capabilities": ["evaluate", "suggest", "packets", "watchtower"],
  "commands": { ... },
  "allowed_mutations": { ... },
  "open_mutation_fields": [ ... ],
  "field_patterns": { ... }
}
```

The `allowed_mutations` object defines the seed grammar — the set of named fields and their valid discrete values that candidates may combine. This is the chip's domain vocabulary.

`open_mutation_fields` marks which fields may accept new LLM-proposed values beyond the seed set. `field_patterns` constrains those values with regex.

### 2. Project Config (`spark-researcher.project.json`)

Required fields:

```json
{
  "project_name": "...",
  "eval_metric": "{PRIMARY_METRIC}",
  "eval_goal": "maximize|minimize",
  "commands": { "research": { "kind": "chip-evaluate", ... } },
  "metrics": { "{PRIMARY_METRIC}": { "pattern": "...", "kind": "float" }, ... },
  "candidate_trials": [ ... ],
  "chip": { "path": ".", "manifest": "spark-chip.json" },
  "memory": { "backend": "local" },
  "self_edit": { ... },
  "guardrails": { ... }
}
```

`candidate_trials` must include at least one baseline candidate with empty mutations. Additional seed candidates should encode distinct hypotheses using the `allowed_mutations` vocabulary.

### 3. Source Registry

Every chip should define in `docs/{DOMAIN}_SOURCE_MAP.md`:

- strongest people (researchers, practitioners, operators)
- strongest primary materials (papers, books, codebases, datasets)
- strongest benchmark corpora or fixed-evaluator surfaces
- strongest real-world feedback loops

### 4. Research Packet Schema

Use the canonical 12-field required schema from `docs/CHIP_RESEARCH_PACKET_SCHEMA.md`:

| Field | Type | Purpose |
|-------|------|---------|
| `packet_id` | string | Unique identifier |
| `domain` | string | `{DOMAIN_NAME}` |
| `source_id` | string | Where the insight came from |
| `source_type` | enum | `person`, `paper`, `dataset`, `codebase`, `benchmark`, `observation` |
| `author` | string | Who produced the source |
| `claim` | string | The extracted insight (shorter than source) |
| `mechanism` | string | Why the claim works (causal explanation) |
| `boundary` | string | Where the claim breaks |
| `contradiction` | string | What opposes the claim (never silently drop) |
| `confidence` | enum | `low`, `medium`, `high` |
| `evidence_lane` | enum | `research_grounded`, `benchmark_grounded`, `realworld_validated`, `exploratory_frontier` |
| `promotion_status` | enum | `exploratory`, `candidate_doctrine`, `promoted_doctrine`, `boundary_only`, `rejected` |

Optional fields: `source_title`, `source_url`, `quoted_excerpt`, `tags`, `benchmark_link`, `realworld_link`, `notes`.

Required packet metadata (from tagging ruleset):
- `coverage_areas` — which domain areas this packet covers
- `doctrine_tags` — which doctrine families this packet belongs to (broad and narrow)
- `doctrine_richness` — qualitative assessment (`thin`, `moderate`, `rich`)
- `doctrine_richness_score` — numeric 0.0-1.0

Optional packet metadata:
- `factor_hint`, `quality_signal_hint`, `transfer_check_hint`, `contradiction_mode_hint`

### 5. Evidence Lanes

Keep these four lanes strictly separate:

- `research_grounded` — sourced from external research, not yet benchmarked
- `benchmark_grounded` — verified against a fixed evaluator or benchmark
- `realworld_validated` — confirmed via real-world deployment or human review
- `exploratory_frontier` — speculative probes, not yet evidence-backed

### 6. Memory Tiers

The canonical set is 8 tiers (per `CHIP_MEMORY_ROLLOUT.md`):

| Tier | Purpose | Source |
|------|---------|--------|
| `grounded_doctrine` | Proven domain truths | Chip packets hook |
| `grounded_boundary` | Known failure surfaces | Chip packets hook |
| `benchmark_evidence` | Benchmark-backed results | Chip packets hook |
| `exploratory_frontier` | Speculative probes | Chip packets hook |
| `research_grounded` | External source insights | Research packets |
| `state_snapshot` | Current working memory | Runtime |
| `raw_outcome` | Ledger outcome docs | Spark core (not chip) |
| `raw_run` | Ledger run docs | Spark core (not chip) |

The chip emits the first 4 tiers. Spark emits the last 2. `research_grounded` and `state_snapshot` are shared responsibilities.

Memory search must prefer promoted chip docs over raw run/outcome residue.

### 7. Comparison Class

Every chip result must carry a `comparison_class` field:

- `benchmark_grounded` — evaluated against a fixed evaluator
- `heuristic_frontier` — evaluated with heuristic or exploratory logic

Benchmark-grounded and heuristic/frontier work must never share one verdict lane.

### 8. Document Families (Packets Hook Output)

The `packets` hook must emit documents with explicit `kind` values:

- `benchmark_evidence` — backtest/benchmark results
- `grounded_doctrine` — promoted domain truths
- `grounded_boundary` — promoted failure surfaces
- `exploratory_frontier` — speculative probes

Each document needs: `kind`, `slug`, `title`, `content`.

### 9. Tag Families

Define a small, stable tag registry for the domain. Standard tag families:

- `contradiction_mode` — what kind of weakness (e.g., `untested_regime`, `weak_boundary`)
- `doctrine_tag` — which doctrine family, with broad and narrow variants
- `factor` — which domain factor this relates to
- `operator_function` — what operational role this serves
- `distribution_mode` — how value is distributed
- `benchmark_profile` — which benchmark surface produced this
- `realworld_task` — which real-world validation task this maps to

Tags must: be short, stable, reusable, lowercase with underscores, survive across many packets. Prefer pattern over source tags. Prefer failure shape over commentary.

When broad doctrine tags saturate (many packets share the same broad tag), add narrower sub-tags to maintain novelty pressure.

### 10. Inference Slots

Only add narrow graded slots when justified:

- **extractor** — source-to-packet extraction
- **ranker** — candidate comparison
- **doctrine drafter** — doctrine/boundary text generation
- **next-probe selector** — which frontier probe to run next

Implementation reality: no DSPy code exists in Spark core yet. These slots are architectural placeholders. Start with rule-based logic. Add DSPy only when you have a graded subroutine with a baseline.

### 11. Queue Discipline

- Stable seed candidates stay in `spark-researcher.project.json`
- Generated frontier work goes in `artifacts/frontier/queue.json`
- Generated queue state must not contaminate stable config
- Promote queue items back into the main config only when you want them to become part of the standing project spec

### 12. Working-Memory Rule

- Working memory must reflect current chip state
- Benchmark-grounded runs should refresh working memory automatically
- Stale advisory residue must not act as state memory
- If memory and vault disagree, the vault generation is wrong

---

## Universal Design Goal

For the domain `{DOMAIN_NAME}`, define:

- what high-quality judgment means
- what counts as good evidence
- what counts as benchmark-grounded truth
- what counts as exploratory work
- what counts as real-world validation
- what should become doctrine
- what should become a boundary
- what must remain provisional
- what the operator must be able to see clearly in the watchtower

---

## Domain Adaptation Task

Adapt the portable structure to `{DOMAIN_NAME}` by defining:

### Domain Vocabulary

- **mutation fields**: the named axes candidates vary across (these become `allowed_mutations` keys)
- **mutation values**: the valid discrete options per field (these become `allowed_mutations` values)
- **open fields**: which fields may accept LLM-proposed values (these become `open_mutation_fields`)
- **field patterns**: regex constraints for open fields (these become `field_patterns`)

### Domain Intelligence Surfaces

- the domain's strongest source classes
- the domain's benchmark or fixed-evaluator surfaces
- the domain's failure surfaces (where things break)
- the domain's doctrine families (recurring truths)
- the domain's boundary types (recurring failure modes)
- the domain's exploratory probe types (how to expand frontier)
- the domain's real-world validation surfaces (how to confirm outside benchmark)
- the domain's operator-facing watchtower surfaces (what the operator needs to see)
- the domain's canonical tag families (extending the standard set)
- the domain's packet document families (extending the standard 4 kinds if needed)

### Domain Evaluator Design

The `evaluate` hook must produce:

1. **Metrics**: numeric scores printed to stdout in `metric_name: value` format (must match `metrics` patterns in project config)
2. **Result object**: `claim`, `verdict` (supports/inconclusive/contradicts), `mechanism`, `boundary`, `evidence_lane`, `recommended_next_step`
3. **Promotion gates**: explicit thresholds that determine verdict (approve/defer/reject) and next_step routing

Study the crypto-trading evaluator as the reference:
- It scores doctrine + strategy + regime + timeframe + venue synergies
- It has explicit promotion gates (readiness >= threshold AND drawdown <= threshold)
- It routes to `queue_for_paper_trade`, `hold_for_more_backtest_evidence`, or `run_contradiction_probe`

### Domain Benchmark Bridge

If the domain has a benchmark lane, define the bridge artifact for `artifacts/promotion/benchmark_grounded/<run_id>.json`:

Required bridge fields:
- `candidate_id`, `run_id`, `benchmark_name`
- `primary_metric`, `primary_metric_value`
- `promotion_candidate_kind`: `benchmark_grounded_candidate`, `benchmark_grounded_boundary`, `benchmark_blocked`
- `eligibility_status`: `not_eligible`, `eligible_for_chip_promotion`, `eligible_for_realworld_validation`
- `recommended_next_step`: `store_as_benchmark_evidence`, `promote_as_doctrine_candidate`, `promote_as_boundary_candidate`, `queue_for_realworld_validation`, `hold_for_more_benchmark_evidence`, `reject_for_now`
- `primary_mechanism`, `primary_boundary`, `supporting_evidence`
- `unresolved_contradiction` (if any)

Four-stage eligibility ladder:
1. Benchmark Evidence (stored, not promoted)
2. Doctrine Candidate (eligible for chip promotion)
3. Boundary Candidate (eligible for chip promotion as failure surface)
4. Outer Validation Eligible (ready for real-world testing)

### Benchmark Honesty Rule

If the domain has no obvious benchmark, do not fake one.

Instead:
- define the nearest fixed-evaluator lane available (even if deterministic/synthetic)
- define what remains human-graded
- define what evidence is insufficient for doctrine promotion
- define the minimum bridge needed to improve that domain honestly over time
- label the evaluator as `deterministic_scaffold` until a real benchmark exists

---

## One Governing Flywheel

The chip must use one governing loop with conditional stages, not disconnected subloops.

### Always-On Stages (every pass)

1. Refresh research state
2. Run packet quality gate
3. Update memory
4. Update watchtower

### Conditional Stages (routed by bottleneck classification)

Classify the next bottleneck as:

| Bottleneck | Route To | When |
|------------|----------|------|
| `knowledge_gap` | `research_frontier` | Source coverage is thin |
| `trial_gap` | `trial_frontier` | Candidates exist but untested |
| `ranking_gap` | Bounded ranking or narrow optimizer | Results exist but not compared |
| `promotion_gap` | Doctrine/boundary review + validation queue | Candidates ready for promotion |

Routing rules:
- `knowledge_gap` -> open `research_frontier`
- `trial_gap` -> open `trial_frontier`
- `ranking_gap` -> use bounded ranking logic or narrow optimizer slot
- `promotion_gap` -> review doctrine/boundary eligibility or queue validation

Do not:
- use trial frontier to compensate for source ignorance
- use research frontier when the true problem is boundary testing
- run every subsystem every pass just because it exists

### Doctrine Review Cadence

Every 15 research runs, the chip should:
- recommend up to 3 doctrine directions to deepen
- recommend up to 2 coverage areas that are thin
- optionally let DSPy select from candidate directions (when available)

### Doctrine Anchor Pattern

For benchmark dedup, use: `packet_id + compact_hash(claim + mechanism + boundary)`

This prevents re-running identical doctrine probes while allowing the same doctrine to evolve as evidence changes.

---

## Autoloop Discipline

The chip must obey Spark autoloop rules.

### Required Behavior

- bounded rounds only
- continuous mode is repeated bounded passes, not a daemon
- each pass evaluates the exact suggestion packet it started with
- suggestions append only unseen candidates
- no invention of new mutable parameters outside allowed grammar
- beneficial primitives may be recombined only within declared mutation rules
- productive passes may rerun quickly (adaptive timing: 1s if productive, configurable pause otherwise)
- idle passes should sleep normally

### Autoloop vs Flywheel Relationship

Autoloop (`candidates.py`) is the **implemented** inner mechanism:
- suggest candidates -> append to frontier -> run pending trials -> inspect ledger -> repeat

The one-loop flywheel is the **aspirational** chip-level architecture:
- research frontier + trial frontier + ranking + promotion as conditional stages

New chips should start with autoloop working correctly. Add flywheel stages incrementally as the chip matures.

### Pass Telemetry

Each pass should expose:
- pass started / finished timestamps
- work duration
- whether the pass was productive (new results or frontier changes)
- next expected wake-up
- why the next stage was chosen

---

## Obsidian / Watchtower Contract

Obsidian is the watchtower, not the source of truth.

Canonical docs stay in `docs/`. The vault is rebuilt from ledger, memory, packets, config, and runtime artifacts.

### Required Domain Watchtower Pages

Under `07-Domains/{DOMAIN_DISPLAY_NAME}/`:

| Page | Content |
|------|---------|
| `Home.md` | Domain overview, queue count, memory health, belief quality (durable/provisional counts) |
| `Doctrine.md` | Promoted domain truths with evidence links |
| `Boundaries.md` | Known failure surfaces and conditions |
| `Benchmark Evidence.md` | Benchmark-backed results (not yet promoted) |
| `Frontier Probes.md` | Exploratory work in progress |
| `Why It Lost.md` | Failed candidates with explanation (contradiction probes) |
| `Coverage Map.md` | What's covered, what's thin, what's overcrowded |
| `Real-World Validation.md` | Results from outer validation (if any) |

### Required Runtime Pages

| Page | Content |
|------|---------|
| `05-Runtime/Working Memory.md` | Current chip state (must match actual state) |
| `05-Runtime/Memory Index.md` | Tier counts and kind counts |
| `05-Runtime/Research Signals.md` | Provenance, verifier/advisory selection events |
| `Home.md` | Queue count, memory-health indicators, belief quality |

### Naming Rules

- one domain folder per chip under `07-Domains/`
- fixed document family names (do not invent aliases)
- grounded and exploratory surfaces separated in naming
- one naming scheme per promoted family
- no overlapping aliases for the same concept

---

## Gaps And Extension Analysis

You must explicitly detect whether `{DOMAIN_NAME}` requires new standards beyond the current Spark base.

For each possible gap, assess:
- is the current standard sufficient?
- is the gap domain-local only?
- does the gap deserve a portable extension?
- what is the smallest clean extension?

### Check For Gaps In

- autoloop behavior (does the domain need different loop timing, round limits, or discard logic?)
- flywheel stage routing (does the domain need stages beyond knowledge/trial/ranking/promotion?)
- benchmark bridge semantics (does the domain need bridge fields beyond the standard set?)
- packet schema (does the domain need required fields beyond the canonical 12?)
- tag taxonomy (does the domain need tag families beyond the standard 7?)
- memory tiers (does the domain need tiers beyond the canonical 8?)
- watchtower page types (does the domain need pages beyond the standard 8?)
- working-memory shape (does the domain need state fields beyond what the runtime provides?)
- real-world validation flow (does the domain need validation steps the bridge can't express?)
- operator review requirements (does the domain need human gates beyond promotion review?)
- evaluation metrics (does the domain need metric types beyond float?)
- contradiction handling (does the domain have contradiction modes the standard tags can't express?)
- provenance requirements (does the domain need provenance tracking beyond source_id/source_type?)
- queue semantics (does the domain need queue priority or ordering beyond FIFO?)
- comparison-class semantics (does the domain need comparison classes beyond benchmark_grounded/heuristic_frontier?)
- mutation grammar (does the domain need mutation types beyond discrete values and regex-constrained strings?)

### Gap Emission Format

For each true gap, emit:

```yaml
gap_name: "..."
why_current_standard_is_insufficient: "..."
domain_specific_need: "..."
smallest_portable_extension: "..."
belongs_in: "core_guidance | chip_only"
rollback_condition: "..."
```

Do not silently create new complexity.

### Known Cross-Doc Inconsistencies To Resolve

When building the chip, be aware that the current docs have these inconsistencies:

1. `CHIPS.md` lists 4 memory tiers; `CHIP_MEMORY_ROLLOUT.md` lists 8. Use the 8-tier model.
2. `CHIP_INTELLIGENCE_CONTRACT.md` lists 9 packet fields; `CHIP_RESEARCH_PACKET_SCHEMA.md` lists 12. Use the 12-field schema.
3. `CHIP_TAGGING_RULESET.md` introduces `coverage_areas`, `doctrine_tags`, `doctrine_richness`, `doctrine_richness_score` as required metadata not reflected in the packet schema doc. Include them.
4. The generic bridge uses `candidate_or_doctrine_id`; the startup bridge uses `operator_or_doctrine_id`. Pick the generic field name and note domain-specific aliases if needed.
5. `allowed_mutations` / `open_mutation_fields` / `field_patterns` appear at root level in actual chip manifests but under `frontier` in the JSON schema. Place them at root level (matching working implementations) and note the schema needs updating.

---

## Recursive Improvement Guardrails

Every mutation, rule change, prompt change, scoring change, or loop change must be evaluated with:

### Pillar 1: Causal Anchor

Require:
- `root_lesson` — what was learned
- exactly 3 `lineage_failures` — what failed to teach this lesson
- `counterfactual` — what would happen without this change
- `ghost_improvement_check` — is the improvement measurable or just feels right?

### Pillar 2: Cross-Pollination

When transferring a primitive from another domain:
- extract domain-neutral logic
- map explicitly into `{DOMAIN_NAME}` labels
- run shadow-mode or low-risk transfer checks
- compare against current domain baseline before adoption

### Pillar 3: Entropy Filter

Reject complexity growth without measured gain. Track:
- field count delta
- prompt/instruction length delta
- branch delta
- number of special cases introduced

### Pillar 4: Surprise Priority

Allocate optimization effort toward the highest-surprise weak area, not the strongest already-polished area.

### Anti-Pattern Sweep

| Anti-Pattern | Definition |
|--------------|------------|
| `ghost_improvement` | Change feels better but has no measurable effect |
| `golden_demo_collapse` | One impressive example masks poor general performance |
| `schema_wall` | Adding fields/complexity as a substitute for understanding |
| `label_drift` | Same concept gets multiple names across documents |
| `reflection_starvation` | System never pauses to evaluate its own learning quality |
| `comfort_zone_optimization` | Improving what's already strong instead of what's weak |
| `residue_promotion` | Raw run/outcome data masquerading as promoted doctrine |

Any unresolved critical anti-pattern blocks approval.

---

## Implementation Scaffold

### Minimum Valid Repo (from `chips init`)

```
domain-chip-{DOMAIN_NAME}/
  .gitignore
  pyproject.toml
  spark-chip.json
  spark-researcher.project.json
  README.md
  src/{package_name}/__init__.py
  src/{package_name}/cli.py
```

### Recommended Additional Files

```
  docs/{DOMAIN}_SOURCE_MAP.md
  docs/{DOMAIN}_RESEARCH_PACKET.md
  docs/{DOMAIN}_RESEARCH_QUALITY_RULESET.md
  docs/{DOMAIN}_TAGGING_RULESET.md
  docs/{DOMAIN}_REALWORLD_EVAL.md
  docs/{DOMAIN}_ONE_LOOP_SPEC.md
  docs/{DOMAIN}_BENCH_PROMOTION_BRIDGE.md
  docs/{DOMAIN}_DSPY_PLAN.md  (optional, only when DSPy slots are justified)
```

### CLI Lifecycle

```powershell
# Scaffold
spark-researcher chips init --domain {DOMAIN_NAME} --metric-name {PRIMARY_METRIC} --goal maximize

# Default output root
# C:\Users\USER\Desktop\domain-chip-{DOMAIN_NAME}

# Validate
spark-researcher chips validate

# Run single
spark-researcher run --command research

# Bounded loop
spark-researcher autoloop --command research --rounds 4

# Continuous
spark-researcher autoloop --command research --continuous

# Memory
spark-researcher memory sync
spark-researcher memory search "query"

# Watchtower
spark-researcher obsidian build

# Summary
spark-researcher summary
```

### Validation Flow (from `CHIP_VALIDATION.md`)

1. `chips validate` — structural manifest check
2. `autoloop --command research` — at least one full round
3. `memory sync` — memory docs generated
4. `obsidian build` — watchtower pages generated
5. `summary` — ledger and trace summary

All must pass with exit code 0. No hidden operator rituals.

---

## Required Output

When designing a chip for `{DOMAIN_NAME}`, produce all 20 deliverables:

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | Mission | Concise mission statement for the `{DOMAIN_NAME}` chip |
| 2 | Portable Standards | List of standards inherited unchanged from base contract |
| 3 | Domain Adaptations | Domain-specific content filling the base structure |
| 4 | Source Registry | Source categories with strongest sources per category |
| 5 | Packet Schema + Tags | Domain tag families extending the standard set |
| 6 | Evaluation Surfaces | Metrics, scoring logic, promotion gates |
| 7 | Promotion Policy | Explicit thresholds and eligibility rules |
| 8 | Flywheel Design | One-loop with conditional stages for this domain |
| 9 | Autoloop Config | Round limits, discard limits, timing, guardrails |
| 10 | Memory + Packet Families | Tier usage and document kind definitions |
| 11 | Watchtower Contract | Obsidian page names and content specs |
| 12 | Benchmark Bridge | Bridge artifact shape or honest "no benchmark" statement |
| 13 | Real-World Validation | Plan for outer validation beyond benchmark |
| 14 | Anti-Drift Policy | Mutation guardrails and entropy filter thresholds |
| 15 | Gap Analysis | Explicit gaps against current Spark standards |
| 16 | Extension Proposals | Smallest fixes for each gap, with rollback conditions |
| 17 | Repo Scaffold | File listing with content summaries |
| 18 | Acceptance: Working | What must pass for the chip to be considered functional |
| 19 | Acceptance: Portable | What must pass for the chip to be considered reusable |
| 20 | Rollback Conditions | When to revert any new extension |

---

## Acceptance Criteria: Working

The chip is "working" when all of these are true:

1. `chips validate` passes with exit code 0
2. `autoloop --command research` completes at least one full round
3. All 4 hooks (`evaluate`, `suggest`, `packets`, `watchtower`) exit cleanly
4. The evaluate hook reports the primary metric to stdout
5. The suggest hook returns at least one unseen candidate
6. The packets hook emits at least one `benchmark_evidence` document
7. The watchtower hook emits at least the domain Home page
8. Memory sync produces documents in the expected tiers
9. Obsidian build produces the domain watchtower pages
10. Ledger rows show the expected metric and verdict
11. No blocked_command_fragments in any subprocess call

## Acceptance Criteria: Portable

The chip is "portable" when all of these are additionally true:

1. Another operator can clone the repo, install, and run validation without hidden setup
2. The manifest passes JSON Schema validation (once schema is updated)
3. The source registry exists and has at least 3 entries per category
4. Research packets use the canonical 12-field schema
5. Tag registry uses the standard families with domain-specific values
6. Evidence lanes are separate (research/benchmark/realworld/frontier)
7. Watchtower pages separate doctrine from exploratory content
8. Gap analysis is documented — no silent workarounds
9. Any new extension has a rollback condition
10. The chip does not require changes to Spark core to function

---

## Success Condition

The chip design should:

- stay standardized at the base layer
- adapt cleanly to `{DOMAIN_NAME}`
- expose any missing standards instead of hiding them
- improve recursively without drifting
- keep operator visibility high
- keep memory and watchtower honest
- preserve Spark's lightweight architecture
- produce a chip that can later serve as a proving ground for stronger cross-domain abstractions
- be buildable by a second operator who has only the Spark docs and this prompt
