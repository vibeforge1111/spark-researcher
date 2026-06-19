# Self Editing

Self editing is split into `propose` and `apply`.

![Bounded Self-Evolution Loop](assets/self-evolution-loop.svg)

## Propose

- copies the repo into `artifacts/self-edit/<proposal_id>/workspace/`
- writes `request.md`
- optionally runs a configured backend profile such as `codex-exec`
- records stdout, stderr, diff text, allowed changes, and blocked changes

## Apply

- rechecks git cleanliness when configured
- requires a `GovernorDecisionV1` file authorizing this exact proposal id
- requires an allow `AuthorizationDecisionV1` and pre-execution `ToolCallLedgerV1`
- refuses proposals with out-of-scope file changes
- copies only allowed changed files back into the repo
- records a final apply result ledger beside the proposal
- optionally commits to a review branch or directly on `main`
- optionally pushes the resulting branch/commit to `origin`

## Recommended Use

Use an external coding agent that can run with restrictive permissions. Spark Researcher gives you a transparent packet and a narrow apply path, but it does not pretend to be an operating-system sandbox.

Repo-wide backend rules live in `AGENTS.md`. Backend integration expectations live in `docs/AGENT_BACKENDS.md`. This page stays focused on the operator flow.

## Backend Profiles

List built-in profiles:

```powershell
spark-researcher self-edit profiles
```

Use the installed Codex CLI profile:

```powershell
spark-researcher self-edit propose --prompt "..." --backend-profile codex-exec
```

Use another backend with an explicit command override when you do not want the built-in profile:

```powershell
spark-researcher self-edit propose --prompt "..." --backend-command claude --backend-command code --backend-command --print
```

Set repo-wide defaults once:

```powershell
spark-researcher self-edit policy --git-mode branch --push
spark-researcher self-edit policy --git-mode main --push
spark-researcher self-edit policy --git-mode manual --no-push
```

## Git Modes

- `manual`: apply files only, no commit, no push
- `branch`: create a new branch, apply, commit, and optionally push for human review
- `main`: apply directly on the checked-out main branch, commit, and optionally push

Examples:

```powershell
spark-researcher self-edit apply --proposal-id <id> --governor-decision artifacts/self-edit/<id>/governor-decision.json --git-mode branch --push
spark-researcher self-edit apply --proposal-id <id> --governor-decision artifacts/self-edit/<id>/governor-decision.json --git-mode main --push
```
