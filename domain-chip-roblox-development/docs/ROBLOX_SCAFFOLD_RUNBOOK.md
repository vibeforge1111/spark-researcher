# Roblox Scaffold Runbook

Use the scaffold generator to turn a brief into a Rojo-ready Roblox project skeleton.

## Command

```powershell
python -m domain_chip_roblox_development.scaffold --brief docs/OBBY_SAMPLE_BRIEF.json --output-dir generated/skyrail-obby
```

Add `--force` if you want to replace an existing generated folder.

## Validation Commands

```powershell
python -m domain_chip_roblox_development.studio_sync --project-dir generated/skyrail-obby
python -m domain_chip_roblox_development.quality --project-dir generated/skyrail-obby
python -m domain_chip_roblox_development.playable --project-dir generated/skyrail-obby
```

## What It Generates

- `default.project.json`
- `game.config.json`
- `README.md`
- `src/server/bootstrap.server.lua`
- `src/client/bootstrap.client.lua`
- `src/replicated/Modules/GameConfig.lua`
- `src/replicated/Modules/LoopDefinition.lua`
- one stub service per declared system
- `docs/STUDIO_SYNC.md`
- `scripts/run_rojo_serve.ps1`
- `scripts/run_rojo_serve.cmd`
- `scripts/run_sync_preflight.ps1`
- `scripts/run_sync_preflight.cmd`
- `scripts/run_quality_gate.ps1`
- `scripts/run_quality_gate.cmd`
- `scripts/run_playable_check.ps1`
- `scripts/run_playable_check.cmd`

## Current Scope

This is Phase 1 only.

It gives the flywheel a real brief-to-project surface, plus preflight and structural quality checks, but it does not yet:

- connect directly to Roblox Studio
- verify gameplay behavior
- collect playtest telemetry
