# Architecture

Spark Researcher is intentionally small.

## Core Flow

1. Load `spark-researcher.project.json`.
2. Copy the target project into a run workspace.
3. Apply one explicit mutation set.
4. Run one declared command.
5. Parse one fixed metric.
6. Append one immutable ledger row.
7. Export memory docs and rebuild the Obsidian vault when needed.

## Layers

- `runner.py`: command execution, mutations, verdicts, ledger writes
- `trainers.py`: generic example-count watchers with bounded recompiles
- `memory.py`: Markdown memory export and lexical search
- `obsidian.py`: watchtower generation
- `collective.py`: portable capsule export
- `self_edit.py`: workspace-only self-edit proposals with explicit apply
- `presets.py`: multi-domain scaffolding without adding framework weight
- `chips.py`: external domain-chip bridge over a tiny manifest contract

## Non-Goals

- no hidden background daemon
- no database requirement
- no framework-heavy plugin system
- no auto-merge of self edits
- no domain logic hardcoded into the core when a chip can hold it
