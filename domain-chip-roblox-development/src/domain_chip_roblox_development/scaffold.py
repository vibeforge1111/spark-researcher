from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return cleaned.strip("-") or "roblox-game"


def _pascal(value: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", value.strip())
    cleaned = "".join(part[:1].upper() + part[1:] for part in parts if part)
    return cleaned or "Game"


def _lua_key(key: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return key
    return f'["{key}"]'


def _lua_value(value: Any, indent: int = 0) -> str:
    pad = " " * indent
    next_pad = " " * (indent + 2)
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    if isinstance(value, list):
        if not value:
            return "{}"
        lines = ["{"]
        for item in value:
            lines.append(f"{next_pad}{_lua_value(item, indent + 2)},")
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = ["{"]
        for key, item in value.items():
            lines.append(f"{next_pad}{_lua_key(str(key))} = {_lua_value(item, indent + 2)},")
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    raise TypeError(f"Unsupported value for Lua conversion: {type(value)!r}")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _require_string(brief: dict[str, Any], key: str) -> str:
    value = str(brief.get(key, "")).strip()
    if not value:
        raise ValueError(f"Brief field `{key}` is required.")
    return value


def _normalize_brief(brief: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(brief, dict):
        raise ValueError("Brief must be a JSON object.")
    game_title = _require_string(brief, "game_title")
    genre = _require_string(brief, "genre")
    core_loop = _require_string(brief, "core_loop")
    audience = _require_string(brief, "target_audience")
    session_goal = _require_string(brief, "session_goal")
    game_slug = _slug(str(brief.get("game_slug", "")) or game_title)
    systems = brief.get("systems", [])
    if not isinstance(systems, list):
        raise ValueError("Brief field `systems` must be a list when present.")
    normalized_systems: list[dict[str, str]] = []
    for raw in systems:
        if not isinstance(raw, dict):
            raise ValueError("Each `systems` entry must be an object.")
        name = _require_string(raw, "name")
        description = _require_string(raw, "description")
        normalized_systems.append(
            {
                "name": name,
                "description": description,
                "service_name": _pascal(name) + "Service",
                "module_name": _pascal(name),
            }
        )
    if not normalized_systems:
        normalized_systems = [
            {
                "name": "Checkpoint",
                "description": "Save player progress and restart from the latest checkpoint.",
                "service_name": "CheckpointService",
                "module_name": "Checkpoint",
            },
            {
                "name": "Hazard",
                "description": "Reset players when they fail the core movement challenge.",
                "service_name": "HazardService",
                "module_name": "Hazard",
            },
        ]

    world = brief.get("world", {})
    if world is None:
        world = {}
    if not isinstance(world, dict):
        raise ValueError("Brief field `world` must be an object when present.")
    monetization = brief.get("monetization", {})
    if monetization is None:
        monetization = {}
    if not isinstance(monetization, dict):
        raise ValueError("Brief field `monetization` must be an object when present.")

    return {
        "game_title": game_title,
        "game_slug": game_slug,
        "genre": genre,
        "core_loop": core_loop,
        "target_audience": audience,
        "session_goal": session_goal,
        "world": world,
        "monetization": monetization,
        "systems": normalized_systems,
    }


def _project_tree() -> dict[str, Any]:
    return {
        "name": "$game_title",
        "tree": {
            "$className": "DataModel",
            "ReplicatedStorage": {
                "Shared": {"$path": "src/replicated"},
            },
            "ServerScriptService": {
                "Server": {"$path": "src/server"},
            },
            "StarterPlayer": {
                "StarterPlayerScripts": {
                    "Client": {"$path": "src/client"},
                }
            },
            "Workspace": {
                "Map": {"$path": "src/workspace"},
            },
        },
    }


def _readme(brief: dict[str, Any]) -> str:
    systems = "\n".join(
        f"- `{item['service_name']}`: {item['description']}"
        for item in brief["systems"]
    )
    return "\n".join(
        [
            f"# {brief['game_title']}",
            "",
            "Generated by `domain-chip-roblox-development`.",
            "",
            "## Brief",
            "",
            f"- genre: `{brief['genre']}`",
            f"- target_audience: `{brief['target_audience']}`",
            f"- session_goal: {brief['session_goal']}",
            f"- core_loop: {brief['core_loop']}",
            "",
            "## Generated Systems",
            "",
            systems,
            "",
            "## Next Steps",
            "",
            "1. Open the project in Rojo and Roblox Studio.",
            "2. Replace stub logic with real movement, fail, and reward loops.",
            "3. Add playtest instrumentation before expanding scope.",
        ]
    )


def _game_config_lua(brief: dict[str, Any]) -> str:
    payload = {
        "gameTitle": brief["game_title"],
        "gameSlug": brief["game_slug"],
        "genre": brief["genre"],
        "coreLoop": brief["core_loop"],
        "targetAudience": brief["target_audience"],
        "sessionGoal": brief["session_goal"],
        "world": brief["world"],
        "monetization": brief["monetization"],
        "systems": [
            {
                "name": item["name"],
                "description": item["description"],
                "serviceName": item["service_name"],
            }
            for item in brief["systems"]
        ],
    }
    return "\n".join(
        [
            "--!strict",
            "",
            "local GameConfig = " + _lua_value(payload),
            "",
            "return GameConfig",
        ]
    )


def _loop_definition_lua(brief: dict[str, Any]) -> str:
    payload = {
        "coreLoop": brief["core_loop"],
        "sessionGoal": brief["session_goal"],
        "steps": [item["name"] for item in brief["systems"]],
    }
    return "\n".join(
        [
            "--!strict",
            "",
            "local LoopDefinition = " + _lua_value(payload),
            "",
            "return LoopDefinition",
        ]
    )


def _server_bootstrap(brief: dict[str, Any]) -> str:
    requires = "\n".join(
        f"local {item['service_name']} = require(script.Parent.Services.{item['service_name']})"
        for item in brief["systems"]
    )
    starts = "\n".join(
        f"{item['service_name']}.start(config)"
        for item in brief["systems"]
    )
    return "\n".join(
        [
            "--!strict",
            "",
            f"-- Generated bootstrap for {brief['game_title']}",
            "local ReplicatedStorage = game:GetService(\"ReplicatedStorage\")",
            "local config = require(ReplicatedStorage.Shared.Modules.GameConfig)",
            "",
            requires,
            "",
            starts,
        ]
    )


def _client_bootstrap(brief: dict[str, Any]) -> str:
    return "\n".join(
        [
            "--!strict",
            "",
            f"-- Client bootstrap for {brief['game_title']}",
            "local ReplicatedStorage = game:GetService(\"ReplicatedStorage\")",
            "local config = require(ReplicatedStorage.Shared.Modules.GameConfig)",
            "",
            "print(\"Loaded client for\", config.gameTitle)",
            "print(\"Session goal:\", config.sessionGoal)",
        ]
    )


def _service_module(brief: dict[str, Any], system: dict[str, str]) -> str:
    return "\n".join(
        [
            "--!strict",
            "",
            f"-- Stub generated for {brief['game_title']}",
            f"local {system['service_name']} = {{}}",
            "",
            f"function {system['service_name']}.start(config)",
            f"    print(\"Starting {system['service_name']} for\", config.gameTitle)",
            f"    print(\"System intent: {system['description']}\")",
            "end",
            "",
            f"return {system['service_name']}",
        ]
    )


def _workspace_notes(brief: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {brief['game_title']} Workspace Notes",
            "",
            "Use this folder for placeholder map and spawn content.",
            "",
            "Suggested first build order:",
            "",
            "1. spawn and checkpoint path",
            "2. fail hazards",
            "3. finish trigger",
            "4. one monetization hook only after the core loop feels good",
        ]
    )


def _studio_sync_doc(brief: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {brief['game_title']} Studio Sync",
            "",
            "## Goal",
            "",
            "Start a local Rojo server and connect the generated project to Roblox Studio.",
            "",
            "## Steps",
            "",
            "1. Install Rojo if it is not already available on your machine.",
            "2. Run `scripts/run_rojo_serve.ps1` from PowerShell.",
            "3. Open Roblox Studio with the Rojo plugin enabled.",
            "4. Connect Studio to `localhost:34872`.",
            "5. Confirm the generated modules appear under ReplicatedStorage, ServerScriptService, StarterPlayerScripts, and Workspace.",
            "",
            "## First Manual Checks",
            "",
            "- `bootstrap.server.lua` loads without syntax errors",
            "- `bootstrap.client.lua` prints the generated session goal",
            "- each generated service module can be required cleanly",
            "- the map and spawn path still need manual assembly",
        ]
    )


def _run_rojo_ps1() -> str:
    return "\n".join(
        [
            "param(",
            "    [int]$Port = 34872",
            ")",
            "",
            '$ProjectPath = Join-Path $PSScriptRoot "..\\default.project.json"',
            "",
            "if (-not (Get-Command rojo -ErrorAction SilentlyContinue)) {",
            '    Write-Error "Rojo is not installed or not on PATH."',
            "    exit 1",
            "}",
            "",
            'Write-Host "Starting Rojo with project $ProjectPath on port $Port"',
            "rojo serve $ProjectPath --port $Port",
        ]
    )


def _run_rojo_cmd() -> str:
    return "\n".join(
        [
            "@echo off",
            "set PORT=%1",
            "if \"%PORT%\"==\"\" set PORT=34872",
            "where rojo >nul 2>nul",
            "if errorlevel 1 (",
            "  echo Rojo is not installed or not on PATH.",
            "  exit /b 1",
            ")",
            "set PROJECT=%~dp0..\\default.project.json",
            "echo Starting Rojo with project %PROJECT% on port %PORT%",
            "rojo serve %PROJECT% --port %PORT%",
        ]
    )


def _quality_ps1() -> str:
    return "\n".join(
        [
            '$ProjectPath = Join-Path $PSScriptRoot ".."',
            'python -m domain_chip_roblox_development.quality --project-dir $ProjectPath',
        ]
    )


def _quality_cmd() -> str:
    return "\n".join(
        [
            "@echo off",
            "set PROJECT=%~dp0..",
            "python -m domain_chip_roblox_development.quality --project-dir %PROJECT%",
        ]
    )


def _sync_preflight_ps1() -> str:
    return "\n".join(
        [
            '$ProjectPath = Join-Path $PSScriptRoot ".."',
            'python -m domain_chip_roblox_development.studio_sync --project-dir $ProjectPath',
        ]
    )


def _sync_preflight_cmd() -> str:
    return "\n".join(
        [
            "@echo off",
            "set PROJECT=%~dp0..",
            "python -m domain_chip_roblox_development.studio_sync --project-dir %PROJECT%",
        ]
    )


def _playable_check_ps1() -> str:
    return "\n".join(
        [
            '$ProjectPath = Join-Path $PSScriptRoot ".."',
            'python -m domain_chip_roblox_development.playable --project-dir $ProjectPath',
        ]
    )


def _playable_check_cmd() -> str:
    return "\n".join(
        [
            "@echo off",
            "set PROJECT=%~dp0..",
            "python -m domain_chip_roblox_development.playable --project-dir %PROJECT%",
        ]
    )


def generate_project(brief: dict[str, Any], output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    normalized = _normalize_brief(brief)
    destination = output_dir.resolve()
    if destination.exists():
        if not force and any(destination.iterdir()):
            raise FileExistsError(f"Output directory is not empty: {destination}")
        if force:
            shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    project_tree = _project_tree()
    project_tree["name"] = normalized["game_title"]

    _write(destination / "README.md", _readme(normalized))
    _write(destination / "game.config.json", json.dumps(normalized, indent=2, sort_keys=True))
    _write(destination / "default.project.json", json.dumps(project_tree, indent=2, sort_keys=True))
    _write(destination / "src" / "replicated" / "Modules" / "GameConfig.lua", _game_config_lua(normalized))
    _write(destination / "src" / "replicated" / "Modules" / "LoopDefinition.lua", _loop_definition_lua(normalized))
    _write(destination / "src" / "server" / "bootstrap.server.lua", _server_bootstrap(normalized))
    _write(destination / "src" / "client" / "bootstrap.client.lua", _client_bootstrap(normalized))
    _write(destination / "src" / "workspace" / "README.md", _workspace_notes(normalized))
    _write(destination / "docs" / "STUDIO_SYNC.md", _studio_sync_doc(normalized))
    _write(destination / "scripts" / "run_rojo_serve.ps1", _run_rojo_ps1())
    _write(destination / "scripts" / "run_rojo_serve.cmd", _run_rojo_cmd())
    _write(destination / "scripts" / "run_quality_gate.ps1", _quality_ps1())
    _write(destination / "scripts" / "run_quality_gate.cmd", _quality_cmd())
    _write(destination / "scripts" / "run_sync_preflight.ps1", _sync_preflight_ps1())
    _write(destination / "scripts" / "run_sync_preflight.cmd", _sync_preflight_cmd())
    _write(destination / "scripts" / "run_playable_check.ps1", _playable_check_ps1())
    _write(destination / "scripts" / "run_playable_check.cmd", _playable_check_cmd())
    for system in normalized["systems"]:
        _write(
            destination / "src" / "server" / "Services" / f"{system['service_name']}.lua",
            _service_module(normalized, system),
        )

    return {
        "game_title": normalized["game_title"],
        "game_slug": normalized["game_slug"],
        "output_dir": str(destination),
        "generated_files": sorted(str(path.relative_to(destination)).replace("\\", "/") for path in destination.rglob("*") if path.is_file()),
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Brief file must contain a JSON object.")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(prog="domain_chip_roblox_development.scaffold")
    parser.add_argument("--brief", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    result = generate_project(_load_json(Path(args.brief)), Path(args.output_dir), force=args.force)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
