from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from domain_chip_roblox_development.scaffold import generate_project


def test_generate_project_writes_expected_files(tmp_path: Path) -> None:
    brief = {
        "game_title": "Skyrail Obby",
        "game_slug": "skyrail-obby",
        "genre": "obby",
        "core_loop": "Jump through checkpoints and reach the finish portal.",
        "target_audience": "Players who like fast skill-based courses.",
        "session_goal": "Finish in under five minutes.",
        "systems": [
            {"name": "Checkpoint", "description": "Save player progress."},
            {"name": "Hazard", "description": "Reset on fail."},
        ],
    }

    output = tmp_path / "skyrail-obby"
    result = generate_project(brief, output)

    assert result["game_slug"] == "skyrail-obby"
    assert (output / "default.project.json").exists()
    assert (output / "game.config.json").exists()
    assert (output / "src" / "server" / "bootstrap.server.lua").exists()
    assert (output / "src" / "client" / "bootstrap.client.lua").exists()
    assert (output / "src" / "server" / "Services" / "CheckpointService.lua").exists()
    assert (output / "src" / "server" / "Services" / "HazardService.lua").exists()
    assert (output / "docs" / "STUDIO_SYNC.md").exists()
    assert (output / "scripts" / "run_rojo_serve.ps1").exists()
    assert (output / "scripts" / "run_rojo_serve.cmd").exists()

    config = json.loads((output / "game.config.json").read_text(encoding="utf-8"))
    assert config["game_title"] == "Skyrail Obby"
    assert config["systems"][0]["service_name"] == "CheckpointService"


def test_generate_project_rejects_non_empty_directory_without_force(tmp_path: Path) -> None:
    output = tmp_path / "occupied"
    output.mkdir()
    (output / "existing.txt").write_text("busy", encoding="utf-8")

    brief = {
        "game_title": "Busy Game",
        "genre": "obby",
        "core_loop": "Run forward.",
        "target_audience": "Everyone.",
        "session_goal": "Reach the end.",
    }

    try:
        generate_project(brief, output)
    except FileExistsError:
        pass
    else:
        raise AssertionError("Expected FileExistsError for non-empty output directory.")
