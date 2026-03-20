# Roblox Scaffold Runbook

Use the scaffold generator to turn a brief into a Rojo-ready Roblox project skeleton.

## Command

```powershell
python -m domain_chip_roblox_development.scaffold --brief docs/OBBY_SAMPLE_BRIEF.json --output-dir generated/skyrail-obby
```

Add `--force` if you want to replace an existing generated folder.

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

## Current Scope

This is Phase 1 only.

It gives the flywheel a real brief-to-project surface, but it does not yet:

- sync with Roblox Studio
- run Luau quality gates
- verify gameplay behavior
- collect playtest telemetry
