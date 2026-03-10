# Agent Backends

Spark Researcher can use external coding agents as proposal engines.

## Current State

- built-in profile today: `codex-exec`
- other agents can be used right now through `--backend-command` or `SPARK_RESEARCHER_SELF_EDIT_COMMAND`
- Spark still owns review, apply, commit, and push

## Lightweight Policy

- keep the built-in profile list small
- add a new built-in only after a backend is used often and its CLI shape is stable
- prefer `--backend-command` for experimental or less-common agents
- do not let backend-profile sprawl turn into a framework

## Required Backend Behavior

Any backend should:

- run non-interactively
- accept a workspace path and request file
- edit only inside the provided workspace
- respect mutable targets from the request
- produce a concise final message
- exit non-zero on failure

## Backend Contract

Spark gives the backend:

- `{workspace}`: copied writable workspace
- `{request}`: Markdown request with intent, rules, and mutable targets
- `{last_message}`: file path where the backend can leave its final note if the command supports that

Spark expects:

- file edits in the workspace only
- no direct writes to the source repo
- no git promotion actions
- no out-of-scope edits

## Examples

Built-in Codex profile:

```powershell
spark-researcher self-edit propose --prompt "simplify trainer status output" --backend-profile codex-exec
```

Custom backend command:

```powershell
spark-researcher self-edit propose --prompt "..." --backend-command claude --backend-command code --backend-command --print --backend-command --cd --backend-command {workspace} --backend-command "Read {request} and edit only declared mutable targets."
```

Environment override:

```powershell
$env:SPARK_RESEARCHER_SELF_EDIT_COMMAND = 'claude code --print --cd {workspace} "Read {request} and edit only declared mutable targets."'
```
