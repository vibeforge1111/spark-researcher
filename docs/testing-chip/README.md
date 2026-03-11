# Spark Testing Chip

This chip runs deterministic reliability probes against the current `spark-researcher` core through the normal chip bridge.

## What It Checks

- durable belief preference
- advisory downgrade on provisional-only memory
- adapter brief packet-stability injection
- trace to Obsidian packet-selection wiring
- research URL/domain provenance helpers

## How To Use

Temporarily point the current project at this chip:

```json
{
  "chip": {
    "path": "docs/testing-chip",
    "manifest": "spark-chip.json"
  }
}
```

Then run:

```powershell
spark-researcher chips validate
spark-researcher chips status
```

The chip is intentionally small. It is for core reliability checks, not domain scoring.
