from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from domain_chip_roblox_development.quality import check_project
from domain_chip_roblox_development.playable import inspect_playable_loop
from domain_chip_roblox_development.scaffold import generate_project
from domain_chip_roblox_development.studio_sync import inspect_project


def _brief() -> dict[str, object]:
    return {
        "game_title": "Skyrail Obby",
        "game_slug": "skyrail-obby",
        "genre": "obby",
        "core_loop": "Jump through checkpoints and reach the finish portal.",
        "target_audience": "Players who like fast skill-based courses.",
        "session_goal": "Finish in under five minutes.",
        "systems": [
            {"name": "Checkpoint", "description": "Save player progress."},
            {"name": "Hazard", "description": "Reset on fail."},
            {"name": "Timer", "description": "Track the player run time."},
        ],
    }


def test_quality_check_passes_on_generated_project(tmp_path: Path) -> None:
    output = tmp_path / "skyrail-obby"
    generate_project(_brief(), output)

    result = check_project(output)

    assert result["passed"] is True
    assert result["errors"] == []
    assert result["checked_lua_file_count"] >= 4
    assert isinstance(result["tool_results"], list)


def test_sync_preflight_reports_ready_for_manual_sync(tmp_path: Path) -> None:
    output = tmp_path / "skyrail-obby"
    generate_project(_brief(), output)

    result = inspect_project(output)

    assert result["status"] == "ready_for_manual_sync"
    assert result["errors"] == []
    assert result["connect_target"] == "localhost:34872"
    assert result["mappings"]
    assert "rojo_check" in result


def test_playable_check_passes_on_generated_obby(tmp_path: Path) -> None:
    output = tmp_path / "skyrail-obby"
    generate_project(_brief(), output)

    result = inspect_playable_loop(output)

    assert result["status"] == "playable_stub_ready"
    assert result["errors"] == []
    assert "checkpoint" in result["required_systems_present"]
    assert "hazard" in result["required_systems_present"]
