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
- do not write outside the workspace unless the owner explicitly requests exporting or moving a completed self-contained artifact to a declared destination
- do not create, recreate, copy, or move any `domain-chip-*` repo inside the `spark-researcher` repo tree; domain chips must live as sibling Desktop repos such as `C:\Users\USER\Desktop\domain-chip-foo`
- do not bypass declared guardrails
- do not add hidden services, daemons, or background processes
- once the owner has enabled autonomous shipping, git state changes needed to complete the task are allowed after the requested changes are implemented and verified
- once the owner has enabled autonomous shipping, push verified coherent feature commits automatically unless the owner says to pause
- commits are allowed only after the requested changes are implemented and verified
- prefer one small commit per coherent change set
- do not merge, open PRs, amend, rebase, force-push, or rewrite history unless the owner explicitly asks for it

## Owner-Approved Export Exception

- exports or moves outside the workspace are allowed only after the requested implementation is complete and verified
- the destination must be explicitly named by the owner in the current task
- prefer exporting self-contained folders such as standalone domain chips
- do not use the exception for broad repo rewrites, hidden copies, or undeclared side effects
- if the active runtime sandbox forbids the write, report that the repo policy allows it but the current session still cannot perform it

## Change Style

- keep edits local and easy to review
- prefer file artifacts over new infrastructure
- preserve the fixed-evaluator model
- preserve transparent ledger and artifact generation
- avoid speculative abstractions
- avoid large dependency additions unless explicitly required

## Response Contract

- read the request file Spark provides
- apply the requested edits in the workspace only unless the owner-approved export exception applies
- write a concise final message for the owner
- exit non-zero if the request cannot be completed safely

## What Spark Owns

Spark, not the backend agent, decides:

- whether a proposal is in scope
- whether blocked changes invalidate the proposal
- whether a reviewed proposal is applied
- whether changes are committed to a branch or `main`
- whether anything is pushed to a remote

