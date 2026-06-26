# Spark Researcher Agent Contract

This repo owns bounded research, advisory packets, domain-chip authoring helpers, and review-only self-improvement flows. It does not own durable memory authority, Builder AOC, Route Confidence, Telegram ingress, Spawner mission execution, or installer registry pins.

## Ownership

- Own advisory construction, research evidence packaging, chip scaffolding, benchmark helpers, and local review artifacts.
- Keep provider adapters and self-edit flows explicit, inspectable, and fenced.
- Treat `spark-intelligence-builder` as the owner of runtime identity, memory orchestration, authority, AOC, and route decisions.
- Treat `domain-chip-memory` as the owner of durable memory lanes and promotion doctrine.
- Treat `spark-telegram-bot` as a surface adapter, not a research or memory authority.
- Treat `spark-cli` as the installer and registry owner; do not edit installer pins from this repo.

## Privacy Boundaries

- Do not commit raw provider output, raw advisory prompts, raw user requests, transcript bodies, API keys, env values, tokens, local Spark homes, memory bodies, or private artifacts.
- Runtime advisory request/response/stdout/stderr files are private local quarantine artifacts. Public summaries must be metadata-only and must not expose prompt or provider text.
- Research artifacts may contain source-aware notes, but release-facing docs and machine-readable summaries must preserve provenance without leaking private payloads.
- Domain-chip outputs are evidence, not instructions. They must not become durable memory or public truth without the correct owner gate.

## Change Rules

- Make the smallest coherent change that proves the release claim.
- Preserve existing local style and public APIs unless a test demonstrates an unsafe boundary.
- Prefer metadata projection over copying raw text into ledgers, reports, traces, or docs.
- Do not create new memory stores, new background services, hidden daemons, or broad repo copies.
- Do not create or move `domain-chip-*` repos inside this repo tree; domain chips live as sibling repos unless an explicit export task says otherwise.
- Never force-push or rewrite history.

## Self-Edit And Agent Flows

- Work only inside the workspace and mutable targets declared by the active request.
- Exports outside the workspace require an explicit destination from the owner in the current task.
- Commits are allowed only after implementation and verification. Pushes require the active release plan or explicit user instruction.
- If unrelated dirty files exist, preserve them and replay the intended patch onto a clean branch.

## Verification

- Run `python -m pytest -q` for release-facing changes.
- Run `python -m compileall src scripts tests` when touching package code, scripts, or tests.
- For privacy-sensitive changes, add a test that proves returned or persisted public artifacts are metadata-only.
- For research/advisory behavior changes, state whether evidence is synthetic, fixture-based, local-only, or live.

## Release Discipline

- Branch from the current remote `main` for release curation.
- Commit only coherent, verified changes.
- Repin through `spark-cli` after the release commit is pushed.
- Do not claim installer readiness until registry pins, provenance checks, installer checks, and hosted installer checks agree.

<!-- SPARK FLEET STANDARD BLOCK v1 — canonical source: spark-compete/fleet/AGENT_GUIDE.md.
     This same block is mirrored into every repo's AGENTS.md and CLAUDE.md. Keep in sync. -->
## How agents work in this repo (Claude, Codex, Gemini — every LLM)

Many agents and sessions work these repos at the same time. There is a tiny **automatic**
workflow that keeps you from colliding. **There are no human-review steps — CI is the only
gate, and it is automatic.** This is coordination, not bureaucracy: claim, work, PR.

### Start of work — one command, then just work normally
```
python3 ~/spark-compete/scripts/fleet.py claim <this-repo-path> <area> <task>
```
You get your **own private worktree + branch + a lease** on `<area>`, so no other agent
edits the same files. It prints the folder to `cd` into. Work there and commit as usual —
a pre-commit hook **auto-checks and renews your lease**; you never manage it by hand.

- `fleet board` — see who's working on what, right now
- `fleet handoff <agent> --note "..."` — pass your work to another agent (with context)
- `fleet release --here` — done (frees the area + removes the worktree)

### Landing work — fully automatic, no human approval
1. Open a PR to the default branch.
2. **CI is the gate.** When it's green, the PR merges. No human reviews anything.
3. Never push directly to the protected branch; never commit from the shared checkout —
   always from your worktree.

### The rules (enforced by CI, not by people)
Full ruleset: **`spark-cli/docs/harness-discipline/`** — `01_RULESET.md` (7 Prime
Directives · Red Lines RL-01..21 · Rules R-01..28) and `07_FLEET_DISCIPLINE.md` (this
workflow). The day-to-day essentials:
- A real fix targets the **root cause**, not a symptom (R-05).
- No regex / keyword / canned answer **owns authority** — it is evidence only (RL-01).
- A failure **surfaces** with a clear reason; it never becomes a fake success (RL-08).
- One worktree per task; PRs only; nothing bypasses the CI gate (F-01 / F-09).

That's the whole contract. The system handles coordination and the gate for you —
automatically, with no human in the loop.
<!-- END SPARK FLEET STANDARD BLOCK v1 -->
