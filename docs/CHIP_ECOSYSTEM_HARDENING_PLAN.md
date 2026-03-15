# Chip Ecosystem Hardening Plan

## Purpose

This document turns the current Spark Researcher and domain-chip audits into one operating plan.

It has four jobs:

1. define what Spark Researcher should own versus what a chip should own
2. list the concrete gaps found in the current system
3. describe how to fix those gaps without collapsing chip logic back into core
4. define a better standard for documentation, validation, and new chip creation

This is meant to be a working hardening manual, not just an audit summary.

## Current Read

Spark Researcher is directionally correct as a bounded kernel:

- core owns queueing, run isolation, ledgering, memory export, watchtower build, and self-edit control
- chips own domain evaluation, candidate suggestion, doctrine packeting, and domain pages

That architecture is worth preserving.

What is not yet strong enough is the contract layer between:

- chip manifest and real runtime behavior
- chip-local truth and Spark-facing memory/watchtower surfaces
- isolated workspace execution and large, stateful, real-world chips

The current system is good enough to prove the model. It is not yet hardened enough to be the default operating system for a large chip portfolio.

## Target State

Spark should become a strict, small, reliable kernel with these properties:

- a chip that validates is actually runnable, packetable, and watchtower-buildable
- the core never silently accepts malformed chip frontier contracts
- the core never compares failed runs as if they were legitimate evidence
- the core never promotes heuristic or disconnected evidence as benchmark-grounded truth
- the core can isolate a chip workspace on Windows without path-length or embedded-state failures
- chips can grow rich domain systems without forcing core changes for each domain

Each chip should become a self-contained domain adapter with these properties:

- explicit benchmark lane, exploratory lane, and promotion lane
- packet hooks that derive from real Spark runtime inputs, not chip-private assumptions
- watchtower pages that show why a candidate won, why it lost, and what lane it belongs to
- no hidden dependency on sibling repos unless that dependency is declared and validated
- truthful downgrade behavior when required external systems are missing

## Architectural Guardrail

Preserve this split:

- Spark core owns generic orchestration and generic truth gates
- chips own domain semantics and domain-specific artifacts

Do not respond to current gaps by moving startup, trading, Pokemon, or Spark-ops logic into the core.

Instead:

- strengthen core contracts
- strengthen generic validation
- tighten chip authoring rules
- make richer chip surfaces legal without making them invisible to Spark

## Cross-Cutting Gaps

### 1. Validation Is Too Shallow

Current problem:

- `chips validate` mostly checks schema shape and command presence
- malformed practical manifests can still pass
- chips can validate even when full Spark execution later fails

Observed failures:

- trading chips declare frontier config at top level instead of under `frontier`
- Spark Private validates even though isolated `run` fails on workspace copy

What to change in core:

- split validation into levels
- make validation report both `schema_valid` and `runtime_ready`
- fail validation when recognized frontier keys are present at top level
- add runtime smoke hooks for `evaluate`, `packets`, and `watchtower`
- add isolation checks for path length, embedded state trees, and undeclared dependencies

Recommended validation levels:

- `L0 schema`: manifest shape, command shape, protocol version
- `L1 contract`: frontier placement, allowed field names, hook I/O shape
- `L2 runtime smoke`: evaluate/suggest/packets/watchtower execute with minimal payloads
- `L3 Spark flow`: `run`, `memory sync`, and `obsidian build` succeed
- `L4 portability`: chip is self-contained or explicitly declares external roots

Documentation changes needed:

- expand [`docs/CHIP_VALIDATION.md`](/C:/Users/USER/Desktop/spark-researcher/docs/CHIP_VALIDATION.md)
- add a new explicit "runtime-ready versus schema-valid" section to [`docs/CHIPS.md`](/C:/Users/USER/Desktop/spark-researcher/docs/CHIPS.md)

### 2. Workspace Isolation Breaks on Large Stateful Chips

Current problem:

- Spark copies the whole project tree into a run workspace
- this is correct in principle, but too naive for deeply nested or live state trees on Windows

Observed failure:

- `domain-chip-spark-private` failed before hook execution because embedded Paperclip state under `localhost/.../.paperclip-data/...` was copied into a path tree too deep for the run workspace

What to change in core:

- add configurable ignore patterns per project or per chip
- add a `chip.runtime.ignore_paths` or `chip.workspace.exclude` contract
- add preflight detection for suspicious nested state directories
- normalize workspace-copy behavior for Windows path constraints
- support a "thin workspace copy" mode for chips that only need code and declared docs, not full local runtime residue

What to change in chip standards:

- chips must keep live local services, databases, logs, and caches outside the committed chip surface where possible
- if a chip depends on local embedded state, that state must be explicitly declared as non-copyable and non-required for bounded evaluation

Documentation changes needed:

- add a "workspace isolation contract" section to [`docs/ARCHITECTURE.md`](/C:/Users/USER/Desktop/spark-researcher/docs/ARCHITECTURE.md)
- add a "path hygiene and state hygiene" section to [`docs/CHIPS.md`](/C:/Users/USER/Desktop/spark-researcher/docs/CHIPS.md)

### 3. Core Baseline Logic Is Not Truthful Enough

Current problem:

- failed or non-comparable runs can still influence best-metric logic
- baseline comparison is using any historical best instead of lane-aware, status-aware evidence

Observed effects:

- failed runs can poison the benchmark baseline
- new baseline evaluations are reported as `regressed` simply because a much stronger historical candidate already exists
- autoloop semantics become misleading across chips

What to change in core:

- exclude `failed` and `unknown` rows from best-metric and suggestion logic
- compare only against status-qualified rows
- separate baseline verdicts from "best historical candidate" verdicts
- add comparison lanes:
  - baseline versus baseline
  - exploratory versus exploratory
  - benchmark-grounded versus benchmark-grounded
  - promotion-lane versus promotion-lane
- store lane in normalized core metadata, not only chip-local result blobs

Documentation changes needed:

- update [`docs/AUTOLOOP.md`](/C:/Users/USER/Desktop/spark-researcher/docs/AUTOLOOP.md)
- update [`docs/CHIP_BENCHMARK_BRIDGE_GUIDE.md`](/C:/Users/USER/Desktop/spark-researcher/docs/CHIP_BENCHMARK_BRIDGE_GUIDE.md)

### 4. Research Escalation Is Not Reaching the Weakest Cases

Current problem:

- under-supported tasks can return early from advisory verification
- the web-research retry path is not reached in the cases most likely to need it

Why this matters for chips:

- chips with `frontier.web_search` enabled rely on Spark to escalate weak evidence into bounded research
- if core does not escalate correctly, web-aware chips become worse than their manifests claim

What to change in core:

- fix the advisory state machine so `under_supported` can reach bounded research
- separate "needs verification" from "research retry requested"
- record advisory lane transitions visibly in traces and memory

Documentation changes needed:

- update [`docs/ADVISORY.md`](/C:/Users/USER/Desktop/spark-researcher/docs/ADVISORY.md)
- update [`docs/CHIP_INTELLIGENCE_CONTRACT.md`](/C:/Users/USER/Desktop/spark-researcher/docs/CHIP_INTELLIGENCE_CONTRACT.md)

### 5. Packet Hook Contract Is Too Easy To Misuse

Current problem:

- Spark sends packet hooks a standard payload
- chips can still assume a different payload model and produce misleading memory docs

Observed failure:

- `domain-chip-trading-crypto` packeting uses `payload["candidate"]` and re-scores empty mutations instead of using `ledger_rows` and `outcomes`

What to change in core:

- formalize packet hook schema as first-class documentation
- validate required/allowed packet inputs in `chips validate`
- add optional strict-mode warnings when a hook emits docs without consuming ledger rows
- include a packeting fixture test in the validation suite

What to change in chip standards:

- `packets()` must be ledger-derived by default
- single-candidate packeting should only happen in explicit chip-local helper flows, not Spark's main memory sync path

Documentation changes needed:

- strengthen [`docs/CHIP_INTELLIGENCE_CONTRACT.md`](/C:/Users/USER/Desktop/spark-researcher/docs/CHIP_INTELLIGENCE_CONTRACT.md)
- strengthen [`docs/CHIP_MEMORY_ROLLOUT.md`](/C:/Users/USER/Desktop/spark-researcher/docs/CHIP_MEMORY_ROLLOUT.md)

### 6. Memory and Obsidian Surfaces Need Collision Control

Current problem:

- slug truncation and repeated titles can collide
- Spark writes packet outputs without dedupe
- large chips dump huge numbers of raw outcome and run docs into memory/watchtower

Observed effects:

- duplicate logical docs can point at the same physical file
- document counts inflate without adding new truth
- large chips become noisy instead of more legible

What to change in core:

- use deterministic collision-safe filenames
- dedupe packet documents by `kind + slug + content hash`
- separate "raw archive" from "operator-facing memory"
- cap default watchtower ingestion of raw run history
- introduce compaction summaries for mature chips

What to change in chip standards:

- packet outputs should favor doctrine, boundary, benchmark evidence, and state snapshots
- chips should not use packet hooks to dump raw archives that Spark already stores

Documentation changes needed:

- update [`docs/MEMORY.md`](/C:/Users/USER/Desktop/spark-researcher/docs/MEMORY.md)
- update [`docs/OBSIDIAN.md`](/C:/Users/USER/Desktop/spark-researcher/docs/OBSIDIAN.md)

### 7. Truth Lanes Need To Be More Explicit

Current problem:

- heuristic frontier, benchmark-grounded evidence, and real-world readiness are not normalized enough in core

Observed effects:

- Pokemon can surface disconnected heuristic best-runs too close to meaningful benchmark evidence
- watchtower pages can blur "interesting" with "grounded"

What to change in core:

- normalize lane fields in core ledger rows
- make memory tier defaults depend on lane
- add lane badges in watchtower summaries
- block grounded doctrine packeting from heuristic-only rows unless the chip explicitly downgrades them

Documentation changes needed:

- update [`docs/CHIP_ONE_LOOP_FLYWHEEL.md`](/C:/Users/USER/Desktop/spark-researcher/docs/CHIP_ONE_LOOP_FLYWHEEL.md)
- update [`docs/STARTUP_BENCH_PROMOTION_BRIDGE.md`](/C:/Users/USER/Desktop/spark-researcher/docs/STARTUP_BENCH_PROMOTION_BRIDGE.md)

### 8. Self-Edit Apply Needs Atomicity

Current problem:

- `self-edit apply` can mutate git state and then fail before metadata completes

Why this matters for chips:

- chip-local self-edit only stays trustworthy if "applied" means coherent and durable

What to change in core:

- stage all validation before commit
- treat commit, copy, metadata write, and push as an ordered transactional flow
- record partial-apply failures explicitly if atomicity cannot be guaranteed

Documentation changes needed:

- update [`docs/SELF_EDITING.md`](/C:/Users/USER/Desktop/spark-researcher/docs/SELF_EDITING.md)

## Chip-Specific Remediation

### Domain Chip Agentic Marketing

Current status:

- good integration with Spark
- coherent packeting and watchtower behavior
- useful benchmark versus frontier distinction

Gaps to close:

- fix packet slug collisions
- reduce duplicate memory outputs
- tighten state snapshot and pilot packet dedupe

Recommended work:

1. add collision-safe slugs or explicit doc ids in the chip packet output
2. make repeated benchmark evidence updates idempotent
3. add a small chip-local test that packeting the top 3 rows produces unique documents

Documentation to add or improve:

- a short "pilot bridge packet contract" inside the chip repo
- a short "what makes a marketing candidate benchmark-grounded" manual

### Domain Chip Pokemon Red

Current status:

- richest experimental chip in the portfolio
- real emulator path exists
- autolearn/autopilot machinery is deeper than most chips

Gaps to close:

- heuristic scaffold scores are too eligible for top-level best-run surfaces
- watchtower and memory need a harder divide between disconnected scaffold output and emulator-grounded evidence

Recommended work:

1. require `emulator_connected == 1.0` for benchmark-grounded best-run packeting
2. keep disconnected scaffold runs in exploratory frontier only
3. expose "ROM connected / task state loaded / benchmark legal" status prominently at watchtower top
4. add a chip-local test proving packeting does not elevate disconnected runs into grounded doctrine

Documentation to add or improve:

- a "truth lanes for emulator chips" section in the chip README
- a "what counts as benchmark proof versus scaffold hint" manual

### Domain Chip Spark Private

Current status:

- valuable chip-local doctrine and packeting logic
- memory sync and watchtower can work against existing runtime artifacts
- full isolated `run` path currently breaks

Gaps to close:

- workspace copy is not portable
- chip mixes durable code with live embedded local ops state
- packet outputs still show duplicate doc behavior

Recommended work:

1. declare runtime-excluded paths for local control-plane state
2. move or quarantine non-essential local service data outside the chip tree
3. create a bounded evaluation mode that does not require copying live Paperclip residue
4. add a chip-local smoke test for isolated Spark execution

Documentation to add or improve:

- a "local ops state versus portable chip state" manual
- a bootstrap guide for bringing up local integrations after the chip is copied

### Domain Chip Startup YC

Current status:

- strongest benchmark-grounded chip in the portfolio
- coherent separation between heuristic factor frontier and benchmark lane
- good candidate for becoming the reference chip

Gaps to close:

- external sibling dependency on `startup-bench`
- portability is environment-dependent rather than chip-declared
- large watchtower surface needs compaction rules

Recommended work:

1. explicitly declare `startup-bench` as an external dependency in manifest or config
2. add validation that benchmark mode is unavailable without that dependency
3. consider packaging the minimal benchmark runner contract or adapter separately
4. add compaction views so watchtower emphasizes current strongest doctrine, weakest grounded track, and next benchmark queue

Documentation to add or improve:

- promote this chip as the reference benchmark-lane design
- add a manual for external benchmark adapters

### Domain Chip Trading Crypto

Current status:

- direction is right
- watchtower ambition is good
- evaluation and recursive loop concepts are aligned with the desired model

Gaps to close:

- malformed frontier manifest
- packets hook is not Spark-ledger-derived
- packet outputs underuse actual benchmark results
- needs stronger bridge between backtest results and promotion queue truth

Recommended work:

1. move `allowed_mutations`, `field_patterns`, and `open_mutation_fields` under `frontier`
2. rewrite `packets()` to derive from `ledger_rows` and `outcomes`
3. emit benchmark evidence, doctrine candidates, and contradiction surfaces from actual best rows
4. add a chip-local test proving packet output changes when ledger winners change
5. add explicit "why not paper-trade-ready yet" outputs for rejected rows

Documentation to add or improve:

- a manual for doctrine extraction from backtests
- a manual for backtest-to-paper-trade promotion rules

## Documentation Work For Spark Researcher

Spark's docs should stop assuming that schema validity implies operational validity.

### Update `docs/CHIPS.md`

Add sections for:

- chip ownership boundaries
- required hook behavior
- self-contained versus externally dependent chips
- workspace copy model
- truth lanes: exploratory, benchmark-grounded, shadow, real-world
- required watchtower minimums

### Rewrite `docs/CHIP_VALIDATION.md`

Make it a serious manual, not just a schema note.

It should include:

- validation levels `L0-L4`
- required smoke tests
- examples of invalid-but-schema-passing chips
- portability requirements
- packet hook truthfulness requirements

### Expand `docs/MEMORY.md`

Add:

- packet dedupe rules
- collision-safe slug guidance
- raw archive versus operator-facing memory
- chip packet dos and don'ts

### Expand `docs/OBSIDIAN.md`

Add:

- watchtower compaction patterns
- required pages for mature chips
- how to avoid dumping every run into first-class operator views

### Expand `docs/ARCHITECTURE.md`

Add:

- "bounded kernel, rich chips" principle
- runtime isolation model
- external adapter contract
- why domain logic should stay out of core

### Expand `docs/SELF_EDITING.md`

Add:

- atomicity expectations
- partial-failure behavior
- how chip-local self-edit should interact with Spark review state

## New Manual Needed: How To Create A New Chip Correctly

Spark should gain a first-class chip authoring manual.

Recommended new document:

- `docs/CHIP_AUTHORING_GUIDE.md`

That guide should cover:

### Phase 1. Define The Domain Truth Model

The author must answer:

- what is exploratory evidence in this domain
- what is benchmark-grounded evidence
- what is promotion-lane evidence
- what should never be promoted from heuristic output alone

### Phase 2. Define The Mutation Frontier

Rules:

- every mutable field must serve evaluator-visible meaning
- open fields must be bounded by patterns
- frontier config must live under `frontier`
- required fields should be minimal but real

### Phase 3. Define Hook Responsibilities

`evaluate`:

- receives candidate mutations
- returns truthful result, metrics, and lane
- must degrade honestly when prerequisites are missing

`suggest`:

- derives from `ledger_rows`, `candidate_trials`, and intent
- should prefer near-winner improvements and contradiction checks

`packets`:

- derives from `ledger_rows` and `outcomes`
- emits doctrine, boundary, benchmark evidence, or state docs
- should not hallucinate candidate context not present in Spark inputs

`watchtower`:

- produces operator-facing pages
- must show current leader, key failures, and next queue
- must keep lane distinctions visible

### Phase 4. Define Environment Contract

The author must declare:

- external repos required
- local executables required
- services required
- optional integrations
- what is still runnable in bounded mode when dependencies are absent

### Phase 5. Provide Smoke Tests

Every chip should include tests for:

- manifest shape
- hook smoke execution
- packeting from fixture ledger rows
- watchtower build from fixture summary
- degraded-mode truthfulness when dependencies are absent

## Suggested New Validation Rules For Future Chips

The next chips should not be accepted until they pass all of these:

1. manifest frontier config is structurally correct
2. `evaluate` returns a result in both fully configured and degraded modes
3. `packets` consumes fixture `ledger_rows` and emits distinct documents
4. `watchtower` builds a bounded operator surface
5. `run`, `memory sync`, and `obsidian build` all succeed in Spark
6. path and filename lengths stay Windows-safe
7. no undeclared sibling dependency exists
8. heuristic-only rows cannot become grounded doctrine unless explicitly allowed and clearly downgraded

## Core Engineering Roadmap

### Phase A. Core Truth And Safety Fixes

Do these first:

1. status-aware best-metric and baseline logic
2. advisory research escalation fix
3. self-edit apply atomicity
4. discard-limit logic including failed and unknown runs

Why first:

- these affect every chip immediately
- these are correctness issues, not polish

### Phase B. Contract Hardening

Do next:

1. stricter manifest validation
2. packet hook contract validation
3. lane normalization in ledger rows
4. runtime-ready validation levels

Why next:

- these stop future chip drift

### Phase C. Isolation And Filesystem Hardening

Do next:

1. configurable workspace exclusions
2. Windows path-length hardening
3. collision-safe memory filenames
4. packet dedupe

Why next:

- these unblock richer chips and reduce operational brittleness

### Phase D. Watchtower And Memory Quality

Do next:

1. compaction views
2. mature-chip archive separation
3. lane badges and clearer operator summaries

Why next:

- these improve usability once correctness is stable

## Chip Remediation Order

Recommended order:

1. fix Spark core truth bugs first
2. fix validation and packet contract second
3. fix `domain-chip-trading-crypto`
4. fix `domain-chip-spark-private` isolation
5. fix Pokemon truth-lane hardening
6. clean up Agentic Marketing dedupe
7. convert Startup YC into the reference chip and authoring model

Why this order:

- trading and Spark Private are the clearest contract failures
- Pokemon is valuable but mostly needs truth-surface hardening
- Agentic Marketing is already usable
- Startup YC is closest to a canonical benchmark chip

## Definition Of Done For A Hardened Chip Ecosystem

The system is in a good state when all of these are true:

- a chip that validates also runs, syncs memory, and builds watchtower
- no failed run can poison baselines or candidate suggestions
- no malformed frontier manifest can pass quietly
- packet hooks are ledger-derived and test-covered
- heuristic frontier output is visibly separate from benchmark-grounded doctrine
- chips can declare external dependencies explicitly
- Windows path and copy constraints are handled deliberately
- at least one benchmark chip and one exploratory chip are documented as reference implementations

## Immediate Next Actions

Start here, one by one:

1. patch Spark core baseline/status logic
2. patch advisory research escalation
3. harden manifest validation for frontier placement
4. harden packet hook validation
5. fix trading chip manifest and packets hook
6. add workspace exclusion support and unblock Spark Private
7. harden Pokemon packeting so disconnected scaffold runs stay exploratory
8. update docs to match the new real contract

## Recommended Follow-On Documents

After the first code fixes land, create these:

- `docs/CHIP_AUTHORING_GUIDE.md`
- `docs/CHIP_HOOK_IO_SCHEMA.md`
- `docs/CHIP_PORTABILITY_GUIDE.md`
- `docs/REFERENCE_CHIPS.md`

Those documents should turn the lessons in this plan into stable operating rules for future chip builders.
