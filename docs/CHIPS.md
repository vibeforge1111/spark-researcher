# Domain Chips

Domain chips keep `spark-researcher` small.

## Contract

A chip is an external repo with:

- `spark-chip.json`
- `AUTORESEARCH.md`
- one or more command hooks
- its own source code and tests

The manifest now follows `spark-chip.v1` with `spark-hook-io.v1` hook I/O.

Spark calls chip hooks with `--input <json> --output <json>`.

`AUTORESEARCH.md` is the collective bridge contract. It should declare at least:

- repo identity
- display name or agent identity
- `run_command`
- `publish_command`
- collective and adoption policy

Supported hooks:

- `evaluate`: domain-specific candidate evaluation
- `suggest`: domain-specific next-candidate generation
- `packets`: domain-specific memory documents and promotion decisions
- `watchtower`: domain-specific Obsidian pages

Validate a configured chip with:

```powershell
spark-researcher chips validate
spark-researcher collective ready
```

The canonical schema lives at `schemas/spark-chip.schema.json`.

Use `docs/README.md` for the full chip-doc map.

## Related Docs

- validation: `docs/CHIP_VALIDATION.md`, `docs/CHECKLOOP.md`
- rollout and operating model: `docs/CHIP_MEMORY_ROLLOUT.md`, `docs/CHIP_INTELLIGENCE_CONTRACT.md`, `docs/CHIP_INTELLIGENCE_ROLLOUT.md`, `docs/CHIP_ONE_LOOP_FLYWHEEL.md`
- packet and optimizer methods: `docs/CHIP_RESEARCH_PACKET_SCHEMA.md`, `docs/CHIP_TAGGING_RULESET.md`, `docs/CHIP_DSPY_METHOD.md`, `docs/CHIP_BENCHMARK_BRIDGE_GUIDE.md`
- registry: `docs/CHIP_REGISTRY.md`

For richer chips, keep source choice separate from source fetching:

- `research_frontier` decides whether the chip needs more knowledge
- `research_selection` decides which sources should be added next
- bounded discovery or approved-source ingest then fetches or drafts those sources

Create a new chip scaffold with:

```powershell
spark-researcher chips init --domain foo --metric-name foo_score --goal maximize
```

This defaults to a standalone Desktop sibling folder:

```text
C:\Users\USER\Desktop\domain-chip-foo
```

Rules:

- chip names are normalized to start with `domain-chip-`
- omitting `--chip-name` uses `domain-chip-<domain>`
- omitting `--path` creates the chip on the Desktop
- relative `--path` values are also resolved under the Desktop instead of inside `spark-researcher`
- use an absolute `--path` only when you intentionally want a different external location
- absolute or relative targets inside `spark-researcher` are refused

Create the experimental crypto-trading starter with:

```powershell
spark-researcher chips init --domain trading --chip-name domain-chip-trading-crypto --preset crypto-trading
```

The starter writes only the minimum valid repo:

- `pyproject.toml`
- `spark-chip.json`
- `spark-researcher.project.json`
- `README.md`
- `src/<package>/__init__.py`
- `src/<package>/cli.py`

The init command also returns a `next_steps` list for the standalone repo bootstrap flow, including:

- `git init`
- `git branch -m main`
- editable install commands
- a `chips validate` command pointed at the new chip config

The experimental `crypto-trading` preset also writes:

- `docs/CRYPTO_TRADING_ONE_LOOP_SPEC.md`
- `docs/CRYPTO_TRADING_BENCH_PROMOTION_BRIDGE.md`

Create the X content research starter with:

```powershell
spark-researcher chips init --domain xcontent --preset xcontent
```

The `xcontent` preset evaluates X (Twitter) content format + hook type + audience combinations against engagement quality, useful reach, and Grok/xAI relevance scoring. It writes:

- `docs/XCONTENT_ONE_LOOP_SPEC.md`
- `docs/XCONTENT_BENCH_PROMOTION_BRIDGE.md`

Integration surfaces: X API (post analytics, trending topics), Grok/xAI API (relevance scoring, discoverability prediction).

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
- collective identity and publish policy through `AUTORESEARCH.md`

## Packet Rule

Chip packet output should be opinionated, not just verbose.

Prefer a small number of explicit memory tiers:

- `grounded_doctrine`
- `grounded_boundary`
- `benchmark_evidence`
- `exploratory_frontier`

Avoid treating raw run history as chip doctrine. Spark already exports raw `run` and `outcome` docs from the ledger; the chip should add the smaller set of domain docs that deserve promotion above that residue.

When possible, benchmark-grounded chip runs should also drive the current working-memory snapshot through the normal run path so the runtime state stays aligned with promoted doctrine.

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

## Swarm Readiness

A chip is only Spark Swarm ready when all of these are true:

- `AUTORESEARCH.md` exists
- the manifest has identity plus `run_command` and `publish_command`
- the chip has at least one numeric metric run in the ledger
- `.spark-swarm/collective-sync.json` exists and matches the latest run
- `.autoresearch/capsules/` contains a capsule for the latest run

Use:

```powershell
spark-researcher collective ready
```

This reports the exact missing surfaces instead of treating partial wiring as success.

## Commit Rule

When evolving a chip, prefer one small commit per coherent change set.

Good boundaries:

- loop logic
- docs/spec updates
- source-pack expansion
- DSPy runner work
- memory/watchtower changes

Do not mix unrelated runtime residue or queue state into those commits unless you are intentionally snapshotting runtime state.

## Registry

Current known chips are listed in `docs/CHIP_REGISTRY.md`. The broader documentation map lives in `docs/README.md`.
