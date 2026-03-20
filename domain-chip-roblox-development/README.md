# domain-chip-roblox-development

`domain-chip-roblox-development` is a Spark domain chip scaffold for building an end-to-end Roblox game flywheel.

Its current honest state is planning-first:

- Spark core already provides bounded autoloop, chip hooks, frontier queueing, packet emission, and watchtower output.
- This chip now encodes the Roblox delivery audit and the next implementation sequence.
- It does not yet connect to Roblox Studio, Rojo, playtest telemetry, publishing, or live-ops services.

## Quick Start

```powershell
cd C:\Users\USER\Desktop\spark-researcher\domain-chip-roblox-development
python -m pip install -e .
$env:PYTHONPATH="C:\Users\USER\Desktop\spark-researcher\src;src"
python -m spark_researcher.cli chips validate --config spark-researcher.project.json
python -m spark_researcher.cli autoloop --config spark-researcher.project.json --command research --rounds 2 --suggest-limit 3
```

## Read First

- `docs/ROBLOX_SYSTEM_AUDIT_2026-03-21.md`
- `docs/ROBLOX_ONE_LOOP_SPEC.md`
- `docs/ROBLOX_IMPLEMENTATION_PLAN.md`
- `docs/ROBLOX_TASK_PLAN.md`
- `docs/ROBLOX_VALIDATION_SNAPSHOT_2026-03-21.md`

## What The Chip Owns

- scoring Roblox delivery candidates against the current platform reality
- suggesting the next bounded implementation probes
- emitting benchmark evidence and boundary packets
- rendering watchtower pages for the Roblox delivery flywheel

## What Is Still Missing

- real Roblox project generation and Rojo sync
- Luau lint, format, and test execution
- playtest analytics and retention instrumentation
- publish, rollback, moderation, and live-ops integration
- real-world benchmark bridges from prototype to release
