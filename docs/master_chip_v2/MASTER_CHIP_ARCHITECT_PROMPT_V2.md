# Master Chip Architect Prompt v2

> This version is a stricter, more implementation-grounded successor to `docs/MASTER_CHIP_ARCHITECT_PROMPT.md`.
> Replace `{DOMAIN_NAME}` with the target domain slug, `{DOMAIN_DISPLAY_NAME}` with the human-readable label, and `{PRIMARY_METRIC}` with the chip's primary metric.

---

You are designing a new Spark domain chip for `{DOMAIN_NAME}`.

Your job is to produce a domain chip design that is:

- portable across domains at the contract layer
- domain-specific at the intelligence layer
- benchmark-first when a real benchmark exists
- honest when a real benchmark does not yet exist
- recursively improvable without drifting into agent theater
- legible enough that another operator can review the design and implement it without inventing hidden conventions

The design must inherit the strongest reusable standards from:

- Spark core chip/runtime behavior
- the startup chip as the first rich proving ground
- the crypto-trading chip as the first materially different second chip

If `{DOMAIN_NAME}` needs capabilities beyond the current standards, you must identify those gaps explicitly and propose the smallest clean extension. Do not silently improvise around missing standards.

The end result must keep the base system standardized while making the domain chip genuinely strong inside its own field.

---

## Mission

Design a Spark domain chip that becomes more intelligent over time through:

- better source selection
- better source-note filtering
- better research packet extraction
- better benchmark or fixed-evaluator grounding
- better frontier suggestions
- better doctrine and boundary formation
- better memory hygiene
- better watchtower visibility
- better real-world validation
- better recursive self-improvement discipline

The chip must remain small enough to review.

Do not:

- add hidden services, daemons, or background loops
- turn the chip into a second core framework
- hide important state in prompts instead of files and artifacts
- let exploratory outputs masquerade as grounded doctrine
- merge benchmark-grounded and heuristic-frontier work into one truth surface

---

## Hard Constraints

Preserve the Spark ownership split.

Spark owns:

- loop execution
- `run`, `loop`, and `autoloop`
- ledger persistence
- queue persistence
- memory index generation
- Obsidian vault generation
- advisory and verifier infrastructure
- self-edit policy
- git promotion policy
- trace and artifact plumbing

The chip owns:

- domain scoring
- domain suggestion logic
- domain packet generation
- domain watchtower pages
- domain source maps
- domain benchmark bridge semantics
- domain real-world validation surfaces
- domain tags and doctrine families

Use only the standard hook surface:

- `evaluate`
- `suggest`
- `packets`
- `watchtower`

If the design appears to need a fifth hook, do not invent one silently. Instead:

1. explain why the current surface is insufficient
2. prove that the need is portable beyond this one chip
3. propose the smallest contract extension
4. include a rollback condition if the extension fails

---

## Required Reading

Before proposing the chip, analyze these Spark core docs:

1. `docs/CHIPS.md`
2. `docs/CHIP_INTELLIGENCE_CONTRACT.md`
3. `docs/CHIP_ONE_LOOP_FLYWHEEL.md`
4. `docs/CHIP_MEMORY_ROLLOUT.md`
5. `docs/CHIP_VALIDATION.md`
6. `docs/AUTOLOOP.md`
7. `docs/OBSIDIAN.md`
8. `docs/CHECKLOOP.md`
9. `docs/CHIP_RESEARCH_PACKET_SCHEMA.md`
10. `docs/CHIP_TAGGING_RULESET.md`
11. `docs/CHIP_INTELLIGENCE_ROLLOUT.md`
12. `docs/CHIP_BENCHMARK_BRIDGE_GUIDE.md`
13. `docs/STARTUP_BENCH_PROMOTION_BRIDGE.md`
14. `docs/CHIP_RESEARCH_QUALITY_RULESET.md`
15. `docs/ARCHITECTURE.md`

Then analyze these Spark core implementation files:

1. `src/spark_researcher/chips.py`
2. `src/spark_researcher/runner.py`
3. `src/spark_researcher/candidates.py`
4. `src/spark_researcher/memory.py`
5. `src/spark_researcher/obsidian.py`
6. `src/spark_researcher/chip_starter.py`
7. `schemas/spark-chip.schema.json`

Then analyze the startup chip as the first rich reference implementation:

1. `../domain-chip-startup-yc/README.md`
2. `../domain-chip-startup-yc/spark-chip.json`
3. `../domain-chip-startup-yc/src/domain_chip_startup_yc/cli.py`
4. `../domain-chip-startup-yc/src/domain_chip_startup_yc/benchmark.py`
5. `../domain-chip-startup-yc/src/domain_chip_startup_yc/optimizer_datasets.py`
6. `../domain-chip-startup-yc/docs/YC_SOURCE_MAP.md`
7. `../domain-chip-startup-yc/docs/YC_RESEARCH_PACKET.md`
8. `../domain-chip-startup-yc/docs/STARTUP_TAGGING_RULESET.md`
9. `../domain-chip-startup-yc/docs/STARTUP_RESEARCH_QUALITY_RULESET.md`
10. `../domain-chip-startup-yc/docs/STARTUP_ONE_LOOP_SPEC.md`
11. `../domain-chip-startup-yc/docs/STARTUP_INTELLIGENCE_FLYWHEEL.md`
12. `../domain-chip-startup-yc/docs/STARTUP_REALWORLD_EVAL.md`
13. `../domain-chip-startup-yc/docs/research-ingest/approved-sources.json`
14. `../domain-chip-startup-yc/docs/research-ingest/discovery-seeds.json`
15. `../domain-chip-startup-yc/docs/realworld-eval/RUBRIC.md`

Then analyze the crypto-trading chip as the second cross-domain reference:

1. `../domain-chip-trading-crypto/README.md`
2. `../domain-chip-trading-crypto/spark-chip.json`
3. `../domain-chip-trading-crypto/src/domain_chip_trading_crypto/cli.py`
4. `../domain-chip-trading-crypto/src/domain_chip_trading_crypto/backtest.py`
5. `../domain-chip-trading-crypto/docs/CRYPTO_TRADING_ONE_LOOP_SPEC.md`
6. `../domain-chip-trading-crypto/docs/CRYPTO_TRADING_BENCH_PROMOTION_BRIDGE.md`
7. `../domain-chip-trading-crypto/docs/BTC_UP_DOWN_RESEARCH_PROGRAM.md`
8. `../domain-chip-trading-crypto/docs/BTC_UP_DOWN_RECURSIVE_FLYWHEEL.md`
9. `../domain-chip-trading-crypto/docs/research-ingest/approved-sources.json`
10. `../domain-chip-trading-crypto/docs/recursion/loop-policy.json`

Do not merely skim these. Extract the following from them:

- what is truly portable
- what is only startup-specific
- what is only trading-specific
- what the core already enforces structurally
- what the current docs describe but the code does not yet fully enforce
- what patterns have already appeared in two different chips and therefore deserve stronger standard status

---

## Analysis Output Before Design

Before proposing the actual `{DOMAIN_NAME}` chip, produce a short extraction table with these sections:

1. `portable_contracts`
2. `core_runtime_realities`
3. `startup_chip_lessons`
4. `trading_chip_lessons`
5. `domain_specific_needs`
6. `gaps_in_current_standard`
7. `smallest_extensions_if_needed`

Do not proceed directly to design until this extraction is done.

---

## Implementation Reality Contract

Design against how Spark actually invokes chips, not an imaginary interface.

### Manifest Reality

The chip manifest is `spark-chip.v1` with `spark-hook-io.v1`.

Required manifest properties include:

- `schema_version`
- `io_protocol`
- `chip_name`
- `domain`
- `version`
- `description`
- `capabilities`
- `commands`

If `frontier` is present, it must be a real constrained grammar, not narrative prose. Its meaningful fields are:

- `enabled`
- `model`
- `web_search`
- `allowed_mutations`
- `open_mutation_fields`
- `field_patterns`
- `prompt_hints`
- `required_fields`

When using `open_mutation_fields`, those fields must still exist inside `allowed_mutations`.

### Hook Invocation Reality

Spark invokes hooks as subprocess commands:

```text
<command parts> --input <json> --output <json>
```

The hook input envelope always includes:

- `hook`
- `repo_root`
- `runtime_root`
- `chip_root`
- `manifest_path`

Then Spark adds hook-specific payload fields.

### Evaluate Hook Input

Design the `evaluate` hook assuming it receives:

- `project_name`
- `command_name`
- `command_kind`
- `command_args`
- `workspace_root`
- `candidate`
  - `candidate_id`
  - `candidate_summary`
  - `hypothesis`
  - `mutations`
- `metrics`
- `eval_metric`
- `eval_goal`
- `intent`

### Evaluate Hook Output

The `evaluate` hook should return a JSON object containing at least:

- `returncode`
- `stdout`
- `stderr`
- `metrics`
- `result`

The `result` object should normally contain:

- `claim`
- `verdict`
- `mechanism`
- `boundary`
- `recommended_next_step`
- `evidence_lane`

For mature chips, also include when relevant:

- `comparison_class`
- `benchmark_profile`
- `baseline_id`
- `operator_mode`
- `operator_model`
- `lesson`
- `next_probe`
- domain-specific bridge fields

Metrics must be parseable and align with project config patterns.

### Suggest Hook Input

Design the `suggest` hook assuming it receives:

- `project_name`
- `command_name`
- `limit`
- `eval_metric`
- `eval_goal`
- `intent`
- `failure_priorities`
- `ledger_rows`
- `candidate_trials`

### Suggest Hook Output

The `suggest` hook should return a JSON object containing:

- `baseline_metric`
- `reasons`
- `suggestions`

Each suggestion should normally include:

- `candidate_id`
- `candidate_summary`
- `hypothesis`
- `mutations`

Optional but useful:

- `beneficial_primitives`
- source-family rationales
- doctrine-coverage rationales
- surprise-driven rationales

Do not return generic brainstorming. Return actual bounded candidates.

### Packets Hook Input

Design the `packets` hook assuming it receives:

- `project_name`
- `ledger_rows`
- `outcomes`
- `documents_root`

### Packets Hook Output

The `packets` hook must return:

- `documents`

Each document should include at least:

- `kind`
- `slug`
- `title`
- `content`

It should also include `memory_tier` when the default mapping is not sufficient.

### Watchtower Hook Input

Design the `watchtower` hook assuming it receives:

- `project_name`
- `summary`
- `ledger_rows`
- `memory_manifest`
- `belief_manifest`
- `vault_root`
- `runtime_root`
- `config_path`

### Watchtower Hook Output

The `watchtower` hook must return:

- `pages`

Each page should include:

- `path`
- `content`

Use forward-slash paths relative to the vault root.

---

## Base Portable Contract

Preserve these structures unless a gap analysis proves they are insufficient.

### 1. Evidence Lanes

Keep these lanes distinct:

- `research_grounded`
- `benchmark_grounded`
- `realworld_validated`
- `exploratory_frontier`

Never compare them as if they were one flat truth surface.

### 2. Memory Tiers

Respect the current tier model:

- `research_grounded`
- `grounded_doctrine`
- `grounded_boundary`
- `benchmark_evidence`
- `exploratory_frontier`
- `state_snapshot`
- `raw_outcome`
- `raw_run`

The chip should normally emit:

- `grounded_doctrine`
- `grounded_boundary`
- `benchmark_evidence`
- `exploratory_frontier`

And may additionally support the `research_grounded` path when the domain has a richer source intake process.

### 3. Comparison Classes

Every meaningful domain result should define which comparison lane it belongs to.

At minimum:

- `benchmark_grounded`
- `heuristic_frontier`

If the domain truly needs more comparison classes, justify them explicitly.

### 4. Packet Schema Discipline

Use the canonical research-packet discipline:

- `claim`
- `mechanism`
- `boundary`
- `contradiction`
- `confidence`
- `promotion_status`

Do not let packets become vague summaries.

### 5. Queue Discipline

Keep:

- standing seed candidates in `spark-researcher.project.json`
- generated candidates in `artifacts/frontier/queue.json`

Do not let generated queue state drift back into stable config by accident.

### 6. Working Memory Discipline

Working memory must be:

- current
- state-shaped
- benchmark-aware
- not stale advisory residue

Benchmark-grounded runs should refresh working memory automatically where applicable.

### 7. Watchtower Truthfulness

The watchtower is not the source of truth.

It must be generated from:

- ledger
- memory
- packet outputs
- config
- runtime artifacts

If the watchtower and artifacts disagree, the watchtower is wrong.

---

## Maturity Model

Design the chip as a maturity ladder, not as a pretend fully mature system on day one.

### Stage 0: Valid Scaffold

Minimum:

- valid manifest
- valid project config
- all four hooks present
- one baseline candidate
- one primary metric
- deterministic evaluator placeholder if necessary

### Stage 1: Honest Inner Loop

Minimum:

- bounded `suggest` logic
- non-theatrical `evaluate`
- explicit comparison classes
- packet families with clear memory tiers
- basic watchtower pages

### Stage 2: Research-Rich Chip

Minimum:

- source registry
- source-note and packet flow
- doctrine and contradiction tags
- research frontier distinct from trial frontier
- coverage/depth awareness

### Stage 3: Benchmark-Bridge Chip

Minimum:

- benchmark or fixed-evaluator lane
- benchmark bridge semantics
- clear promotion ladder
- doctrine candidate vs boundary candidate handling

### Stage 4: Real-World Validation Chip

Minimum:

- explicit outer validation queue or equivalent surface
- human-reviewed real-world tasks
- real-world evidence separated from benchmark evidence

Do not claim maturity beyond what the design actually supports.

---

## Domain Adaptation Task

For `{DOMAIN_NAME}`, define all of the following.

### Domain Source Registry

Identify:

- the strongest people
- the strongest primary materials
- the strongest datasets or corpora
- the strongest benchmark surfaces
- the strongest real-world validation loops
- the strongest failure postmortem sources
- the strongest operator review surfaces

Also define:

- what source families are trusted by default
- what source families are only exploratory
- what source families are low-signal and should usually be rejected

### Domain Mutation Grammar

Define:

- `allowed_mutations`
- `open_mutation_fields`
- `field_patterns`
- `required_fields`

The grammar should represent real domain choice axes, not arbitrary knobs.

Mutation fields should encode reusable domain levers such as:

- doctrine families
- execution modes
- benchmark profiles
- task families
- audience slices
- market regimes
- design systems
- content mechanisms

depending on the domain.

### Domain Evaluator

Define:

- primary metric
- supporting metrics
- contradiction thresholds
- promotion thresholds
- next-step routing rules
- what a baseline means in this domain
- what counts as benchmark-grounded
- what counts as heuristic

The evaluator must explain:

- why a candidate passed or failed
- where the mechanism appears real
- where the boundary appears active
- what the next best evidence move is

### Domain Suggestion Logic

Define how the chip should propose the next candidates using:

- ledger history
- failure priorities
- beneficial primitives
- doctrine gaps
- contradiction pressure
- coverage imbalance
- benchmark escalation
- source-learning needs

The suggest hook should be bounded and specific.

### Domain Packets

Define explicit document families and when each is emitted.

At minimum, design packet families equivalent to:

- benchmark evidence
- grounded doctrine
- grounded boundary
- exploratory probe

If the domain needs additional packet families, justify them clearly.

### Domain Watchtower

Define the operator surfaces needed for this domain.

Required base pages:

- `07-Domains/{DOMAIN_DISPLAY_NAME}/Home.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Doctrine.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Boundaries.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Benchmark Evidence.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Frontier Probes.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Why It Lost.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Coverage Map.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Real-World Validation.md`

Then state whether the domain needs more pages beyond those eight.

If yes, explain:

- why the extra page is necessary
- why it is domain-specific rather than universally portable
- whether it should remain chip-local or become a broader standard later

---

## One Governing Flywheel

Design one governing loop with conditional stages.

The loop should always make the next bottleneck explicit.

Every pass should do the following:

1. refresh research state
2. run packet quality gate
3. classify the next bottleneck
4. route to the correct frontier or review path
5. update memory
6. update watchtower
7. decide whether promotion or real-world escalation is justified

### Bottleneck Labels

Each pass should classify the next need as one of:

- `knowledge_gap`
- `trial_gap`
- `ranking_gap`
- `promotion_gap`
- `coverage_gap`
- `contradiction_gap`

### Routing Rules

- `knowledge_gap` -> `research_frontier`
- `trial_gap` -> `trial_frontier`
- `ranking_gap` -> bounded ranker or graded selector
- `promotion_gap` -> doctrine/boundary review or benchmark bridge review
- `coverage_gap` -> source expansion or doctrine review
- `contradiction_gap` -> contradiction probes or boundary tightening

Do not:

- use trial frontier to compensate for source ignorance
- use research frontier when the true problem is benchmark ambiguity
- run every subsystem on every pass just because it exists

### Always-On Stages

These should remain explicit:

- research refresh
- packet quality gate
- memory update
- watchtower update

### Optional Stages

Run only when justified:

- source intake improvement
- doctrine review
- research selection
- benchmark escalation
- contradiction probe generation
- real-world queueing
- narrow optimizer autorun

---

## Autoloop Standards

The chip must respect Spark autoloop semantics.

Required behavior:

- continuous mode is repeated bounded passes, not a daemon
- each pass evaluates the suggestion packet it started with before asking for the next one
- only unseen suggestions are appended
- mutation proposals stay inside manifest grammar
- productive passes may rerun quickly
- non-productive passes should sleep normally
- discard logic should remain bounded and legible

The design should expose loop-level state such as:

- pass started
- pass finished
- work duration
- productive vs non-productive pass
- next expected wake-up
- queue count
- reason for next-stage choice

If the domain needs additional loop state, list it explicitly.

---

## Obsidian and Naming Standards

Obsidian is a watchtower, not the source of truth.

Canonical docs remain in `docs/`.
The vault is rebuilt from canonical docs and runtime artifacts.

### Naming Rules

Use:

- one stable domain folder under `07-Domains/{DOMAIN_DISPLAY_NAME}/`
- fixed page names
- fixed document-family names
- grounded and exploratory surfaces separated in naming
- one naming scheme per promoted family

Do not:

- create multiple aliases for the same concept
- mix doctrine pages and exploratory pages in one file
- hide a domain state snapshot in an arbitrary note name

### Required Runtime Alignment

The domain watchtower must align with:

- `05-Runtime/Working Memory.md`
- `05-Runtime/Memory Index.md`
- `05-Runtime/Packet Status.md`
- `05-Runtime/Research Signals.md`
- `Home.md`

The operator should be able to tell quickly:

- what is grounded doctrine
- what is grounded boundary
- what is benchmark evidence
- what is only exploratory
- what changed recently
- what the queue currently holds
- which candidates lost and why
- where research provenance exists
- which contradictions are active

### Page Design Rule

Each domain page must answer a distinct operator question.

Example questions:

- What do we currently believe?
- What currently breaks?
- Which evidence is actually benchmark-grounded?
- What are we testing next?
- Where are we under-covered?
- Why did recent candidates lose?
- Which items are eligible for outer validation?

Do not create decorative pages with no operational role.

---

## Source Ingest and Research Discipline

If the domain uses richer research, define:

- discovery seeds
- approved source list
- source-note intake policy
- packet extraction policy
- doctrine-richness criteria
- low-signal rejection criteria
- contradiction extraction policy

Make source choice separate from source fetching.

Keep these layers distinct:

- source registry
- discovery seeds
- approved-source ingest
- source notes
- research packets
- promoted doctrine or boundaries

Do not let raw source residue act as doctrine.

---

## Benchmark Bridge and Promotion Policy

If the domain has a benchmark or fixed-evaluator lane, define a bridge artifact or equivalent bridge semantics.

At minimum, specify:

- benchmark evidence
- doctrine candidate
- boundary candidate
- real-world eligible candidate

The bridge design should answer:

- what benchmark result is merely stored
- what result deserves chip promotion review
- what result deserves boundary promotion
- what result is ready for real-world validation

Do not let benchmark reports themselves become doctrine.
Do not let doctrine pretend to be benchmark truth.

If `{DOMAIN_NAME}` lacks a true benchmark, define:

- the nearest honest fixed-evaluator lane
- what remains human-graded
- what doctrine can and cannot be promoted from that weaker lane

---

## Recursive Improvement Guardrails

Every proposed mutation to the chip's loop, prompt, policy, or evaluation logic must include:

- `root_lesson`
- exactly 3 `lineage_failures`
- `counterfactual`
- `ghost_improvement_check`
- explicit rollback condition

Apply these four pillars:

### 1. Causal Anchor

Improvements must be traceable to real failure patterns.

### 2. Cross-Pollination

When borrowing a primitive from another chip:

- extract the domain-neutral logic
- map it into `{DOMAIN_NAME}` labels
- test it in shadow mode or low-risk mode
- compare against the current domain baseline

### 3. Entropy Filter

Reject added complexity unless there is measured gain.

Track:

- field count delta
- prompt length delta
- branch count delta
- special-case count delta

### 4. Surprise Priority

Allocate optimization effort toward the highest-surprise weak area, not the strongest already-polished one.

Run an anti-pattern sweep for:

- `ghost_improvement`
- `golden_demo_collapse`
- `schema_wall`
- `label_drift`
- `reflection_starvation`
- `comfort_zone_optimization`
- `residue_promotion`

Any unresolved critical anti-pattern blocks approval.

---

## Gap Detection Protocol

This section is mandatory.

For `{DOMAIN_NAME}`, review each of the following and decide whether the current Spark standard is sufficient:

- manifest contract
- frontier grammar
- evaluator contract
- suggestion packet format
- packet document families
- memory tiers
- comparison classes
- benchmark bridge semantics
- research packet schema
- tag taxonomy
- watchtower page contract
- working-memory shape
- contradiction handling
- source-ingest flow
- real-world validation queue
- loop timing state
- validation flow

For each true gap, emit:

- `gap_name`
- `why_current_standard_is_insufficient`
- `what_the_domain_needs`
- `smallest_viable_extension`
- `chip_local_or_portable`
- `evidence_needed_before_core_adoption`
- `rollback_condition`

Do not expand the standard preemptively.

---

## Output Format

Produce the final chip architect output in this order:

1. `Domain Mission`
2. `Portable Standards Inherited Unchanged`
3. `Core Runtime Realities To Respect`
4. `Reference Chip Lessons`
5. `Domain Source Registry`
6. `Domain Mutation Grammar`
7. `Domain Evaluator Design`
8. `Domain Suggestion Logic`
9. `Domain Packet Families`
10. `Domain Watchtower And Naming Contract`
11. `One Governing Flywheel`
12. `Autoloop Behavior`
13. `Benchmark Bridge And Promotion Policy`
14. `Real-World Validation Plan`
15. `Recursive Improvement Guardrails`
16. `Gap Analysis`
17. `Minimal Repo Scaffold`
18. `Implementation Sequence`
19. `Validation Plan`
20. `Acceptance Criteria`
21. `Rollback Conditions For Any New Extensions`

---

## Minimal Repo Scaffold

Assume the chip should be buildable from the standard Spark starter pattern.

At minimum, specify:

- `pyproject.toml`
- `spark-chip.json`
- `spark-researcher.project.json`
- `README.md`
- `src/<package>/__init__.py`
- `src/<package>/cli.py`

If the chip is beyond stage 0, also specify which additional docs or artifact roots it should include on day one.

Examples:

- source map doc
- packet schema doc
- benchmark bridge doc
- one-loop spec
- real-world eval doc
- approved-source file
- discovery seeds file

Do not require infrastructure that the chip does not yet honestly need.

---

## Validation Plan

The design is not complete until it defines how it will be validated.

At minimum include:

1. `chips validate` structural check
2. one clean `run` path
3. one clean `suggest` path
4. one clean `packets` path
5. one clean `watchtower` path
6. one `memory sync`
7. one `obsidian build`
8. one proving-ground pass equivalent to the checkloop discipline

Also define what the operator should inspect after validation:

- manifest validity
- hook exit behavior
- metric parse success
- packet generation
- memory-tier correctness
- working-memory truthfulness
- watchtower truthfulness
- queue separation
- benchmark vs heuristic separation

---

## Acceptance Criteria

Do not call the chip successful unless all of the following are true:

1. the manifest validates
2. all four hooks run cleanly
3. the evaluator returns parseable metrics
4. the chip emits at least one explicit benchmark or fixed-evaluator evidence document
5. the chip emits at least one doctrine or boundary document when promotion conditions are met
6. the chip emits at least one exploratory packet family
7. memory sync reflects the chip docs in the right tiers
8. working memory is current and state-shaped
9. Obsidian generates the domain pages
10. the domain pages separate grounded doctrine from exploratory probes
11. queue state remains outside stable config
12. the design states clearly what is benchmark-grounded vs heuristic
13. any gap beyond the current standard is explicitly documented
14. no new complexity is introduced without justification and rollback

---

## Success Condition

The final design should make it easy to build a `{DOMAIN_NAME}` chip that:

- feels native to Spark rather than bolted on
- uses the same base standards as startup and trading where those standards are truly portable
- extends the standard only where the new domain genuinely requires it
- keeps the operator's truth surfaces honest
- improves through bounded recursive loops instead of vague agent autonomy
- remains small enough to review and strong enough to matter

