# Chip Memory Rollout

Use this playbook when upgrading another domain chip to the newer Spark memory model.

This document captures the sequence used on the startup chip during the March 11-12, 2026 upgrade session.

## Goal

Move a chip from:

- raw run/outcome-heavy memory
- stale working memory
- weak distinction between grounded doctrine and exploratory probes

to:

- explicit memory tiers
- benchmark-grounded doctrine and boundary docs
- exploratory frontier docs that do not masquerade as doctrine
- working memory refreshed from real benchmark-grounded runs

## What Changed In Core

These changes live in `spark-researcher` and should already be available to every chip once they pull the updated core.

1. Generated frontier state moved out of `spark-researcher.project.json` into `artifacts/frontier/queue.json`.
2. `loop` stayed stable-config-only; generated queue state is for `autoloop` and related candidate flows.
3. Benchmark-grounded and heuristic-frontier runs were split into separate comparison lanes through `chip_result.comparison_class`.
4. Memory search was changed to prefer promoted chip docs over raw run/outcome residue.
5. Memory now has explicit tiers:
   - `research_grounded`
   - `grounded_doctrine`
   - `grounded_boundary`
   - `benchmark_evidence`
   - `exploratory_frontier`
   - `state_snapshot`
   - `raw_outcome`
   - `raw_run`
6. Benchmark-grounded chip runs now refresh `artifacts/memory/working.json` automatically through the normal run path.
7. Memory sync and local search were hardened against concurrent rewrite races on Windows.

## What Changed In The Startup Chip

The startup chip was the proving ground for the pattern.

1. Frontier generation

- added a local frontier fallback so autoloop can continue without a configured provider command
- added bounded follow-on frontier generation from recent frontier results
- kept provider-backed behavior optional instead of making the fallback the default everywhere

2. Evaluation semantics

- benchmark-backed runs now emit `comparison_class: benchmark_grounded`
- heuristic/factor/frontier runs now emit `comparison_class: heuristic_frontier`
- this prevents apples-to-oranges verdicts between benchmark scores and heuristic frontier scores

3. Packet promotion

- benchmark-backed rows emit:
  - `startup_benchmark` with `memory_tier: benchmark_evidence`
  - `startup_doctrine` with `memory_tier: grounded_doctrine`
  - `startup_boundary` with `memory_tier: grounded_boundary`
- exploratory rows emit:
  - `startup_factor` with `memory_tier: exploratory_frontier`

4. Working memory

- replaced stale advisory residue with a chip-state summary
- then automated benchmark-grounded working-memory refresh through the normal run path

5. Watchtower output

- added clearer doctrine, tracks, frontier probes, and why-it-lost pages
- added stable seed vs queued frontier counts
- made startup pages respect explicit config/runtime paths from the core payload

## Rollout Sequence For Another Chip

Follow this order.

1. Fix evaluation semantics first.

- if the chip has more than one evaluator class, add an explicit `comparison_class`
- do not let benchmark-grounded and heuristic/frontier runs compete in the same verdict lane

2. Split stable config from generated frontier state.

- keep stable seed candidates in `spark-researcher.project.json`
- keep generated candidates in `artifacts/frontier/queue.json`
- make sure the chip and operator docs reflect that split

3. Promote packet docs into explicit tiers.

For grounded evidence, emit:

- one or more benchmark evidence docs
- one or more doctrine docs
- one or more boundary docs

For exploratory evidence, emit:

- a small number of explicit exploratory frontier docs

Do not rely on raw `run` and `outcome` docs to do this job.

4. Clean duplicate packet naming.

- keep one naming scheme for each promoted doc family
- remove legacy winner-only or one-off variants once the richer format exists

5. Refresh working memory.

- first do it manually once if needed, to remove stale advisory residue
- then automate benchmark-grounded refresh from the normal `run` path

6. Rebuild memory and Obsidian.

```powershell
python -m spark_researcher.cli memory sync --config <chip-config>
python -m spark_researcher.cli obsidian build --config <chip-config>
```

7. Verify retrieval behavior directly.

For each chip, test at least:

- one grounded doctrine query
- one grounded boundary query
- one exploratory frontier query

Expected behavior:

- grounded doctrine query returns doctrine docs first
- grounded boundary query returns boundary docs first
- exploratory query returns exploratory frontier docs before raw outcomes

## Acceptance Checks

The rollout is not complete until all of these are true.

1. Memory manifest shows explicit `memory_tiers`.
2. Memory index lists tier counts.
3. Working memory is current and chip-state-shaped, not stale advisory text.
4. Obsidian runtime pages reflect the same doctrinal state as memory.
5. Grounded doctrine retrieval beats raw run/outcome residue.
6. Exploratory queries return explicit exploratory docs rather than only raw outcomes.
7. `loop` semantics remain stable and do not replay queue residue.

## Suggested Verification Commands

```powershell
python -m spark_researcher.cli memory sync --config <chip-config>
python -m spark_researcher.cli obsidian build --config <chip-config>
python -m spark_researcher.cli run --config <chip-config> --command <chip-command> --candidate-id <grounded-benchmark-candidate>
python -m spark_researcher.cli memory search "doctrine"
python -m spark_researcher.cli memory search "board"
python -m spark_researcher.cli memory search "<current exploratory theme>"
```

## Failure Patterns To Watch

- benchmark and heuristic runs sharing one metric lane
- queue state drifting back into project config
- working memory staying advisory-shaped after chip runs
- chip packet docs duplicating the same doctrine under multiple names
- exploratory packet docs missing, causing frontier queries to fall back to raw outcomes
- Obsidian showing counts or paths inferred from defaults instead of the actual payload

## Minimal Standard For New Chips

Before trusting a chip as a real operator surface, require:

- one grounded doctrine doc
- one grounded boundary doc
- one benchmark evidence doc
- one current working-memory snapshot
- one exploratory frontier doc family
- one watchtower page that separates grounded doctrine from exploratory probes

That is enough to give the chip a real memory center without adding new infrastructure.
