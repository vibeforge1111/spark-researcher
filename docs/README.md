# Documentation Map

This repo now uses a simple documentation split:

- [`README.md`](../README.md): landing page, quick start, and repo shape
- `docs/`: operator and design docs
- domain chip repos: domain-specific specs and operating notes

Keep detailed procedures in `docs/`. Keep [`README.md`](../README.md) short and oriented around entry, not duplication.

## Start Here

Read these first if you are new to the repo:

1. [`README.md`](../README.md)
2. [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
3. [`docs/RULES.md`](RULES.md)
4. [`docs/CHECKLOOP.md`](CHECKLOOP.md)

## Core Operator Docs

- [`docs/AUTOLOOP.md`](AUTOLOOP.md): bounded autonomous loop behavior and limits
- [`docs/ADVISORY.md`](ADVISORY.md): packet-backed model path, verifier loop, and provider execution
- [`docs/MEMORY.md`](MEMORY.md): local memory policy, promotion gate, and retrieval backend boundary
- [`docs/BELIEFS.md`](BELIEFS.md): how durable and provisional beliefs are built
- [`docs/INTENT.md`](INTENT.md): persistent mission settings for projects and chips
- [`docs/SELF_EDITING.md`](SELF_EDITING.md): propose/apply flow for workspace-only self edits
- [`docs/AGENT_BACKENDS.md`](AGENT_BACKENDS.md): backend contract for external coding agents
- [`docs/OBSIDIAN.md`](OBSIDIAN.md): watchtower output and vault expectations
- [`docs/PRESETS.md`](PRESETS.md): scaffold presets

## Spark Swarm Integration

Spark Researcher now also serves as the runtime core for Spark Swarm specialization paths.

Use these docs first for that integration:

- [`README.md`](../README.md): high-level runtime-core role
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md): specialization-path runtime contract and kernel boundary
- the path-owned repo docs in the relevant `specialization-path-*` repo for path-specific templates, guidance, and benchmark defaults

For this integration, treat [`README.md`](../README.md) and [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) as the authoritative docs.
Treat generated local files like `AUTORESEARCH.md` and `PROJECT.md` as operational residue, not architecture doctrine.

## Domain Chip Docs

- [`docs/CHIPS.md`](CHIPS.md): chip contract, ownership boundary, and scaffold flow
- [`docs/CHIP_VALIDATION.md`](CHIP_VALIDATION.md): standard chip validation path
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
- [`docs/EXTERNAL_CHIP_TASKS.md`](EXTERNAL_CHIP_TASKS.md): external chip task surfaces

## Reliability And Review

- [`docs/CHECKLOOP.md`](CHECKLOOP.md): local proving-ground flow before trusting a change
- [`docs/RELIABILITY_TEST_PLAN.md`](RELIABILITY_TEST_PLAN.md): subsystem-by-subsystem reliability audit
- [`docs/ADVISORY.md`](ADVISORY.md): verifier and research retry boundaries
- [`docs/SELF_EDITING.md`](SELF_EDITING.md): self-edit review and apply boundaries

## Strategy And Deep Dives

- [`docs/AI_LAB_MAP.md`](AI_LAB_MAP.md): how Spark maps to AI-lab style practice
- [`docs/FRONTIER_LAB_BENCHMARKING_BOOK.md`](FRONTIER_LAB_BENCHMARKING_BOOK.md): benchmark framing and research doctrine
- [`docs/CHIP_ECOSYSTEM_HARDENING_PLAN.md`](CHIP_ECOSYSTEM_HARDENING_PLAN.md): chip ecosystem hardening backlog
- [`docs/CHIP_REMEDIATION_PROMPTS.md`](CHIP_REMEDIATION_PROMPTS.md): remediation prompt library
- [`docs/book-of-ai-intelligence/README.md`](book-of-ai-intelligence/README.md): book-length playbook
- [`docs/master_chip_v2/README.md`](master_chip_v2/README.md): master-chip prompt pack

## Root-Level Repo Docs

- [`AUTORESEARCH.md`](../AUTORESEARCH.md): compact machine-readable repo capsule plus summary
- [`AGENTS.md`](../AGENTS.md): contract for external coding agents working in this repo
- [`PROJECT.md`](../PROJECT.md): current project intelligence snapshot

## Domain Repo Docs

These stay with the chip repos and should not be duplicated into the core docs unless the content becomes cross-domain policy:

- `domain-chip-vibe-incubator/docs/`
- `domain-chip-trading-crypto-private/docs/`

## Consolidation Rule

When adding or revising docs:

- update [`README.md`](../README.md) only if the repo entry story changes
- update [`docs/README.md`](README.md) when a new durable document becomes part of the operator surface
- keep detailed procedures in one focused document instead of copying sections into [`README.md`](../README.md)
- link across docs instead of restating the same command list or policy twice
