# Roblox Implementation Plan

This is the implementation sequence for turning the Roblox chip from a planning scaffold into an end-to-end game delivery flywheel.

## Phase 0. Flywheel Baseline

Deliver:

- chip scaffold
- fixed evaluator
- audit and task plan docs
- bounded autoloop compatibility

Success condition:

- Spark can evaluate and rank Roblox implementation lanes instead of treating the domain as an empty placeholder.

## Phase 1. Brief To Project Scaffold

Build:

- Roblox game brief schema
- source folder and package conventions
- Rojo-ready project scaffold generator
- asset placeholder contracts

Success condition:

- a bounded prompt can produce a reviewable Roblox project skeleton from a game brief.

## Phase 2. Scaffold To Studio

Build:

- Studio sync workflow
- local run instructions
- minimal place bootstrap
- smoke-test handshake proving generated code can load

Success condition:

- the generated scaffold can be opened and iterated in Roblox Studio with a working boot path.

## Phase 3. Playable Core Loop

Build:

- one low-complexity genre lane, starting with `obby`
- gameplay script composition rules
- local quality gates for Luau
- playable-loop acceptance checks

Success condition:

- the system can repeatedly regenerate and improve a simple playable Roblox loop.

## Phase 4. Playtest Evidence

Build:

- local playtest logging
- event taxonomy for onboarding, fail points, completion, and session timing
- evidence packets that separate benchmark signal from speculation

Success condition:

- prototype quality is judged by observed playtest evidence, not by prompt confidence.

## Phase 5. Vertical Slice And Economy

Build:

- tycoon or simulator expansion lane
- economy configuration surfaces
- balancing heuristics linked to telemetry
- release-readiness checks

Success condition:

- the system can evaluate a richer Roblox loop without skipping evidence or scope discipline.

## Phase 6. Release Ops

Build:

- packaging and publish checklist
- rollback and version policy
- moderation and trust checks
- release packet schema

Success condition:

- the flywheel can prepare a game for release without hiding manual risk.

## Phase 7. Live Ops

Build:

- live event planning
- economy health monitoring
- retention dashboards
- update cadence and post-launch packet flow

Success condition:

- the system can support a live Roblox game after launch with explicit gates and evidence.
