# domain-chip-pokemon-player

`domain-chip-pokemon-player` is a Spark domain chip scaffold for emulator-connected Pokemon play and speedrun learning.

It is built around `PyBoy`, which gives Python control over a Game Boy emulator and supports:

- opening a ROM in a desktop window
- pressing buttons programmatically
- loading and saving emulator state
- headless evaluation for bounded chip runs

This repo does not ship any ROMs or boot ROMs.
You need to provide your own legally owned Pokemon ROM file.

## What It Does Right Now

- launches a Game Boy emulator window for manual play
- runs simple policy-controlled sessions for autonomous probing
- exposes Spark chip hooks for `evaluate`, `suggest`, `packets`, and `watchtower`
- scores short emulator-connected sessions with a lightweight benchmark surface
- falls back to an explicit heuristic scaffold when no ROM is configured

It is connected enough to play and iterate, but it is not yet a world-class Pokemon speedrun benchmark system.
That would need richer save-state task suites, route objectives, text and menu benchmarks, battle objectives, and study of real speedrun routes.

## Folder Location

Because this was generated inside the current Spark workspace, the chip lives at:

```text
C:\Users\USER\Desktop\spark-researcher\domain-chip-pokemon-player
```

## Install

```powershell
cd C:\Users\USER\Desktop\spark-researcher\domain-chip-pokemon-player
python -m pip install -e .
python -m pip install -e C:\Users\USER\Desktop\spark-researcher
```

## Configure A ROM

Set an environment variable pointing at your ROM:

```powershell
$env:POKEMON_ROM_PATH='C:\path\to\your\Pokemon.gb'
```

Optional:

```powershell
$env:POKEMON_BOOTROM_PATH='C:\path\to\dmg_boot.bin'
$env:POKEMON_SAVE_STATE_PATH='C:\path\to\opening_scene.state'
$env:POKEMON_TASK_STATE_LEAVE_BEDROOM='C:\path\to\leave_bedroom.state'
```

## Play In A Desktop Emulator Window

Manual play:

```powershell
python -m domain_chip_pokemon_player.play --window SDL2 --agent manual
```

Or use the helper script:

```powershell
.\launch_pokemon_player.ps1 -Window SDL2
```

List built-in speedrun tasks:

```powershell
python -m domain_chip_pokemon_player.play --list-speedrun-tasks
```

Seed the first deterministic benchmark states from a clean boot:

```powershell
python -m domain_chip_pokemon_player.seed_states --rom "c:\Users\USER\Downloads\Pokemon - Red Version (USA, Europe) (SGB Enhanced)\Pokemon - Red Version (USA, Europe) (SGB Enhanced).gb"
```

This currently creates:

- `intro_boot.state`
- `leave_bedroom.state`
- `menu_fastpath.state`
- `text_mash.state`

The `oak_lab_entry` route task still remains intentionally unseeded until there is a stronger scripted progression path.

Launch straight into a named speedrun task. If a matching save state exists in `benchmarks/states/` or a `POKEMON_TASK_STATE_<TASK>` env var is set, the task will load from that state automatically:

```powershell
python -m domain_chip_pokemon_player.play --window SDL2 --speedrun-task leave_bedroom
```

## Let The Chip Control The Emulator

Run a short autonomous probe:

```powershell
python -m domain_chip_pokemon_player.play --window SDL2 --agent wander --steps 24
```

Run the task's default speedrun benchmark policy instead of manual mode:

```powershell
python -m domain_chip_pokemon_player.play --window null --speedrun-task leave_bedroom
```

Headless benchmark-style run:

```powershell
python -m domain_chip_pokemon_player.play --window null --agent right_scout --steps 24
```

Override the save state explicitly:

```powershell
python -m domain_chip_pokemon_player.play --window null --speedrun-task text_mash --load-state C:\path\to\text_mash.state
```

## Use It Through Spark

```powershell
$env:PYTHONPATH='C:\Users\USER\Desktop\spark-researcher\src;src'
python -m spark_researcher.cli chips validate --config spark-researcher.project.json
python -m spark_researcher.cli run --config spark-researcher.project.json --command research
python -m spark_researcher.cli candidates suggest --config spark-researcher.project.json --command research
python -m spark_researcher.cli memory sync --config spark-researcher.project.json
python -m spark_researcher.cli obsidian build --config spark-researcher.project.json
```

## Domain Goal

The long-term goal is to make this chip a strong Pokemon speedrun learner by evolving:

- better early-game movement policies
- better text and menu mashing policies
- save-state-backed route tasks
- menu quality and interaction quality tasks
- battle-quality benchmarks
- route doctrine learned from real speedrun guides and leaderboards
- contradiction-aware doctrine about what actually improves play

## Speedrun Study Direction

The chip is now pointed toward studying:

- Pokemon Red/Blue leaderboards and guide surfaces on Speedrun.com
- route and menu optimizations from the Pokemon speedrunning community
- disassembly-level game knowledge from `pret/pokered`
- repeatable save-state benchmarks derived from real opening speedrun fragments

## Save-State Benchmarks

Named tasks now carry benchmark defaults for:

- preferred profile
- preferred policy
- preferred tick stride
- preferred startup timing
- preferred save-state path

Expected state locations live under `benchmarks/states/`:

- `intro_boot.state`
- `leave_bedroom.state`
- `oak_lab_entry.state`
- `text_mash.state`
- `menu_fastpath.state`

If a task state is missing, the chip falls back honestly and reports that the benchmark is not yet save-state-backed.

Preview screenshots for seeded states are written to `benchmarks/previews/`.

## Next Strong Steps

1. Add a stable save state near a repeatable scene.
2. Define task-level speedrun benchmarks such as "leave the opening room", "enter Oak's lab", or "clear an intro text sequence".
3. Add battle, menu, and route-specific evaluators.
4. Promote doctrine only after repeated save-state-backed wins.
