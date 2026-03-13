# Master Chip Operator Prompt

> Use this when you want a strong but shorter prompt for planning a new domain chip.
> Replace `{DOMAIN_NAME}`, `{DOMAIN_DISPLAY_NAME}`, and `{PRIMARY_METRIC}`.
> This prompt is the compressed operator version of `docs/master_chip_v2/MASTER_CHIP_ARCHITECT_PROMPT_V2.md`.

---

Design a Spark domain chip for `{DOMAIN_NAME}`.

Your job is to create a portable, benchmark-first, recursively improving domain chip that fits the real Spark chip/runtime contract and transfers the strongest proven lessons from:

- Spark core chip behavior
- `domain-chip-startup-yc`
- `domain-chip-trading-crypto`

Do not design from intuition alone. Read the core chip docs, core chip implementation files, and the two reference chips first. Extract:

- what is portable
- what is domain-specific
- what the code already enforces
- what the docs describe but code does not yet fully enforce
- what gaps `{DOMAIN_NAME}` introduces

Preserve the base contract:

- Spark owns loop execution, ledger, queue, memory index, vault generation, and self-edit policy.
- The chip owns domain scoring, suggestions, packets, watchtower pages, source maps, benchmark bridge semantics, and real-world validation surfaces.
- Use only the standard hooks: `evaluate`, `suggest`, `packets`, `watchtower`.

Design against the real implementation:

- manifest schema: `spark-chip.v1`
- IO protocol: `spark-hook-io.v1`
- hooks are invoked via `--input <json> --output <json>`
- queue state lives in `artifacts/frontier/queue.json`
- watchtower pages are emitted by the chip but rendered into the core vault
- working memory should refresh from benchmark-grounded runs when appropriate

The design must preserve these standards unless a gap is explicitly justified:

- separate evidence lanes:
  - `research_grounded`
  - `benchmark_grounded`
  - `realworld_validated`
  - `exploratory_frontier`
- separate memory tiers:
  - `grounded_doctrine`
  - `grounded_boundary`
  - `benchmark_evidence`
  - `exploratory_frontier`
  - `state_snapshot`
- separate comparison classes:
  - `benchmark_grounded`
  - `heuristic_frontier`
- stable config separate from generated queue
- watchtower is not source of truth
- raw residue must not become doctrine

You must design:

1. the domain mission
2. the source registry
3. the mutation grammar
4. the evaluator and promotion logic
5. the suggestion logic
6. the packet families
7. the watchtower and naming contract
8. the one governing flywheel
9. the autoloop behavior
10. the benchmark bridge
11. the real-world validation surface
12. the recursive-improvement guardrails

The flywheel must use one governing loop with conditional stages:

1. refresh research state
2. run packet quality gate
3. classify the next bottleneck
4. route to the right frontier or review path
5. update memory
6. update watchtower
7. decide whether promotion or real-world validation is justified

Use explicit bottleneck labels:

- `knowledge_gap`
- `trial_gap`
- `ranking_gap`
- `promotion_gap`
- `coverage_gap`
- `contradiction_gap`

Do not:

- use trial frontier to compensate for source ignorance
- use research frontier when the true issue is benchmark ambiguity
- invent a fifth hook silently
- merge grounded and exploratory truth surfaces

The watchtower must use stable naming under:

- `07-Domains/{DOMAIN_DISPLAY_NAME}/`

Required base pages:

- `Home.md`
- `Doctrine.md`
- `Boundaries.md`
- `Benchmark Evidence.md`
- `Frontier Probes.md`
- `Why It Lost.md`
- `Coverage Map.md`
- `Real-World Validation.md`

The operator must be able to see:

- what is currently trusted
- what is only exploratory
- what changed recently
- what the next best probe is
- where evidence is weak
- why candidates lost
- what contradictions are active
- what the queue contains

You must run explicit gap analysis for `{DOMAIN_NAME}`.

For every true gap, output:

- `gap_name`
- `why_current_standard_is_insufficient`
- `what_the_domain_needs`
- `smallest_viable_extension`
- `chip_local_or_portable`
- `rollback_condition`

Output format:

1. `Portable Standards Inherited`
2. `Core Runtime Realities`
3. `Reference Chip Lessons`
4. `Domain Design`
5. `Flywheel`
6. `Watchtower`
7. `Gap Analysis`
8. `Implementation Sequence`
9. `Validation Plan`
10. `Acceptance Criteria`

Success condition:

The design should make `{DOMAIN_NAME}` feel like a true Spark chip, not a one-off framework, while still surfacing any genuinely new standards the domain requires.
