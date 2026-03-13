# Pokemon Speedrun Tasks

These are the first task families the chip should learn before trying to beat strong runners.

## Intro Tasks

- `intro_boot`
  - get from boot into controllable play quickly
  - preferred state: `benchmarks/states/intro_boot.state`
- `text_mash`
  - clear opening dialogue efficiently
  - preferred state: `benchmarks/states/text_mash.state`
- `menu_fastpath`
  - handle basic start and menu interactions without stalls
  - preferred state: `benchmarks/states/menu_fastpath.state`

## Early Route Tasks

- `leave_bedroom`
  - exit the starting room cleanly
  - preferred state: `benchmarks/states/leave_bedroom.state`
- `oak_lab_entry`
  - reach and enter Oak's lab cleanly
  - preferred state: `benchmarks/states/oak_lab_entry.state`

## Launch Rule

Named speedrun tasks should try to load their preferred state first.

Resolution order:

1. `--load-state`
2. `POKEMON_TASK_STATE_<TASK>`
3. `benchmarks/states/<task>.state`
4. `POKEMON_SAVE_STATE_PATH`

If no state exists, the run must say so clearly and stay conservative about promotion.

## Current Seeding Status

Auto-seedable today from a deterministic cold boot:

- `intro_boot`
- `leave_bedroom`
- `menu_fastpath`
- `text_mash`

Still intentionally missing until stronger scripted routing exists:

- `oak_lab_entry`

## Rule

Do not jump straight from "screen novelty" to "best in the world".

The chip should first beat stable task benchmarks:

1. room exit
2. intro text
3. menu fastpath
4. opening town route fragments
5. early forced interactions

Then it can compose those into longer route segments.
