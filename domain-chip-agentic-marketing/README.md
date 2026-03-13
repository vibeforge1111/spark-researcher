# domain-chip-agentic-marketing

`domain-chip-agentic-marketing` is a Spark domain chip for designing and iterating on startup marketing and distribution systems that are run through automations, agents, LLMs, and open-source tooling.

This chip was shaped from the `docs/master_chip_v2` workflow in the parent Spark workspace. It keeps the Spark core contract intact and pushes the domain-specific logic into a portable repo that can score, suggest, packetize, and render watchtower pages for a startup growth operating system.

## What This Chip Models

The chip does not yet call vendor APIs directly.
It gives you an honest benchmark scaffold for comparing candidate growth systems across:

- motion: founder-led content, programmatic SEO, signal-based outbound, community embeds, partner distribution
- channel: X, LinkedIn, SEO, email, communities, partner ecosystems
- offer: teardown, comparison page, template pack, benchmark report, ROI calculator
- orchestration: `n8n`, `Mautic`, or a hybrid agent stack
- feedback closure: analytics, CRM, surveys, support inbox, and conversion surfaces

The goal is to make startup distribution feel less like ad hoc hustle and more like a measurable operating system:

1. research and observe demand
2. package a sharp offer
3. generate and distribute assets
4. capture and route demand
5. score what actually closed the loop
6. promote only what survives both benchmark and real-world scrutiny

## Suggested Open-Source Stack

The methodology documents in `docs/` are grounded around a practical stack:

- `n8n` for workflow orchestration and agent handoffs
- `PostHog` for product, web, and experiment analytics
- `Twenty` for CRM and account memory
- `Mautic` for lifecycle campaigns and outbound automation
- `Chatwoot` for inbound support and human-in-the-loop conversations
- `Typebot` for conversational capture flows
- `Formbricks` for voice-of-customer and survey feedback
- `Dub` for link routing and attribution

You can swap tools, but the system needs equivalents for orchestration, analytics, CRM, capture, support, and feedback.

## Folder Location

```text
C:\Users\USER\Desktop\spark-researcher\domain-chip-agentic-marketing
```

## Quick Start

```powershell
cd C:\Users\USER\Desktop\spark-researcher\domain-chip-agentic-marketing
python -m pip install -e .
$env:PYTHONPATH='C:\Users\USER\Desktop\spark-researcher\src;src'
python -m spark_researcher.cli chips validate --config spark-researcher.project.json
python -m spark_researcher.cli run --config spark-researcher.project.json --command research
python -m spark_researcher.cli candidates suggest --config spark-researcher.project.json --command research
python -m spark_researcher.cli memory sync --config spark-researcher.project.json
python -m spark_researcher.cli obsidian build --config spark-researcher.project.json
```

## Domain Docs

- `docs/AGENTIC_MARKETING_ONE_LOOP_SPEC.md`
- `docs/AGENTIC_MARKETING_BENCH_PROMOTION_BRIDGE.md`
- `docs/AGENTIC_MARKETING_REALWORLD_EVAL.md`
- `docs/AGENTIC_MARKETING_SOURCE_MAP.md`
- `docs/research-ingest/approved-sources.json`
- `docs/research-ingest/discovery-seeds.json`

## Standard

This chip keeps four truth surfaces separate:

- `research_grounded`
- `benchmark_grounded`
- `realworld_validated`
- `exploratory_frontier`

Do not treat generated watchtower pages or raw run history as doctrine.
Only promote a motion-channel-offer system after it clears explicit benchmark gates and then survives a live pilot with real attribution.
