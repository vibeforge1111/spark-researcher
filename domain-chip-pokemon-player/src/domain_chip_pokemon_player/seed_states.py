from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyboy import PyBoy

from .benchmarks import default_task_preview_path, default_task_state_path
from .emulator import configured_rom_path


@dataclass(frozen=True)
class SeedAction:
    button: str
    ticks: int
    delay: int = 2


@dataclass(frozen=True)
class SeedPlan:
    task_id: str
    startup_ticks: int
    actions: tuple[SeedAction, ...]
    notes: str


def _repeat(button: str, ticks: int, count: int, delay: int = 2) -> tuple[SeedAction, ...]:
    return tuple(SeedAction(button, ticks, delay=delay) for _ in range(count))


SEEDABLE_TASKS: dict[str, SeedPlan] = {
    "intro_boot": SeedPlan(
        task_id="intro_boot",
        startup_ticks=1500,
        actions=(),
        notes="Stable title-area boot screen from a deterministic cold boot.",
    ),
    "menu_fastpath": SeedPlan(
        task_id="menu_fastpath",
        startup_ticks=1500,
        actions=(
            SeedAction("a", 60),
            SeedAction("a", 30),
            SeedAction("a", 60),
        ),
        notes="Early deterministic post-title menu transition used as a first menu benchmark seed.",
    ),
    "text_mash": SeedPlan(
        task_id="text_mash",
        startup_ticks=1500,
        actions=(
            SeedAction("a", 60),
            SeedAction("a", 30),
            SeedAction("a", 60),
            SeedAction("down", 20),
            SeedAction("a", 60),
        ),
        notes="Early deterministic dialogue-ish transition scene used as a first text-mash benchmark seed.",
    ),
    "leave_bedroom": SeedPlan(
        task_id="leave_bedroom",
        startup_ticks=3000,
        actions=(
            *_repeat("a", 120, 5),
            SeedAction("down", 40),
            *_repeat("a", 120, 5),
            SeedAction("down", 40),
            *_repeat("a", 120, 6),
            *_repeat("a", 90, 3),
            SeedAction("down", 5),
            SeedAction("a", 60),
            *_repeat("a", 90, 9),
            SeedAction("down", 5),
            SeedAction("a", 60),
            *_repeat("a", 90, 19),
        ),
        notes="Deterministic intro-to-bedroom script with preset names selected and the first room ready for route probing.",
    ),
}


def _preview_path(task_id: str) -> Path:
    return default_task_preview_path(task_id)


def _render_to_plan(pyboy: PyBoy, plan: SeedPlan) -> None:
    if plan.startup_ticks > 0:
        pyboy.tick(plan.startup_ticks, True, False)
    for action in plan.actions:
        pyboy.button(action.button, delay=action.delay)
        pyboy.tick(action.ticks, True, False)


def seed_task(rom_path: Path, plan: SeedPlan, *, force: bool = False) -> dict[str, Any]:
    state_path = default_task_state_path(plan.task_id)
    if state_path is None:
        raise RuntimeError(f"No default state path is registered for task `{plan.task_id}`.")
    preview_path = _preview_path(plan.task_id)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)

    if state_path.exists() and not force:
        return {
            "task_id": plan.task_id,
            "state_path": str(state_path),
            "preview_path": str(preview_path),
            "created": False,
            "skipped": True,
            "notes": plan.notes,
            "reason": "state_exists",
        }

    pyboy = PyBoy(str(rom_path), window="null", sound_emulated=False)
    try:
        _render_to_plan(pyboy, plan)
        with state_path.open("wb") as handle:
            pyboy.save_state(handle)
        pyboy.screen.image.save(preview_path)
    finally:
        pyboy.stop()

    return {
        "task_id": plan.task_id,
        "state_path": str(state_path),
        "preview_path": str(preview_path),
        "created": True,
        "skipped": False,
        "notes": plan.notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="domain_chip_pokemon_player.seed_states")
    parser.add_argument("--rom", help="Path to the Pokemon ROM. Falls back to POKEMON_ROM_PATH.")
    parser.add_argument("--task-id", action="append", help="Optional task id to seed. May be repeated.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing state files.")
    args = parser.parse_args()

    rom_path = configured_rom_path(args.rom)
    if rom_path is None:
        raise SystemExit("No ROM configured. Set POKEMON_ROM_PATH or pass --rom <path>.")

    requested = args.task_id or list(SEEDABLE_TASKS)
    results: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for task_id in requested:
        plan = SEEDABLE_TASKS.get(task_id)
        if plan is None:
            skipped.append({"task_id": task_id, "reason": "not_yet_seedable"})
            continue
        results.append(seed_task(rom_path, plan, force=args.force))

    print(json.dumps({"seeded": results, "skipped": skipped}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
