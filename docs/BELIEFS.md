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

Packet selection now prefers `durable` belief docs over `provisional` ones when both match the same task, but provisional beliefs still remain searchable as local evidence.

Other packet kinds can still appear in search when they are the best local match, but they do not inherit belief status. In particular, `research_outcome` entries are bounded evidence-only surfaces from the `research` command, not promoted beliefs.

Core beliefs also skip chip-owned benchmark rows when those rows already belong to a chip-specific evidence system. This keeps generic `docs/beliefs` from preserving stale benchmark anchors as if they were the main truth surface for a richer chip.

## Command

```powershell
spark-researcher beliefs build
```

