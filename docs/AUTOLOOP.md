# Autoloop

Autoloop is the lightweight autonomous layer in Spark Researcher.

## What It Does

- runs pending trials from the current config
- inspects ledger history after each round
- extracts beneficial single-parameter primitives
- suggests new candidate trials
- appends only unseen suggestions
- continues for a bounded number of rounds

## Current Heuristic

The current recommender is intentionally simple:

- find baseline metric from zero-mutation runs
- find single mutations that beat that baseline or already produced an improved run
- combine beneficial primitives across different parameters
- optionally probe numeric neighbors around winning values when a mutable parameter declares `value_range` and `value_step`
- skip any mutation signature already present in config or already tested in the ledger

This is enough to recover the common plateau case:

- one single mutation clearly helps
- another single mutation is better than the raw baseline but worse than the current best
- the combined trial is still worth testing

Neighborhood exploration stays bounded:

- only parameters with declared `value_range` and `value_step` are eligible
- only values near already beneficial runs are explored
- only one step up or down is suggested at a time
- existing or already-tested signatures are skipped

## Commands

```powershell
spark-researcher candidates suggest --command train
spark-researcher candidates apply --command train
spark-researcher autoloop --command train
```

## Boundaries

- bounded by explicit round count
- bounded by existing loop discard limits
- appends suggestions to config transparently
- does not invent new mutable parameters
- does not replace the fixed evaluator
