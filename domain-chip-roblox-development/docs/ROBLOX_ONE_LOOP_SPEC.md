# Roblox One-Loop Spec

## Intent

Build a bounded flywheel that can take a Roblox game from brief to playable prototype, then to release readiness, without pretending that planning alone is production.

The chip should learn:

- which game scopes are small enough to automate first
- which delivery surfaces are still manual
- which evidence lanes are trustworthy enough to promote
- when the next step is implementation, not more planning

## Current Honest State

As of 2026-03-21:

- Spark core already has the bounded loop, ledger, queue, packet, and watchtower primitives.
- This workspace did not have an existing Roblox implementation before this scaffold.
- The limiting factor is not planning. It is the absence of Roblox-specific execution and evidence services.

## One Governing Loop

1. Refresh the current system state.
2. Identify the lowest missing reliable surface.
3. Run the smallest lane that closes that gap.
4. Emit evidence, boundaries, and next probes.
5. Repeat with `autoloop --continuous`, but keep each pass bounded.

## Lane Order

1. `design_packets`
2. `repo_scaffold`
3. `studio_sync`
4. `playtest_telemetry`
5. `economy_tuning` and `launch_prep`
6. `live_service`

## Rules

- Do not expand genre scope before the low-complexity obby lane works.
- Do not claim end-to-end autonomy until Studio sync and playtest telemetry exist.
- Do not move into launch or live ops from synthetic evidence alone.
- Do not let ambitious game concepts hide missing infra.
- Prefer one small, playable loop over a large partially automated design.
