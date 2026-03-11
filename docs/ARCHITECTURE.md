# Architecture

Spark Researcher is intentionally small.

## Core Flow

1. Load `spark-researcher.project.json`.
2. Overlay generated candidates from `artifacts/frontier/queue.json` when present.
3. Copy the target project into a run workspace.
4. Apply one explicit mutation set.
5. Run one declared command.
6. Parse one fixed metric.
7. Append one immutable ledger row.
8. Emit lightweight trace artifacts for the run and related decisions.
9. Export memory docs and rebuild the Obsidian vault when needed.

## Layers

- `runner.py`: command execution, mutations, verdicts, ledger writes
- `failures.py`: concrete failure registry and surprise-priority scoring
- `tracing.py`: JSONL trace recorder for run, advisory, frontier, and self-edit flows
- `research.py`: one-pass bounded research retry that turns `research_needed` into dated web notes with lightweight source provenance plus one follow-up verifier pass
- `verifier.py`: bounded two-draft select-and-revise loop for advisory execution, aware of active surprise-priority failure surfaces and able to escalate time-sensitive misses into `research_needed`
- `trainers.py`: generic example-count watchers with bounded recompiles
- `candidates.py`: now uses recent surprising failures to bias repair-oriented suggestion ordering
- `trial_queue.py`: keeps generated frontier state out of the hand-authored project config
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

## Config Boundary

- `spark-researcher.project.json` is the stable project spec
- `artifacts/frontier/queue.json` is the generated runtime queue

This keeps the repo file-first and resumable without turning the main config into a residue log of every autoloop suggestion.
