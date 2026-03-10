# Domain Chips

Domain chips keep `spark-researcher` small.

## Contract

A chip is an external repo with:

- `spark-chip.json`
- one or more command hooks
- its own source code and tests

Spark calls chip hooks with `--input <json> --output <json>`.

Supported hooks:

- `evaluate`: domain-specific candidate evaluation
- `suggest`: domain-specific next-candidate generation
- `packets`: domain-specific memory documents
- `watchtower`: domain-specific Obsidian pages

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
- memory index
- vault root
- self-edit policy
- git promotion

The chip owns:

- domain scoring
- domain suggestions
- domain packets
- domain watchtower pages

This keeps the kernel portable while letting domains evolve in separate repos.
