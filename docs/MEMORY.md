# Memory

Spark Researcher memory stays lightweight on purpose.

## Policy

- `local` is the default backend
- `ruvector` is optional
- local Markdown memory remains the source of truth
- RuVector is only a delegated external search surface

## Local Memory

The local backend exports compact Markdown documents for:

- runs
- beliefs
- self-edit packets
- outcomes grouped from the ledger

## RuVector

RuVector is not embedded as Spark's internal database.

Spark only delegates `brain search ... --json` to the RuVector CLI when you explicitly choose the `ruvector` backend.

## Commands

```powershell
spark-researcher memory backend-policy
spark-researcher memory backend-policy --backend ruvector
spark-researcher memory sync
spark-researcher memory status
spark-researcher memory status --backend ruvector
spark-researcher memory search "learning rate"
spark-researcher memory search "anchor variance" --backend ruvector
```
