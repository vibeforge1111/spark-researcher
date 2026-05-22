# Documentation Map

This repo now uses a simple documentation split:

- [`README.md`](../README.md): landing page, quick start, and repo shape
- `docs/`: operator and design docs
- domain chip repos: domain-specific specs and operating notes

Keep detailed procedures in `docs/`. Keep [`README.md`](../README.md) short and oriented around entry, not duplication.

## Installation / Getting Started

To set up the project locally:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/spark-swarm.git
   cd spark-swarm
   ```

2. Install dependencies (if applicable):
   ```bash
   pip install -r requirements.txt
   ```

3. Run the initial setup:
   ```bash
   python setup.py
   ```

4. Verify the installation:
   ```bash
   python -m pytest tests/
   ```

For more details, see the [`README.md`](../README.md) landing page.

## Start Here

Read these first if you are new to the repo:

1. [`README.md`](../README.md)
2. [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
3. [`docs/AUTOLOOP.md`](AUTOLOOP.md)
4. [`docs/MEMORY.md`](MEMORY.md)
5. [`examples/toy-project/README.md`](../examples/toy-project/README.md)

## Publication Tiers

Use [`docs/PUBLICATION_MAP.md`](PUBLICATION_MAP.md) when deciding what belongs on the public front door versus what should stay as reference or archive.

Current rule:

- public docs should explain the core system cleanly
- reference docs should remain available for agents and advanced operators
- archive docs should stay in the repo for now so links and agent understanding do not regress

## Core Docs

- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md): core runtime model and Spark Swarm boundary
- [`docs/RULES.md`](RULES.md): non-negotiable system rules
- [`docs/AUTOLOOP.md`](AUTOLOOP.md): bounded loop behavior and limits
- [`docs/MEMORY.md`](MEMORY.md): memory policy and promotion semantics
- [`docs/OBSIDIAN.md`](OBSIDIAN.md): watchtower output and vault expectations
- [`docs/SELF_EDITING.md`](SELF_EDITING.md): propose/apply flow for workspace-only self edits
- [`docs/ADVISORY.md`](ADVISORY.md): packet-backed model path, verifier loop, and provider execution
- [`docs/AGENT_BACKENDS.md`](AGENT_BACKENDS.md): backend contract for external coding agents
- [`docs/CHIPS.md`](CHIPS.md): chip contract and ownership boundary
- [`docs/CHIP_AUTHORING.md`](CHIP_AUTHORING.md): how to design and iterate on chips with an LLM
- [`docs/CHIP_SYSTEMS.md`](CHIP_SYSTEMS.md): chooser for `v1` vs `v2`
- [`docs/CHIP_VALIDATION.md`](CHIP_VALIDATION.md): standard chip validation path
- [`docs/PRESETS.md`](PRESETS.md): scaffold presets

## Spark Swarm Integration

Spark Researcher now also serves as the runtime core for Spark Swarm specialization paths.

Use these docs first for that integration:

- [`README.md`](../README.md): high-level runtime-core role
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md): specialization-path runtime contract and kernel boundary
- the path-owned repo docs in the relevant `specialization-path-*` repo for path-specific templates, guidance, and benchmark defaults

For this integration, treat [`README.md`](../README.md) and [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) as the authoritative docs.
Treat generated local files like `AUTORESEARCH.md` and `PROJECT.md` as operational residue, not architecture doctrine.

## Reference Docs

- [`docs/CHECKLOOP.md`](CHECKLOOP.md): local proving-ground flow before trusting a change
- [`docs/RELIABILITY_TEST_PLAN.md`](RELIABILITY_TEST_PLAN.md): subsystem-by-subsystem reliability audit
- [`docs/BELIEFS.md`](BELIEFS.md): how durable and provisional beliefs are built
- [`docs/INTENT.md`](INTENT.md): persistent mission settings for projects and chips
- [`docs/CHIP_REGISTRY.md`](CHIP_REGISTRY.md): known chips
- [`docs/CHIP_MEMORY_ROLLOUT.md`](CHIP_MEMORY_ROLLOUT.md): chip memory upgrade path
- [`docs/CHIP_INTELLIGENCE_CONTRACT.md`](CHIP_INTELLIGENCE_CONTRACT.md): reusable chip intelligence contract
- [`docs/CHIP_INTELLIGENCE_ROLLOUT.md`](CHIP_INTELLIGENCE_ROLLOUT.md): rollout sequence for richer chip intelligence
- [`docs/CHIP_ONE_LOOP_FLYWHEEL.md`](CHIP_ONE_LOOP_FLYWHEEL.md): reusable richer-chip loop pattern
- [`docs/CHIP_RESEARCH_PACKET_SCHEMA.md`](CHIP_RESEARCH_PACKET_SCHEMA.md): research packet format
- [`docs/CHIP_TAGGING_RULESET.md`](CHIP_TAGGING_RULESET.md): contradiction and factor tagging rules
- [`docs/CHIP_RESEARCH_QUALITY_RULESET.md`](CHIP_RESEARCH_QUALITY_RULESET.md): research quality bar
- [`docs/CHIP_DSPY_METHOD.md`](CHIP_DSPY_METHOD.md): narrow optimizer method
- [`docs/CHIP_BENCHMARK_BRIDGE_GUIDE.md`](CHIP_BENCHMARK_BRIDGE_GUIDE.md): benchmark promotion bridge
- [`docs/STARTUP_BENCH_PROMOTION_BRIDGE.md`](STARTUP_BENCH_PROMOTION_BRIDGE.md): startup-chip-specific benchmark bridge
- [`docs/MASTER_CHIP_ARCHITECT_PROMPT.md`](MASTER_CHIP_ARCHITECT_PROMPT.md): `v1` chip design prompt
- [`docs/master_chip_v2/README.md`](master_chip_v2/README.md): `v2` chip prompt stack

## Archive And Deep Background

Use [`docs/archive/README.md`](archive/README.md) for archived deep-background docs, internal examples, and backlog material that should stay available without remaining on the public front door.

## Root-Level Repo Docs

- [`AUTORESEARCH.md`](../AUTORESEARCH.md): compact machine-readable repo capsule plus summary
- [`AGENTS.md`](../AGENTS.md): contract for external coding agents working in this repo
- `PROJECT.md`: optional local project snapshot when present; not part of the published repo surface

## Domain Repo Docs

These stay with the external chip repos and should not be duplicated into the core docs unless the content becomes cross-domain policy.

## Consolidation Rule

When adding or revising docs:

- update [`README.md`](../README.md) only if the repo entry story changes
- update [`docs/README.md`](README.md) when a new durable document becomes part of the operator surface
- keep detailed procedures in one focused document instead of copying sections into [`README.md`](../README.md)
- link across docs instead of restating the same command list or policy twice

For publishing:

- keep the public front door aligned with [`docs/PUBLICATION_MAP.md`](PUBLICATION_MAP.md)
- do not remove reference docs that agents still need to understand Spark Swarm, chips, memory, Obsidian, or self-edit boundaries