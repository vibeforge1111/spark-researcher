# Roblox Task Plan

Active date: 2026-03-21

## Current Objective

Turn the Roblox chip into a real end-to-end delivery flywheel by implementing the lowest missing reliable surface first.

## Operating Rule

Run `autoloop --continuous` only as a bounded prioritizer. Each pass should produce one of:

- a narrower next implementation target
- a new boundary
- a verified improvement in the current lowest lane

## Priority Queue

1. `P0` Scaffold the repo surface. Status: complete.
   Exit condition met: a Roblox project skeleton can now be generated from a brief into a stable folder structure.
2. `P1` Add Studio sync. Status: partial.
   Current state: sync preflight and Rojo handoff scripts exist. Remaining exit condition: scaffolded output can be loaded and iterated in Roblox Studio.
3. `P2` Add Luau quality gates. Status: partial.
   Current state: deterministic structural quality checks exist. Remaining exit condition: formatter, lint, and test commands can reject broken output with real Luau tooling when available.
4. `P3` Add playable-loop acceptance checks. Status: partial.
   Current state: deterministic playable-stub checks exist for the generated obby lane. Remaining exit condition: one obby loop can be regenerated and validated repeatedly in Studio.
5. `P4` Add playtest telemetry.
   Exit when the system can emit evidence about completion, fail points, and session flow.
6. `P5` Add launch-prep and economy lanes.
   Exit when richer genres can be evaluated without skipping evidence.
7. `P6` Add publish, rollback, and live-ops services.
   Exit when release and post-launch work are explicit, reviewable, and measured.

## Continuous Run Shape

Use this bounded loop during active development:

```powershell
$env:PYTHONPATH="C:\Users\USER\Desktop\spark-researcher\src;src"
python -m spark_researcher.cli autoloop --config spark-researcher.project.json --command research --continuous --rounds 2 --suggest-limit 3 --pause-seconds 300
```

## Human Review Triggers

- any proposal that jumps directly to launch or live ops
- any change that introduces hidden background services
- any candidate that claims benchmark grounding without Studio or playtest evidence
- any expansion away from the initial low-complexity genre lane before `obby` is working
