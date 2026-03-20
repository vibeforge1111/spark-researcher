# Roblox System Audit

Audit date: 2026-03-21

## Where We Actually Are

This workspace was empty at the start of the audit. There was no prior Roblox chip code, manifest, or implementation plan inside `domain-chip-roblox-development`.

The reusable platform already exists in the parent Spark repo:

- bounded autoloop execution and continuous status tracking
- chip manifest validation and hook invocation
- queue-backed suggestion flow
- packet and watchtower export surfaces

Those core capabilities are enough to host a Roblox chip, but they do not yet execute Roblox development work.

## What Already Exists In Spark Core

### Strong and reusable now

- `autoloop` can run bounded and continuous passes.
- chip hooks can own evaluation, suggestion, packets, and watchtower output.
- generated suggestions can be appended into the frontier queue.
- the fixed-evaluator model is already established.

### Good enough for a planning chip

- roadmap scoring
- gap routing
- packet promotion logic
- watchtower status pages

## Missing Roblox-Specific Services

### Foundation gaps

- no Roblox project template generation
- no Rojo project sync or place-file handling
- no Luau test, lint, or formatting runner
- no asset pipeline for maps, UI, audio, or prefabs

### Evidence gaps

- no local playtest session capture
- no funnel or retention instrumentation
- no benchmark bridge from prototype metrics to promotion

### Release and live-ops gaps

- no publish automation
- no rollback or versioned release policy
- no moderation or safety review surfaces
- no live-service event and economy measurement

## Implication

The immediate goal is not "fully autonomous Roblox game shipping."

The immediate goal is:

1. prove brief -> scaffold
2. prove scaffold -> Studio
3. prove Studio -> playable loop
4. prove playable loop -> playtest evidence
5. only then evaluate release and live-ops lanes

## What This Scaffold Adds

- a valid Spark chip manifest and project config
- a fixed evaluator that scores the current Roblox delivery reality honestly
- bounded next-step suggestions aligned to the missing service order
- docs that convert the audit into an implementation sequence and an operating task plan
