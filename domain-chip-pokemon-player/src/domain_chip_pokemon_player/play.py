from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmarks import list_speedrun_tasks, resolve_speedrun_task, resolve_task_state_path
from .emulator import (
    EmulatorConfig,
    available_policies,
    configured_bootrom_path,
    configured_rom_path,
    configured_state_path,
    launch_manual_session,
    normalize_window,
    run_policy_session,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="domain-chip-pokemon-player")
    parser.add_argument("--rom", help="Path to a legally owned Pokemon ROM. Falls back to POKEMON_ROM_PATH.")
    parser.add_argument("--bootrom", help="Optional boot ROM path.")
    parser.add_argument("--load-state", help="Optional .state file to load before the run.")
    parser.add_argument("--speedrun-task", help="Named benchmark task. Applies task defaults and preferred save state when available.")
    parser.add_argument("--list-speedrun-tasks", action="store_true", help="Print the task registry and exit.")
    parser.add_argument("--save-state-out", help="Optional path to save a new emulator state.")
    parser.add_argument("--window", default="SDL2", choices=["SDL2", "OpenGL", "GLFW", "null"])
    parser.add_argument("--agent", choices=["manual", *available_policies()])
    parser.add_argument("--task-id", default="intro_boot")
    parser.add_argument("--benchmark-profile")
    parser.add_argument("--steps", type=int)
    parser.add_argument("--ticks-per-action", type=int)
    parser.add_argument("--startup-ticks", type=int)
    parser.add_argument("--action-hold", type=int)
    parser.add_argument("--startup-action", choices=["none", "start", "a", "b"])
    parser.add_argument("--summary-json", help="Optional path to write the session summary JSON.")
    args = parser.parse_args()

    if args.list_speedrun_tasks:
        print(json.dumps({"speedrun_tasks": list_speedrun_tasks()}, indent=2, sort_keys=True))
        return

    rom_path = configured_rom_path(args.rom)
    if rom_path is None:
        raise SystemExit("No ROM configured. Set POKEMON_ROM_PATH or pass --rom <path>.")

    task_id = args.speedrun_task or args.task_id
    task_spec = resolve_speedrun_task(task_id)
    benchmark_profile = args.benchmark_profile or task_spec.benchmark_profile
    agent = args.agent or (task_spec.default_policy_id if args.speedrun_task else "manual")
    startup_action = args.startup_action or task_spec.startup_action
    steps = max(1, args.steps if args.steps is not None else task_spec.steps)
    ticks_per_action = max(1, args.ticks_per_action if args.ticks_per_action is not None else task_spec.tick_stride)
    startup_ticks = max(0, args.startup_ticks if args.startup_ticks is not None else task_spec.startup_ticks)
    action_hold = max(1, args.action_hold if args.action_hold is not None else task_spec.action_hold)
    state_path, state_source = resolve_task_state_path(task_id, explicit_path=args.load_state, generic_path=configured_state_path())

    config = EmulatorConfig(
        rom_path=rom_path,
        window=normalize_window(args.window),
        ticks_per_action=ticks_per_action,
        startup_ticks=startup_ticks,
        action_hold=action_hold,
        bootrom_path=configured_bootrom_path(args.bootrom),
        load_state_path=state_path,
        load_state_source=state_source,
        save_state_out=Path(args.save_state_out).expanduser() if args.save_state_out else None,
    )

    if agent == "manual":
        launch_manual_session(config, task_id=task_id)
        summary = {
            "mode": "manual",
            "rom_path": str(config.rom_path),
            "window": config.window,
            "save_state_out": str(config.save_state_out) if config.save_state_out else "",
            "task_id": task_id,
            "benchmark_profile": benchmark_profile,
            "task_state_path": str(state_path) if state_path else "",
            "task_state_source": state_source,
            "task_notes": task_spec.notes,
        }
    else:
        summary = run_policy_session(
            config,
            policy_id=agent,
            steps=steps,
            startup_action=startup_action,
            task_id=task_id,
            benchmark_profile=benchmark_profile,
        )
        summary.update(
            {
                "mode": "agent",
                "policy_id": agent,
                "task_id": task_id,
                "benchmark_profile": benchmark_profile,
                "rom_path": str(config.rom_path),
                "window": config.window,
                "task_notes": task_spec.notes,
            }
        )

    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.summary_json:
        output_path = Path(args.summary_json).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
