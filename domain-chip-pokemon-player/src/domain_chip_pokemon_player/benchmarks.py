from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SpeedrunTaskSpec:
    task_id: str
    display_name: str
    benchmark_profile: str
    default_policy_id: str
    startup_action: str
    tick_stride: int
    startup_ticks: int
    action_hold: int
    steps: int
    state_path: str | None
    notes: str


TASK_SPECS: dict[str, SpeedrunTaskSpec] = {
    "intro_boot": SpeedrunTaskSpec(
        task_id="intro_boot",
        display_name="Intro Boot",
        benchmark_profile="speedrun_intro",
        default_policy_id="menu_mash",
        startup_action="start",
        tick_stride=12,
        startup_ticks=90,
        action_hold=3,
        steps=18,
        state_path="benchmarks/states/intro_boot.state",
        notes="Boot from the opening scene and mash into a repeatable intro benchmark.",
    ),
    "leave_bedroom": SpeedrunTaskSpec(
        task_id="leave_bedroom",
        display_name="Leave Bedroom",
        benchmark_profile="speedrun_route",
        default_policy_id="right_scout",
        startup_action="none",
        tick_stride=24,
        startup_ticks=0,
        action_hold=4,
        steps=20,
        state_path="benchmarks/states/leave_bedroom.state",
        notes="Start from a positioned state in the bedroom and optimize room exit quality.",
    ),
    "oak_lab_entry": SpeedrunTaskSpec(
        task_id="oak_lab_entry",
        display_name="Oak Lab Entry",
        benchmark_profile="speedrun_route",
        default_policy_id="edge_scan",
        startup_action="none",
        tick_stride=24,
        startup_ticks=0,
        action_hold=4,
        steps=24,
        state_path="benchmarks/states/oak_lab_entry.state",
        notes="Benchmark pathing into Oak's lab from a stable map-entry state.",
    ),
    "text_mash": SpeedrunTaskSpec(
        task_id="text_mash",
        display_name="Text Mash",
        benchmark_profile="speedrun_menuing",
        default_policy_id="menu_mash",
        startup_action="start",
        tick_stride=12,
        startup_ticks=0,
        action_hold=2,
        steps=16,
        state_path="benchmarks/states/text_mash.state",
        notes="Stress dialogue throughput from a stable text box save state.",
    ),
    "menu_fastpath": SpeedrunTaskSpec(
        task_id="menu_fastpath",
        display_name="Menu Fastpath",
        benchmark_profile="speedrun_menuing",
        default_policy_id="start_then_wander",
        startup_action="a",
        tick_stride=12,
        startup_ticks=0,
        action_hold=2,
        steps=16,
        state_path="benchmarks/states/menu_fastpath.state",
        notes="Benchmark short menu-open and confirm sequences from a seeded state.",
    ),
}


def chip_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_task_preview_path(task_id: str) -> Path:
    return chip_root() / "benchmarks" / "previews" / f"{task_id}.png"


def list_speedrun_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for spec in TASK_SPECS.values():
        payload = asdict(spec)
        path = default_task_state_path(spec.task_id)
        preview_path = default_task_preview_path(spec.task_id)
        payload["state_path"] = str(path) if path else ""
        payload["state_available"] = bool(path and path.exists())
        payload["preview_path"] = str(preview_path)
        payload["preview_available"] = preview_path.exists()
        payload["task_state_env_var"] = task_state_env_var(spec.task_id)
        tasks.append(payload)
    return tasks


def resolve_speedrun_task(task_id: str | None) -> SpeedrunTaskSpec:
    if task_id and task_id in TASK_SPECS:
        return TASK_SPECS[task_id]
    return TASK_SPECS["intro_boot"]


def task_state_env_var(task_id: str) -> str:
    return f"POKEMON_TASK_STATE_{task_id.upper()}"


def default_task_state_path(task_id: str) -> Path | None:
    spec = resolve_speedrun_task(task_id)
    if not spec.state_path:
        return None
    return chip_root() / spec.state_path


def resolve_task_state_path(task_id: str, explicit_path: str | None = None, generic_path: Path | None = None) -> tuple[Path | None, str]:
    if explicit_path:
        explicit = Path(explicit_path).expanduser()
        if explicit.exists():
            return explicit, "explicit"
    env_raw = os.environ.get(task_state_env_var(task_id), "").strip()
    if env_raw:
        env_path = Path(env_raw).expanduser()
        if env_path.exists():
            return env_path, "task_env"
    default_path = default_task_state_path(task_id)
    if default_path and default_path.exists():
        return default_path, "task_registry"
    if generic_path and generic_path.exists():
        return generic_path, "generic_env"
    return None, "missing"
