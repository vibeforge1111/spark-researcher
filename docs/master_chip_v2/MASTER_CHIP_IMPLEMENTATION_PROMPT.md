# Master Chip Implementation Prompt

> Use this after the architect/operator phase, when the goal is to actually build the chip repo.
> Replace `{DOMAIN_NAME}`, `{DOMAIN_DISPLAY_NAME}`, `{PRIMARY_METRIC}`, `{CHIP_NAME}`, and `{PACKAGE_NAME}`.
> This prompt assumes the design should follow `docs/master_chip_v2/MASTER_CHIP_ARCHITECT_PROMPT_V2.md`.

---

Implement a Spark domain chip repo for `{DOMAIN_NAME}` called `{CHIP_NAME}` with Python package `{PACKAGE_NAME}`.

Your job is to build the smallest useful working chip that honors the approved domain design, fits the current Spark core contract, and leaves a reviewable diff.

Do not redesign the architecture from scratch.
Do not add hidden infrastructure.
Do not widen the chip contract unless the approved gap analysis explicitly requires it.

Build against the real core behavior in:

- `src/spark_researcher/chips.py`
- `src/spark_researcher/runner.py`
- `src/spark_researcher/candidates.py`
- `src/spark_researcher/memory.py`
- `src/spark_researcher/obsidian.py`
- `src/spark_researcher/chip_starter.py`

Use these chip repos as concrete implementation references:

- `../domain-chip-startup-yc`
- `../domain-chip-trading-crypto`

---

## Build Goal

Implement a chip that:

- passes `chips validate`
- exposes all 4 hooks
- produces parseable metrics
- emits packet documents with explicit kinds and tiers
- emits domain watchtower pages with stable paths
- keeps queue state separate from stable config
- keeps benchmark-grounded work separate from heuristic/exploratory work
- can survive one clean validation pass through `run`, `memory sync`, and `obsidian build`

Start from the smallest honest version.
If the domain does not yet have a true benchmark, implement an explicit deterministic scaffold and label it honestly.

---

## Required Files

Create or update at minimum:

- `pyproject.toml`
- `spark-chip.json`
- `spark-researcher.project.json`
- `README.md`
- `src/{PACKAGE_NAME}/__init__.py`
- `src/{PACKAGE_NAME}/cli.py`

Add only the extra docs and artifacts the design actually needs, such as:

- `docs/{DOMAIN_NAME}_SOURCE_MAP.md`
- `docs/{DOMAIN_NAME}_ONE_LOOP_SPEC.md`
- `docs/{DOMAIN_NAME}_BENCH_PROMOTION_BRIDGE.md`
- `docs/{DOMAIN_NAME}_REALWORLD_EVAL.md`
- `docs/research-ingest/approved-sources.json`
- `docs/research-ingest/discovery-seeds.json`

Do not add speculative directories.

---

## Manifest Requirements

Implement `spark-chip.json` using the real `spark-chip.v1` schema.

Required fields:

- `schema_version`
- `io_protocol`
- `chip_name`
- `domain`
- `version`
- `description`
- `capabilities`
- `commands`

If the domain uses frontier grammar, add:

- `frontier.enabled`
- `frontier.model`
- `frontier.web_search`
- `frontier.allowed_mutations`
- `frontier.open_mutation_fields`
- `frontier.field_patterns`
- `frontier.prompt_hints`
- `frontier.required_fields`

Do not use narrative placeholders in grammar fields.

---

## Project Config Requirements

Implement `spark-researcher.project.json` so it works with current core behavior.

Required areas:

- `project_name`
- `eval_metric`
- `eval_goal`
- `commands`
- `metrics`
- `candidate_trials`
- `chip`
- `memory`
- `self_edit`
- `guardrails`

The primary command should typically be:

- `research`
  - `kind: "chip-evaluate"`

Include at least:

- one global baseline candidate with empty mutations
- one or more seed candidates if the domain design already justifies them

Metrics must match what the `evaluate` hook prints or returns.

---

## Hook Implementation Requirements

Implement all four hooks in `src/{PACKAGE_NAME}/cli.py`.

### 1. `evaluate`

Read the hook envelope from `--input`.
Write the response JSON to `--output`.

Return:

- `returncode`
- `stdout`
- `stderr`
- `metrics`
- `result`

The `result` object should include:

- `claim`
- `verdict`
- `mechanism`
- `boundary`
- `recommended_next_step`
- `evidence_lane`

Also include when applicable:

- `comparison_class`
- benchmark bridge fields
- domain-specific promotion details
- `lesson`
- `next_probe`

Use explicit promotion gates.
Do not bury the decision logic in vague prose.

### 2. `suggest`

Use:

- `ledger_rows`
- `failure_priorities`
- `candidate_trials`
- domain doctrine gaps
- contradiction pressure
- benchmark escalation needs

Return:

- `baseline_metric`
- `reasons`
- `suggestions`

Each suggestion must include:

- `candidate_id`
- `candidate_summary`
- `hypothesis`
- `mutations`

Suggestions must be bounded and real.

### 3. `packets`

Return:

- `documents`

Each document should include:

- `kind`
- `slug`
- `title`
- `content`

Include `memory_tier` if needed.

At minimum implement explicit families for:

- benchmark evidence
- grounded doctrine
- grounded boundary
- exploratory frontier

Do not rely on raw runs/outcomes to do this job.

### 4. `watchtower`

Return:

- `pages`

Each page must include:

- `path`
- `content`

Use stable relative vault paths under:

- `07-Domains/{DOMAIN_DISPLAY_NAME}/`

Do not write directly outside the returned pages contract.

---

## Evaluator Rules

The evaluator must be honest about domain maturity.

If a real benchmark exists:

- use a benchmark-grounded comparison lane
- emit `comparison_class: benchmark_grounded`
- route promotion through explicit bridge semantics

If only a heuristic scaffold exists:

- label it as heuristic or deterministic scaffold
- emit `comparison_class: heuristic_frontier` or the approved equivalent
- do not over-promote its outputs as settled doctrine

The evaluator should clearly expose:

- the baseline
- the winning mechanism
- the active boundary
- why the candidate passed, deferred, or failed
- the next required evidence step

---

## Packet and Memory Rules

Map packet families cleanly into memory tiers.

Use the current tier model:

- `grounded_doctrine`
- `grounded_boundary`
- `benchmark_evidence`
- `exploratory_frontier`
- `research_grounded`
- `state_snapshot`
- `raw_outcome`
- `raw_run`

The chip should emit promoted domain docs, not raw residue.

If the design includes research packets, ensure the implementation keeps these distinct:

- source notes
- research packets
- doctrine candidates
- promoted doctrine
- contradiction/boundary docs

Do not collapse all domain artifacts into one generic markdown family.

---

## Watchtower Rules

Implement at least these pages:

- `07-Domains/{DOMAIN_DISPLAY_NAME}/Home.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Doctrine.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Boundaries.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Benchmark Evidence.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Frontier Probes.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Why It Lost.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Coverage Map.md`
- `07-Domains/{DOMAIN_DISPLAY_NAME}/Real-World Validation.md`

Each page should answer a clear operator question.

Make sure the watchtower helps an operator see:

- current trusted doctrine
- current boundaries
- benchmark-backed evidence
- active frontier probes
- recent losing candidates and why they lost
- coverage gaps
- contradiction pressure
- real-world validation readiness

The watchtower must stay aligned with:

- memory output
- ledger output
- queue state
- actual packet documents

If the watchtower and runtime artifacts disagree, fix the implementation.

---

## Autoloop and Flywheel Rules

Implement the chip so it works naturally with Spark autoloop.

Required expectations:

- generated candidates live in `artifacts/frontier/queue.json`
- suggestions remain inside the declared mutation grammar
- continuous mode remains bounded
- each pass should make the next bottleneck legible

The chip should support one governing loop pattern with explicit routing between:

- research frontier
- trial frontier
- ranking/review stages
- promotion stages
- real-world validation stages

Do not implement disconnected side loops unless the approved design explicitly requires them.

---

## Validation Sequence

After implementation, validate in this order:

1. `python -m spark_researcher.cli chips validate`
2. one `run` using the chip command
3. one `candidates suggest`
4. one `memory sync`
5. one `obsidian build`
6. inspect packet status
7. inspect generated domain pages

The implementation is not complete until you can verify:

- manifest validity
- hook execution
- metric parsing
- packet generation
- memory-tier correctness
- working-memory truthfulness
- watchtower truthfulness
- stable config / generated queue separation
- benchmark / heuristic separation

---

## Acceptance Criteria

Only consider the implementation complete if:

1. `chips validate` passes
2. all 4 hooks run without error
3. the evaluator returns parseable metrics
4. the chip emits at least one explicit benchmark or fixed-evaluator evidence doc
5. the chip emits at least one doctrine or boundary doc when conditions are met
6. the chip emits at least one exploratory frontier doc
7. memory sync indexes the chip docs in the right tiers
8. Obsidian builds the domain pages
9. the domain pages separate grounded doctrine from exploratory work
10. queue state remains outside stable config
11. the implementation does not add unjustified complexity

---

## Delivery Format

When implementing, report back with:

1. `What Was Built`
2. `What Was Deferred`
3. `How The Hooks Behave`
4. `How The Watchtower Is Structured`
5. `Validation Results`
6. `Known Gaps Or Honest Scaffolds`

Success condition:

The result should be a working Spark chip repo for `{DOMAIN_NAME}` that is small, honest, standardized, and ready for iterative strengthening without breaking the base system.
