# Self Editing

Self editing is split into `propose` and `apply`.

## Propose

- copies the repo into `artifacts/self-edit/<proposal_id>/workspace/`
- writes `request.md`
- optionally runs the configured external editor command
- records stdout, stderr, diff text, allowed changes, and blocked changes

## Apply

- rechecks git cleanliness when configured
- refuses proposals with out-of-scope file changes
- copies only allowed changed files back into the repo

## Recommended Use

Use an external coding agent that can run with restrictive permissions. Spark Researcher gives you a transparent packet and a narrow apply path, but it does not pretend to be an operating-system sandbox.

