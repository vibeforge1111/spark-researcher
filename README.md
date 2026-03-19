# Spark Researcher

Spark Researcher is a small, review-first research loop for local projects.

It combines three ideas:

- Karpathy-style autoresearch with fixed evaluation
- bounded Spark-style recursive improvement
- file-first memory, watchtower output, and transparent self-edit packets

The design target is simple: stay legible, keep the evaluator fixed, and preserve a visible artifact trail instead of hiding state in a heavier framework.

## What It Does

- runs declared project commands from one small JSON config
- evaluates candidates against a fixed metric and appends an immutable ledger
- exports local Markdown memory and Obsidian watchtower pages
- keeps self-editing proposal-first, with explicit human apply
- supports external domain chips without moving domain logic into the core repo
- supports advisory-backed model execution through lightweight command templates

## Core Rules

- fixed evaluator, mutable strategy
- one mutation, one hypothesis
- ledger first, narrative second
- self-edit never auto-applies
- mutable targets must be declared
- the system works in copied workspaces, not in-place

## Quick Start

```powershell
cd C:\Users\USER\Desktop\spark-researcher
python -m pip install -e .
spark-researcher run --command train
spark-researcher loop --command train
spark-researcher autoloop --command train
spark-researcher self-edit propose --prompt "simplify the trainer status output"
```

The bundled config targets [`examples/toy-project/`](examples/toy-project/README.md), so the core loop is runnable without extra setup.

## Documentation

Use [`docs/README.md`](docs/README.md) as the canonical map.

Recommended reading order:

1. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
2. [`docs/RULES.md`](docs/RULES.md)
3. [`docs/CHECKLOOP.md`](docs/CHECKLOOP.md)
4. the focused operator doc for the subsystem you are touching

High-signal operator docs:

- [`docs/AUTOLOOP.md`](docs/AUTOLOOP.md)
- [`docs/ADVISORY.md`](docs/ADVISORY.md)
- [`docs/MEMORY.md`](docs/MEMORY.md)
- [`docs/BELIEFS.md`](docs/BELIEFS.md)
- [`docs/INTENT.md`](docs/INTENT.md)
- [`docs/SELF_EDITING.md`](docs/SELF_EDITING.md)
- [`docs/CHIPS.md`](docs/CHIPS.md)

Repo and backend contracts:

- [`AGENTS.md`](AGENTS.md)
- [`docs/AGENT_BACKENDS.md`](docs/AGENT_BACKENDS.md)
- [`AUTORESEARCH.md`](AUTORESEARCH.md)

## Layout

- `src/spark_researcher/`: core runtime
- `docs/`: operator and design docs
- `examples/toy-project/`: runnable demo target
- `artifacts/`: generated ledger, traces, memory, self-edit packets, and related runtime output
- `obsidian-vault/`: generated watchtower view
- `.autoresearch/capsules/`: collective-ready exports
- `domain-chip-*`: external or sibling domain chips

## Boundaries

Spark is meant to become more useful, not more theatrical.

- keep domain intelligence in chips when it does not belong in the kernel
- keep durable memory local and file-first
- keep provider execution lightweight and wrapper-based
- keep self-editing reviewable and explicitly applied

See [`docs/README.md`](docs/README.md) for the organized doc structure and where each topic now lives.
