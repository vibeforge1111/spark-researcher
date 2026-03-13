from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .benchmarks import resolve_speedrun_task

try:
    from pyboy import PyBoy
except ImportError:  # pragma: no cover
    PyBoy = None  # type: ignore[assignment]


DEFAULT_POLICY = "wander"
DEFAULT_TASK = "intro_boot"
DEFAULT_PROFILE = "speedrun_intro"
POLICY_LIBRARY: dict[str, list[str]] = {
    "wander": ["up", "right", "down", "left", "a", "b"],
    "right_scout": ["right", "right", "up", "a", "right", "down"],
    "menu_mash": ["start", "a", "b", "down", "a", "start"],
    "edge_scan": ["up", "up", "right", "right", "down", "left"],
    "start_then_wander": ["start", "a", "right", "up", "left", "down"],
}
STARTUP_ACTIONS = {"none", "start", "a", "b"}
WINDOW_TYPES = {"SDL2", "OpenGL", "GLFW", "null"}
TASK_BONUS = {
    "intro_boot": 0.01,
    "leave_bedroom": 0.03,
    "oak_lab_entry": 0.05,
    "text_mash": 0.02,
    "menu_fastpath": 0.025,
}
PROFILE_BONUS = {
    "speedrun_intro": 0.03,
    "speedrun_menuing": 0.025,
    "speedrun_route": 0.04,
}


@dataclass(frozen=True)
class EmulatorConfig:
    rom_path: Path
    window: str = "null"
    ticks_per_action: int = 24
    startup_ticks: int = 120
    action_hold: int = 4
    bootrom_path: Path | None = None
    load_state_path: Path | None = None
    load_state_source: str = "missing"
    save_state_out: Path | None = None


def pyboy_available() -> bool:
    return PyBoy is not None


def configured_rom_path(explicit: str | None = None) -> Path | None:
    raw = (explicit or os.environ.get("POKEMON_ROM_PATH") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.exists() else None


def configured_bootrom_path(explicit: str | None = None) -> Path | None:
    raw = (explicit or os.environ.get("POKEMON_BOOTROM_PATH") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.exists() else None


def configured_state_path(explicit: str | None = None) -> Path | None:
    raw = (explicit or os.environ.get("POKEMON_SAVE_STATE_PATH") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.exists() else None


def emulator_status() -> dict[str, Any]:
    rom_path = configured_rom_path()
    return {
        "pyboy_available": pyboy_available(),
        "rom_configured": rom_path is not None,
        "rom_path": str(rom_path) if rom_path else "",
        "bootrom_configured": configured_bootrom_path() is not None,
        "save_state_configured": configured_state_path() is not None,
    }


def available_policies() -> list[str]:
    return sorted(POLICY_LIBRARY)


def normalize_policy(policy_id: str) -> str:
    return policy_id if policy_id in POLICY_LIBRARY else DEFAULT_POLICY


def normalize_window(window: str) -> str:
    return window if window in WINDOW_TYPES else "null"


def _expanded_actions(policy_id: str, steps: int, startup_action: str) -> list[str]:
    base = POLICY_LIBRARY[normalize_policy(policy_id)]
    actions: list[str] = []
    if startup_action in STARTUP_ACTIONS and startup_action != "none":
        actions.append(startup_action)
    while len(actions) < steps:
        actions.extend(base)
    return actions[:steps]


def deterministic_scaffold(
    policy_id: str,
    startup_action: str,
    ticks_per_action: int,
    task_id: str = DEFAULT_TASK,
    benchmark_profile: str = DEFAULT_PROFILE,
) -> dict[str, Any]:
    task_spec = resolve_speedrun_task(task_id)
    base_score = 0.34
    policy_bonus = {
        "wander": 0.18,
        "right_scout": 0.24,
        "menu_mash": 0.11,
        "edge_scan": 0.16,
        "start_then_wander": 0.2,
    }.get(normalize_policy(policy_id), 0.12)
    startup_bonus = {"none": 0.0, "start": 0.04, "a": 0.03, "b": 0.01}.get(startup_action, 0.0)
    stride_bonus = 0.03 if ticks_per_action == 24 else 0.02 if ticks_per_action == 36 else 0.01
    task_bonus = TASK_BONUS.get(task_id, 0.0)
    profile_bonus = PROFILE_BONUS.get(benchmark_profile, 0.0)
    progress = round(min(0.95, base_score + policy_bonus + startup_bonus + stride_bonus + task_bonus + profile_bonus), 4)
    exploration = round(min(0.95, 0.35 + policy_bonus * 0.7 + stride_bonus + task_bonus * 0.5), 4)
    interaction = round(min(0.95, 0.2 + startup_bonus + (0.08 if "a" in POLICY_LIBRARY[normalize_policy(policy_id)] else 0.0) + profile_bonus * 0.4), 4)
    novelty = round(min(0.95, 0.28 + policy_bonus * 0.8), 4)
    return {
        "pokemon_progress_score": progress,
        "exploration_score": exploration,
        "interaction_score": interaction,
        "screen_novelty": novelty,
        "emulator_connected": 0.0,
        "verdict_confidence": round(min(0.9, 0.42 + progress * 0.45), 4),
        "verdict": "defer",
        "recommended_next_step": "connect_emulator_and_load_rom",
        "mechanism": f"The speedrun scaffold for `{task_id}` under `{benchmark_profile}` looks directionally useful, but the emulator is not connected yet.",
        "boundary": "Without a legal ROM and emulator session, this remains a heuristic frontier estimate.",
        "comparison_class": "heuristic_frontier",
        "evidence_lane": "exploratory_frontier",
        "action_history": _expanded_actions(policy_id, 8, startup_action),
        "frame_hashes": [],
        "task_id": task_id,
        "benchmark_profile": benchmark_profile,
        "task_state_loaded": False,
        "task_state_source": "missing",
        "task_notes": task_spec.notes,
    }


def _frame_hash(pyboy: Any) -> str:
    return hashlib.blake2b(bytes(pyboy.screen.raw_buffer), digest_size=8).hexdigest()


def _movement_ratio(actions: list[str]) -> float:
    if not actions:
        return 0.0
    movement = sum(1 for item in actions if item in {"up", "down", "left", "right"})
    return round(movement / len(actions), 4)


def _interaction_ratio(actions: list[str]) -> float:
    if not actions:
        return 0.0
    interactions = sum(1 for item in actions if item in {"a", "b", "start", "select"})
    return round(interactions / len(actions), 4)


def run_policy_session(
    config: EmulatorConfig,
    *,
    policy_id: str,
    steps: int,
    startup_action: str,
    task_id: str = DEFAULT_TASK,
    benchmark_profile: str = DEFAULT_PROFILE,
) -> dict[str, Any]:
    if PyBoy is None:
        raise RuntimeError("PyBoy is not installed.")
    if not config.rom_path.exists():
        raise RuntimeError(f"ROM not found: {config.rom_path}")

    task_spec = resolve_speedrun_task(task_id)
    task_state_path = config.load_state_path if config.load_state_path and config.load_state_path.exists() else None
    task_state_source = config.load_state_source if task_state_path else "missing"
    pyboy = PyBoy(
        str(config.rom_path),
        window=normalize_window(config.window),
        bootrom=str(config.bootrom_path) if config.bootrom_path else None,
        sound_emulated=False,
    )
    try:
        if normalize_window(config.window) == "null":
            pyboy.set_emulation_speed(0)
        if task_state_path and task_state_path.exists():
            with task_state_path.open("rb") as handle:
                pyboy.load_state(handle)
        startup_ticks = 0 if task_state_path else config.startup_ticks
        if startup_ticks > 0:
            pyboy.tick(startup_ticks, render=normalize_window(config.window) != "null", sound=False)

        actions = _expanded_actions(policy_id, steps, startup_action)
        frame_hashes: list[str] = []
        for action in actions:
            if action != "none":
                pyboy.button(action, delay=max(1, config.action_hold))
            pyboy.tick(config.ticks_per_action, render=normalize_window(config.window) != "null", sound=False)
            frame_hashes.append(_frame_hash(pyboy))

        if config.save_state_out:
            config.save_state_out.parent.mkdir(parents=True, exist_ok=True)
            with config.save_state_out.open("wb") as handle:
                pyboy.save_state(handle)

        unique_actions = len({item for item in actions if item != "none"})
        unique_frames = len(set(frame_hashes))
        action_diversity = round(unique_actions / 7.0, 4)
        screen_novelty = round(unique_frames / max(len(actions), 1), 4)
        movement_score = _movement_ratio(actions)
        interaction_score = _interaction_ratio(actions)
        task_bonus = TASK_BONUS.get(task_id, 0.0)
        profile_bonus = PROFILE_BONUS.get(benchmark_profile, 0.0)
        progress = round(
            min(
                0.99,
                screen_novelty * 0.4 + action_diversity * 0.18 + movement_score * 0.18 + interaction_score * 0.14 + task_bonus + profile_bonus,
            ),
            4,
        )
        verdict = "approve" if progress >= 0.63 else "defer" if progress >= 0.48 else "reject"
        next_step = (
            "save_state_and_expand_policy"
            if verdict == "approve"
            else "load_save_state_for_stronger_probe"
            if verdict == "defer"
            else "tighten_policy_and_retry"
        )
        return {
            "pokemon_progress_score": progress,
            "exploration_score": movement_score,
            "interaction_score": interaction_score,
            "screen_novelty": screen_novelty,
            "emulator_connected": 1.0,
            "verdict_confidence": round(min(0.98, 0.45 + progress * 0.5), 4),
            "verdict": verdict,
            "recommended_next_step": next_step,
            "mechanism": f"The emulator is connected and the `{task_id}` speedrun policy is being scored from real screen-change and action-diversity signals.",
            "boundary": "This is still a shallow benchmark. It does not yet prove gym progression, battle quality, or long-horizon route competence.",
            "comparison_class": "benchmark_grounded",
            "evidence_lane": "benchmark_grounded",
            "action_history": actions,
            "frame_hashes": frame_hashes,
            "task_id": task_id,
            "benchmark_profile": benchmark_profile,
            "task_state_loaded": bool(task_state_path),
            "task_state_path": str(task_state_path) if task_state_path else "",
            "task_state_source": task_state_source,
            "task_notes": task_spec.notes,
        }
    finally:
        pyboy.stop()


def launch_manual_session(config: EmulatorConfig, task_id: str = DEFAULT_TASK) -> None:
    if PyBoy is None:
        raise RuntimeError("PyBoy is not installed.")
    if not config.rom_path.exists():
        raise RuntimeError(f"ROM not found: {config.rom_path}")
    task_state_path = config.load_state_path if config.load_state_path and config.load_state_path.exists() else None
    window = normalize_window(config.window)
    if window != "null":
        args = [sys.executable, "-m", "pyboy", str(config.rom_path), "-w", window, "--no-sound-emulation"]
        if config.bootrom_path:
            args.extend(["-b", str(config.bootrom_path)])
        if task_state_path and task_state_path.exists():
            args.extend(["-l", str(task_state_path)])
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "start", "", *args], check=True)
            return
        subprocess.run(args, check=True)
        return

    pyboy = PyBoy(
        str(config.rom_path),
        window=window,
        bootrom=str(config.bootrom_path) if config.bootrom_path else None,
        sound_emulated=False,
    )
    try:
        pyboy.set_emulation_speed(0)
        if task_state_path and task_state_path.exists():
            with task_state_path.open("rb") as handle:
                pyboy.load_state(handle)
        while pyboy.tick(1, render=False, sound=False):
            pass
        if config.save_state_out:
            config.save_state_out.parent.mkdir(parents=True, exist_ok=True)
            with config.save_state_out.open("wb") as handle:
                pyboy.save_state(handle)
    finally:
        pyboy.stop()
