---
schema_version: 1
repo: vibeforge1111/spark-researcher
name: Spark Researcher
domain: universal
area: lightweight-autoresearch
objective: run bounded research loops with fixed evaluation, simple memory, and transparent self-improvement
metric_name: primary_metric
metric_direction: lower
default_branch: main
mutable_targets:
  - src/spark_researcher
  - docs
  - README.md
  - pyproject.toml
capsule_dir: .autoresearch/capsules
adoption_policy: review
absorb_merge_policy: human_review
run_command: spark-researcher loop --command train
publish_command: spark-researcher collective publish
platforms:
  - Windows
  - Python
safety_boundaries:
  - do not auto-apply self edits
  - do not write outside declared mutable targets
  - keep the counted codebase below the explicit line budget
  - keep the ledger and generated packets visible to the owner
  - external coding agents must follow the repo contract in AGENTS.md
---

# AUTORESEARCH

Spark Researcher is a lightweight, review-first research system.

It keeps the core loop small:

- config declares commands, metrics, candidates, trainers, and mutable targets
- generated autoloop suggestions live in `artifacts/frontier/queue.json` instead of mutating the base config
- runs execute in copied workspaces
- results append to an immutable ledger
- memory exports derive from existing artifacts
- self edits remain proposals until the owner applies them

The collective bridge is intentionally thin. It writes portable capsule files from local evidence instead of creating another state system.
