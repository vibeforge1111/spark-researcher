# Beliefs

Beliefs are compact packets built from evidence that already exists.

## Sources

- improved run records from the immutable ledger
- approved self-edit reviews with lineage and rollback conditions

## Rule

Beliefs compress lessons. They do not replace the raw ledger, review packet, or source diff.

Run beliefs now carry a small status:

- `durable`
  - repeated support with no active contradiction on shared mutation values
- `provisional`
  - still useful locally, but either replication is thin or another promoted lesson disagrees on the same command surface

Spark also writes `docs/beliefs/CONTRADICTIONS.md` so competing lessons are visible instead of silently living side by side.

## Command

```powershell
spark-researcher beliefs build
```

