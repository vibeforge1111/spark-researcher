# Spark Researcher

Spark Researcher is a compressed blend of three ideas:

- Karpathy's `autoresearch`: a tiny, legible research loop with fixed evaluation.
- Spark Recursion: bounded recursive improvement, trainer recompiles, and anti-drift rules.
- Spark Autoresearch: non-complex local memory, Obsidian watchtower output, and collective sharing.

The design target is simple: keep the whole repo well under `11000` counted lines while still being useful on real projects.

## What It Does

- runs arbitrary project commands from one small JSON config
- evaluates candidates against a fixed metric and writes an immutable JSONL ledger
- exports searchable Markdown memory documents instead of building a heavy memory stack
- keeps memory tiered so grounded doctrine, boundaries, benchmark evidence, exploratory frontier, and raw history do not compete as if they were the same thing
- records lightweight JSONL traces for runs, advisory builds, frontier suggestions, and self-edit actions
- keeps local Markdown memory as the default backend and supports optional RuVector retrieval
- watches trainer example files and triggers bounded recompiles like a lightweight DSPy loop
- generates an Obsidian vault as the operator watchtower
- publishes capsule files that `autoresearch-collective` can ingest
- proposes self-edits in a temporary workspace and requires explicit human apply
- scaffolds coding, research, and content projects with one init command
- builds compact belief packets from improved runs and approved self-edits
- promotes durable run beliefs more selectively and marks contradictory lessons as provisional instead of turning every improved run into long-lived memory
- supports external coding agents through a shared repo contract in `AGENTS.md`
- can suggest and append next candidate trials from ledger history with a bounded autoloop
- can prioritize recent surprising failures so autoloop learns from misses before comfort-zone retuning
- can use failure-aware two-draft verification, bounded research retries, and citation checks with lightweight source provenance to keep advisory answers grounded without adding a heavy agent layer
- can delegate domain-specific evaluation, suggestion, packets, and watchtower pages to external domain chips, with optional LLM frontier fallback and relaxed open-value exploration
- can select reusable packets, build model-specific advisory briefs, and log advisory outcomes
- advisory now carries packet-stability hints so verifier decisions can distinguish durable memory from provisional memory
- packet retrieval now prefers durable beliefs over provisional ones so advisory pulls the steadier local lessons first
- research-command outcomes can surface as evidence-only `research_outcome` packets for discovery, but they stay ranked below doctrine or belief packets
- keeps DSPy optional as an optimizer for measurable subroutines instead of making it part of the core runtime
- can execute advisory-backed model requests through lightweight command templates instead of hardwiring provider SDKs

## Core Rules

- fixed evaluator, mutable strategy
- one mutation, one hypothesis
- ledger first, narrative second
- self-edit never auto-applies
- mutable targets must be declared
- the system works in temp workspaces, not in-place
- git promotion is explicit: `manual`, `branch`, or `main`

## Quick Start

```powershell
cd C:\Users\USER\Desktop\spark-researcher
python -m pip install -e .
spark-researcher run --command train
spark-researcher loop --command train
spark-researcher autoloop --command train
spark-researcher autoloop --command train --continuous --rounds 2 --suggest-limit 2 --pause-seconds 300
spark-researcher init --path C:\work\my-project --preset coding --project-name my-project
spark-researcher chips init --domain foo --metric-name foo_score
spark-researcher chips status
spark-researcher chips validate
spark-researcher intent set --goal "Build the strongest startup-understanding agent" --outcome "Create agentic startups from first-principles doctrine" --success-criterion "Find reusable startup doctrines" --success-criterion "Map failure boundaries" --resource web --resource memory --resource ruvector --resource dspy --frontier-mode open
spark-researcher intent show
spark-researcher packets search "learning rate"
spark-researcher advisory build --task "summarize the strongest current trading rule" --model codex
spark-researcher advisory adapters
spark-researcher advisory providers
spark-researcher optimizer status
spark-researcher trainers run
spark-researcher memory sync
spark-researcher memory backend-policy
spark-researcher beliefs build
spark-researcher obsidian build
spark-researcher collective publish
spark-researcher collective sync-local
spark-researcher line-budget --limit 11000
```

The bundled config points at `examples/toy-project/` so the loop is runnable without extra setup.

## Self Editing

Self-editing is intentionally two-step:

1. `spark-researcher self-edit propose --prompt "..."`
2. `spark-researcher self-edit apply --proposal-id <id>`

The propose step runs only in a copied workspace and writes a full packet with prompt, stdout, stderr, diff summary, and changed files. Nothing is applied to the repo until the second command is called by the owner.

External agents should follow `AGENTS.md`; backend details live in `docs/AGENT_BACKENDS.md`. Only `codex-exec` is built in by default.

## Layout

- `src/spark_researcher/`: the whole runtime
- `docs/`: short operator docs
- `docs/book-of-ai-intelligence/`: nontechnical book-length playbook for building a smarter agent
- `docs/AI_LAB_MAP.md`: how Spark maps to real AI-lab training, eval, retrieval, and data practice
- `examples/toy-project/`: runnable demo target
- external domain chips: optional sibling or separate repos loaded through a small manifest bridge
- `artifacts/`: generated ledger, memory, trainer state, self-edit packets, failures, and traces
- `artifacts/frontier/queue.json`: generated runtime frontier queue
- `obsidian-vault/`: generated watchtower view
- `.autoresearch/capsules/`: collective-ready insight packets

## Commands

```powershell
spark-researcher run --command train
spark-researcher loop --command train
spark-researcher autoloop --command train
spark-researcher autoloop --command train --continuous --rounds 2 --suggest-limit 2 --pause-seconds 300
spark-researcher chips init --domain foo --metric-name foo_score
spark-researcher chips status
spark-researcher chips validate
spark-researcher intent show
spark-researcher packets status
spark-researcher packets search "learning rate"
spark-researcher advisory adapters
spark-researcher advisory build --task "draft a startup doctrine update" --model claude
spark-researcher advisory execute --task "draft a startup doctrine update" --model claude --dry-run --command "my-wrapper {system_prompt_path} {user_prompt_path} {response_path}"
spark-researcher advisory execute --task "draft a startup doctrine update" --model claude
spark-researcher advisory log --task "draft a startup doctrine update" --model claude --status ok --packet-id startup_factor-theme-distribution-velocity-retention
spark-researcher advisory review
spark-researcher optimizer status
spark-researcher optimizer export-advisory-dataset
spark-researcher trainers run
spark-researcher trainers status
spark-researcher candidates suggest --command train
spark-researcher candidates apply --command train
spark-researcher failures --limit 10
spark-researcher memory backend-policy
spark-researcher memory backend-policy --backend ruvector
spark-researcher memory sync
spark-researcher memory search "learning rate"
spark-researcher memory search "anchor variance" --backend ruvector
spark-researcher beliefs build
spark-researcher obsidian build
spark-researcher collective publish
spark-researcher collective status
spark-researcher collective sync-local
spark-researcher self-edit profiles
spark-researcher self-edit policy
spark-researcher self-edit policy --git-mode branch --push
spark-researcher self-edit propose --prompt "simplify the trainer status output" --backend-profile codex-exec
spark-researcher self-edit review --proposal-id <id> --decision approve --root-lesson "..." --lineage-failure "..." --lineage-failure "..." --lineage-failure "..." --counterfactual "..." --ghost-check "..." --rollback-condition "..."
spark-researcher self-edit apply --proposal-id <id>
spark-researcher self-edit apply --proposal-id <id> --git-mode branch --push
spark-researcher self-edit apply --proposal-id <id> --git-mode main --push
spark-researcher line-budget --limit 11000
```

## Intent

This repo is allowed to become more capable, but not more theatrical. If a feature needs a framework before it needs evidence, it probably does not belong here.

## Memory Rule

Local Markdown memory is still the source of truth. `ruvector` remains the recommended retrieval upgrade once your corpus grows, and Spark falls back cleanly to local search when RuVector is not ready in the current shell.

Memory is now explicitly tiered:

- `research_grounded`
- `grounded_doctrine`
- `grounded_boundary`
- `benchmark_evidence`
- `exploratory_frontier`
- `state_snapshot`
- `raw_outcome`
- `raw_run`

Search prefers higher-signal tiers first. That keeps benchmark-grounded doctrine and boundaries ahead of raw run residue, while still preserving the full audit trail on disk.

Working memory is also narrower now: benchmark-grounded chip runs can refresh `artifacts/memory/working.json` automatically so the runtime snapshot tracks the current doctrinal state instead of lingering as stale advisory prompt residue.

## Autonomy Boundary

`loop` runs the current fixed candidate set. `autoloop` is the bounded autonomous layer: it runs pending trials, suggests new candidates from ledger evidence, writes only new generated candidates to `artifacts/frontier/queue.json`, and continues for a limited number of rounds. `autoloop --continuous` simply repeats those bounded passes until interrupted. If a mutable parameter declares `value_range` and `value_step`, autoloop can also probe one-step numeric neighbors around already beneficial values. Frontier runs that land close to the current best are marked `near_best` and do not trip the discard limit.

The config split is intentional:

- `spark-researcher.project.json` is the stable project spec
- `artifacts/frontier/queue.json` is the generated runtime queue

Promote candidates back into the main config only when you want them to become stable seed trials rather than runtime residue.

## Domain Chips

Domain chips keep domain intelligence out of the core repo. A chip is an external repo with a `spark-chip.json` manifest using `spark-chip.v1` and up to four hooks:

- `evaluate`
- `suggest`
- `packets`
- `watchtower`

Spark still owns the loop, ledger, memory index, self-edit policy, and collective export. The chip only supplies domain-specific logic. See `docs/CHIPS.md`.

Use `docs/CHIP_VALIDATION.md` as the standard pass/fail protocol for validating any chip against the current core.

New chips should usually start from `spark-researcher chips init`, which now defaults to creating a standalone Desktop sibling folder like `C:\Users\USER\Desktop\domain-chip-foo`. Relative `--path` values are also resolved under Desktop, and chip targets inside `spark-researcher` are refused. Then replace the deterministic placeholder logic with real domain logic instead of copying an old chip repo by hand.

## Advisory Path

Spark now has one lightweight intelligence path for LLM use:

`task -> advisory -> packets -> adapter -> model -> outcome`

Packets are loaded from local memory exports. Advisory selects only the few packets that matter for the current task. Adapters format that advice for Claude, Codex, OpenClaw, or a generic fallback. See `docs/ADVISORY.md`.

## Intent Path

Spark can keep a persistent mission for a project or chip:

`intent -> advisory -> frontier -> chip -> autoloop`

Use `spark-researcher intent set` to define the goal, target outcome, success criteria, and which resources the loop should actively exploit. Frontier generation then optimizes for that mission instead of exploring aimlessly. See `docs/INTENT.md`.

## Provider Commands

Provider execution stays lightweight. Spark prepares request files and delegates the actual model call to a command template you control.

Example environment variables:

```powershell
$env:SPARK_RESEARCHER_ADAPTER_CLAUDE_COMMAND='powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\USER\Desktop\spark-researcher\scripts\claude_frontier_wrapper.ps1 {system_prompt_path} {user_prompt_path} {response_path} -Model opus'
$env:SPARK_RESEARCHER_ADAPTER_CODEX_COMMAND='codex exec --system-prompt-file {system_prompt_path} --prompt-file {user_prompt_path} --json-out {response_path}'
$env:SPARK_RESEARCHER_ADAPTER_OPENCLAW_COMMAND='openclaw run --system {system_prompt_path} --prompt {user_prompt_path} --output {response_path}'
```

Use `spark-researcher advisory providers` to check whether a provider command is configured and whether its executable is present.

## Checkloop

Use `docs/CHECKLOOP.md` as the standard local proving-ground flow for validating the current core repo on this machine before trusting a new change.

Use `docs/RELIABILITY_TEST_PLAN.md` when you want the more detailed subsystem-by-subsystem reliability audit for advisory, verifier, research, memory, and watchtower behavior.
