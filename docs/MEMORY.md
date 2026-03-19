# Memory

Spark Researcher memory stays lightweight on purpose.

## Policy

- `local` is the default backend
- `ruvector` is the recommended retrieval upgrade once the corpus grows
- local Markdown memory is the canonical source of truth
- Spark falls back to local search when RuVector is unavailable in the current shell
- beliefs are promoted through a keepability gate instead of promoting every improved run

## Local Memory

The local backend exports compact Markdown documents for:

- runs
- beliefs
- self-edit packets
- outcomes grouped from the ledger
- working memory for the current focus
- episode memory for recent bounded lessons such as research retries

## Promotion Gate

Run beliefs are now promoted more selectively.

Spark promotes a run-derived belief only when one of these is true:

- the same mutation signature improved more than once
- the signature is the current best observed candidate for that command and has no regressed runs

Belief status semantics live in `docs/BELIEFS.md`.

Memory search prefers promoted belief docs over evidence-only `research_outcome` entries, and contradictory beliefs are down-weighted rather than hidden. `research_outcome` remains a discoverability surface from the `research` command, not promoted doctrine.

## RuVector

RuVector is not embedded as Spark's internal database.

Spark delegates `brain search ... --json` to the RuVector CLI when you choose the `ruvector` backend, but still writes all durable memory locally.

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
