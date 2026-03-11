# Spark Researcher Agent Contract

This repo may be edited by external coding agents such as Codex, Claude, OpenCode, or OpenClaw through Spark Researcher self-edit flows.

## Mission

- make the smallest useful change
- keep the repo legible
- prefer simplification over framework growth
- leave a reviewable diff

## Hard Boundaries

- only edit files inside the mutable targets listed in the self-edit request
- only work inside the copied workspace Spark provides
- do not write outside the workspace
- do not bypass declared guardrails
- do not add hidden services, daemons, or background processes
- do not change git state on behalf of Spark unless the owner explicitly requests it in the current task
- do not push, merge, or open PRs unless the owner explicitly requests it in the current task
- commits are allowed only after the requested changes are implemented and verified
- prefer one small commit per coherent change set
- never amend, rebase, force-push, or rewrite history unless the owner explicitly asks for it

## Change Style

- keep edits local and easy to review
- prefer file artifacts over new infrastructure
- preserve the fixed-evaluator model
- preserve transparent ledger and artifact generation
- avoid speculative abstractions
- avoid large dependency additions unless explicitly required

## Response Contract

- read the request file Spark provides
- apply the requested edits in the workspace only
- write a concise final message for the owner
- exit non-zero if the request cannot be completed safely

## What Spark Owns

Spark, not the backend agent, decides:

- whether a proposal is in scope
- whether blocked changes invalidate the proposal
- whether a reviewed proposal is applied
- whether changes are committed to a branch or `main`
- whether anything is pushed to a remote
