# External Chip Tasks

This file tracks the remaining work to make Spark treat domain chips as external Desktop-level repos by default, not folders inside `spark-researcher`.

## Completed

- default `chips init` to `C:\Users\USER\Desktop\domain-chip-<domain>`
- normalize omitted or unprefixed chip names to `domain-chip-<domain>`
- resolve relative chip paths under Desktop instead of under `spark-researcher`
- refuse chip targets inside `spark-researcher`
- clean up the refusal path so `chips init` exits with a one-line error instead of a traceback
- add targeted tests for naming, Desktop target resolution, and in-repo target refusal

## Next

- add explicit bootstrap guidance to `chips init` output for standalone chip repos
- document the standalone repo bootstrap flow in the main chip docs
- update prompt-stack docs that still imply chips are created inside the parent repo or require manual path ceremony
- add a small integration test for `chips init` result shape if the CLI output grows
- review any remaining hardcoded examples that still imply in-repo chip placement

## Later

- consider an opt-in `--git-init` mode for standalone chip repos if the workflow proves stable
- consider a helper for adding a remote and pushing a new chip repo without weakening the current explicit-git model
