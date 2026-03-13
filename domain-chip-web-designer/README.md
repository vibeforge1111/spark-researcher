# domain-chip-web-designer

`domain-chip-web-designer` is a private-repo-ready Spark domain chip for building award-level websites and dashboards without losing UI/UX rigor.

It is designed from the parent workspace's `docs/master_chip_v2` prompt stack and keeps the Spark core contract intact while pushing domain logic into a separate folder that can later live as its own private repo.

## What This Chip Optimizes

This chip is meant to learn from:

- award and inspiration ecosystems such as Awwwards, FWA, CSS Design Awards, SiteInspire, Godly, and Land-book
- durable UI/UX foundations such as WCAG 2.2, Nielsen Norman Group heuristics, Apple Human Interface Guidelines, and Material Design
- the tension between visual craft and product usability instead of pretending they are the same thing

The operating goal is not "make pretty websites."
It is to generate web systems that score well across:

- award signal
- UX clarity
- interaction craft
- conversion clarity
- accessibility safety

That balance is what keeps the chip honest while it recursively improves.

## Domain Model

The current mutation space covers:

- site type
- design direction
- narrative model
- interaction model
- proof surface
- conversion strategy
- accessibility mode

The chip is strong when it can produce a site direction that feels premium, memorable, and current while still respecting task flow, conversion logic, motion restraint, and accessibility guardrails.

## Folder Location

```text
C:\Users\USER\Desktop\spark-researcher\domain-chip-web-designer
```

## Quick Start

```powershell
cd C:\Users\USER\Desktop\spark-researcher\domain-chip-web-designer
python -m pip install -e .
$env:PYTHONPATH='C:\Users\USER\Desktop\spark-researcher\src;src'
python -m spark_researcher.cli chips validate --config spark-researcher.project.json
python -m spark_researcher.cli run --config spark-researcher.project.json --command research
python -m spark_researcher.cli candidates suggest --config spark-researcher.project.json --command research
python -m spark_researcher.cli memory sync --config spark-researcher.project.json
python -m spark_researcher.cli obsidian build --config spark-researcher.project.json
```

## Domain Docs

- `docs/PROMPT_STACK_INVOCATION.md`
- `docs/WEB_DESIGN_ONE_LOOP_SPEC.md`
- `docs/WEB_DESIGN_BENCH_PROMOTION_BRIDGE.md`
- `docs/WEB_DESIGN_REALWORLD_EVAL.md`
- `docs/WEB_DESIGN_SOURCE_MAP.md`
- `docs/research-ingest/approved-sources.json`
- `docs/research-ingest/discovery-seeds.json`
- `docs/recursion/loop-policy.json`

## Standard

This chip keeps four evidence classes separate:

- `research_grounded`
- `benchmark_grounded`
- `realworld_validated`
- `exploratory_frontier`

An Awwwards-style look is not enough for promotion.
Do not elevate a design direction into doctrine unless it survives both benchmark scoring and real-world UX checks.
