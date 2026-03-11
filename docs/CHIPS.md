# Domain Chips

Domain chips keep `spark-researcher` small.

## Contract

A chip is an external repo with:

- `spark-chip.json`
- one or more command hooks
- its own source code and tests

The manifest now follows `spark-chip.v1` with `spark-hook-io.v1` hook I/O.

Spark calls chip hooks with `--input <json> --output <json>`.

Supported hooks:

- `evaluate`: domain-specific candidate evaluation
- `suggest`: domain-specific next-candidate generation
- `packets`: domain-specific memory documents
- `watchtower`: domain-specific Obsidian pages

Validate a configured chip with:

```powershell
spark-researcher chips validate
```

The canonical schema lives at `schemas/spark-chip.schema.json`.

The standard runtime validation flow for any chip is documented in `docs/CHIP_VALIDATION.md`.

Create a new chip scaffold with:

```powershell
spark-researcher chips init --path C:\work\domain-chip-foo --chip-name domain-chip-foo --domain foo --metric-name foo_score --goal maximize
```

The starter writes only the minimum valid repo:

- `pyproject.toml`
- `spark-chip.json`
- `spark-researcher.project.json`
- `README.md`
- `src/<package>/__init__.py`
- `src/<package>/cli.py`

## Config

Point a Spark project at a chip with:

```json
{
  "chip": {
    "path": "../domain-chip-startup-yc",
    "manifest": "spark-chip.json"
  }
}
```

Use `command.kind = "chip-evaluate"` when the command should be delegated to the chip's `evaluate` hook.

## Rule

Spark owns:

- loop execution
- ledger
- generated frontier queue
- memory index
- vault root
- self-edit policy
- git promotion

The chip owns:

- domain scoring
- domain suggestions
- domain packets
- domain watchtower pages

Suggestion hooks should keep expanding the frontier from evidence, and Spark can fall back to an LLM frontier constrained by manifest grammar:

- test stronger combinations from winners
- run transfer checks on strong primitives
- run contradiction probes on promoted doctrines

The manifest can now keep field names fixed while relaxing values:

- `allowed_mutations` provides the seed grammar
- `open_mutation_fields` marks which fields may accept new LLM-proposed values
- `field_patterns` keeps those new values structurally valid
- `prompt_hints` lets the chip steer LLM exploration without hardcoding new frontiers every time

Do this through the existing `suggest` hook rather than inventing a new orchestration surface. If you want long-running exploration, use `autoloop --continuous`; it repeats bounded passes, not an unconstrained daemon.

Generated chip suggestions now land in `artifacts/frontier/queue.json`. Keep `spark-researcher.project.json` for stable seed candidates and promote queue items back into the main config only when you want them to become part of the standing project spec.

This keeps the kernel portable while letting domains evolve in separate repos.

## Registry

Current known chips are listed in `docs/CHIP_REGISTRY.md`.
