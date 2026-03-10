# Spark Researcher

Spark Researcher is a compressed blend of three ideas:

- Karpathy's `autoresearch`: a tiny, legible research loop with fixed evaluation.
- Spark Recursion: bounded recursive improvement, trainer recompiles, and anti-drift rules.
- Spark Autoresearch: non-complex local memory, Obsidian watchtower output, and collective sharing.

The design target is simple: keep the whole repo well under `6000` counted lines while still being useful on real projects.

## What It Does

- runs arbitrary project commands from one small JSON config
- evaluates candidates against a fixed metric and writes an immutable JSONL ledger
- exports searchable Markdown memory documents instead of building a heavy memory stack
- keeps local memory as the default backend and supports optional delegated RuVector search
- watches trainer example files and triggers bounded recompiles like a lightweight DSPy loop
- generates an Obsidian vault as the operator watchtower
- publishes capsule files that `autoresearch-collective` can ingest
- proposes self-edits in a temporary workspace and requires explicit human apply
- scaffolds coding, research, and content projects with one init command
- builds compact belief packets from improved runs and approved self-edits
- supports external coding agents through a shared repo contract in `AGENTS.md`
- can suggest and append next candidate trials from ledger history with a bounded autoloop
- can delegate domain-specific evaluation, suggestion, packets, and watchtower pages to external domain chips
- can select reusable packets, build model-specific advisory briefs, and log advisory outcomes
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
spark-researcher init --path C:\work\my-project --preset coding --project-name my-project
spark-researcher chips init --path C:\work\domain-chip-foo --chip-name domain-chip-foo --domain foo --metric-name foo_score
spark-researcher chips status
spark-researcher chips validate
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
spark-researcher line-budget --limit 6000
```

The bundled config points at `examples/toy-project/` so the loop is runnable without extra setup.

## Self Editing

Self-editing is intentionally two-step:

1. `spark-researcher self-edit propose --prompt "..."`
2. `spark-researcher self-edit apply --proposal-id <id>`

The propose step runs only in a copied workspace and writes a full packet with prompt, stdout, stderr, diff summary, and changed files. Nothing is applied to the repo until the second command is called by the owner.

External agents should follow the repo contract in `AGENTS.md`. Backend integration details are documented in `docs/AGENT_BACKENDS.md`.

Only `codex-exec` is built in by default. Other agents should usually be wired through explicit backend commands instead of growing the built-in profile list.

## Layout

- `src/spark_researcher/`: the whole runtime
- `docs/`: short operator docs
- `examples/toy-project/`: runnable demo target
- external domain chips: optional sibling or separate repos loaded through a small manifest bridge
- `artifacts/`: generated ledger, memory, trainer state, and self-edit packets
- `obsidian-vault/`: generated watchtower view
- `.autoresearch/capsules/`: collective-ready insight packets

## Commands

```powershell
spark-researcher run --command train
spark-researcher loop --command train
spark-researcher autoloop --command train
spark-researcher chips init --path C:\work\domain-chip-foo --chip-name domain-chip-foo --domain foo --metric-name foo_score
spark-researcher chips status
spark-researcher chips validate
spark-researcher packets status
spark-researcher packets search "learning rate"
spark-researcher advisory adapters
spark-researcher advisory build --task "draft a startup doctrine update" --model claude
spark-researcher advisory execute --task "draft a startup doctrine update" --model claude --dry-run --command my-wrapper --command {system_prompt_path} --command {user_prompt_path} --command {response_path}
spark-researcher advisory log --task "draft a startup doctrine update" --model claude --status ok --packet-id startup_factor-theme-distribution-velocity-retention
spark-researcher advisory review
spark-researcher optimizer status
spark-researcher optimizer export-advisory-dataset
spark-researcher trainers run
spark-researcher trainers status
spark-researcher candidates suggest --command train
spark-researcher candidates apply --command train
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
spark-researcher line-budget --limit 6000
```

## Intent

This repo is allowed to become more capable, but not more theatrical. If a feature needs a framework before it needs evidence, it probably does not belong here.

## Memory Rule

Local Markdown memory is still the source of truth. The optional `ruvector` backend is only an external delegated search surface, not Spark's internal database.

## Autonomy Boundary

`loop` runs the current fixed candidate set. `autoloop` is the bounded autonomous layer: it runs pending trials, suggests new candidates from ledger evidence, appends only new in-scope candidates to config, and continues for a limited number of rounds. If a mutable parameter declares `value_range` and `value_step`, autoloop can also probe one-step numeric neighbors around already beneficial values.

## Domain Chips

Domain chips keep domain intelligence out of the core repo. A chip is an external repo with a `spark-chip.json` manifest using `spark-chip.v1` and up to four hooks:

- `evaluate`
- `suggest`
- `packets`
- `watchtower`

Spark still owns the loop, ledger, memory index, self-edit policy, and collective export. The chip only supplies domain-specific logic. See `docs/CHIPS.md`.

Use `docs/CHIP_VALIDATION.md` as the standard pass/fail protocol for validating any chip against the current core.

New chips should usually start from `spark-researcher chips init`, then replace the deterministic placeholder logic with real domain logic instead of copying an old chip repo by hand.

## Advisory Path

Spark now has one lightweight intelligence path for LLM use:

`task -> advisory -> packets -> adapter -> model -> outcome`

Packets are loaded from local memory exports. Advisory selects only the few packets that matter for the current task. Adapters format that advice for Claude, Codex, OpenClaw, or a generic fallback. See `docs/ADVISORY.md`.
