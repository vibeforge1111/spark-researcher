from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "default.project.json",
    "game.config.json",
    "src/server/bootstrap.server.lua",
    "src/client/bootstrap.client.lua",
    "src/replicated/Modules/GameConfig.lua",
    "src/replicated/Modules/LoopDefinition.lua",
)

OPTIONAL_TOOLS = ("rojo", "stylua", "selene", "luau-lsp")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _discover_tools() -> dict[str, str | None]:
    return {tool: shutil.which(tool) for tool in OPTIONAL_TOOLS}


def _balanced_lua(text: str) -> bool:
    pairs = {")": "(", "}": "{", "]": "["}
    opening = set(pairs.values())
    closing = set(pairs)
    stack: list[str] = []
    string_char = ""
    escape = False
    for char in text:
        if string_char:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == string_char:
                string_char = ""
            continue
        if char in {"'", '"'}:
            string_char = char
            continue
        if char in opening:
            stack.append(char)
            continue
        if char in closing:
            if not stack or stack.pop() != pairs[char]:
                return False
    return not string_char and not stack


def check_project(project_dir: Path) -> dict[str, Any]:
    root = project_dir.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED_FILES:
        if not (root / relative).exists():
            errors.append(f"Missing required file: {relative}")

    project_json = root / "default.project.json"
    config_json = root / "game.config.json"
    if project_json.exists():
        try:
            project_payload = _load_json(project_json)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
        else:
            tree = project_payload.get("tree", {})
            if not isinstance(tree, dict):
                errors.append("default.project.json `tree` must be an object.")
            else:
                for path in ("ReplicatedStorage", "ServerScriptService", "StarterPlayer", "Workspace"):
                    if path not in tree:
                        errors.append(f"default.project.json is missing `{path}` mapping.")

    systems: list[dict[str, Any]] = []
    if config_json.exists():
        try:
            config_payload = _load_json(config_json)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
        else:
            for key in ("game_title", "genre", "core_loop", "target_audience", "session_goal"):
                if not str(config_payload.get(key, "")).strip():
                    errors.append(f"game.config.json is missing required field `{key}`.")
            raw_systems = config_payload.get("systems", [])
            if not isinstance(raw_systems, list) or not raw_systems:
                errors.append("game.config.json must include at least one system.")
            else:
                systems = [item for item in raw_systems if isinstance(item, dict)]

    lua_files = sorted(root.rglob("*.lua"))
    if not lua_files:
        errors.append("No Lua files were generated.")

    for lua_path in lua_files:
        text = lua_path.read_text(encoding="utf-8")
        rel = str(lua_path.relative_to(root)).replace("\\", "/")
        if not text.startswith("--!strict"):
            errors.append(f"{rel} must start with `--!strict`.")
        if not _balanced_lua(text):
            errors.append(f"{rel} has unbalanced delimiters or unterminated strings.")
        if "return " not in text and rel.endswith(".lua") and "bootstrap" not in rel:
            warnings.append(f"{rel} does not return a module value.")

    for system in systems:
        service_name = str(system.get("service_name", "")).strip()
        if not service_name:
            errors.append("Each system must include `service_name` in game.config.json.")
            continue
        service_path = root / "src" / "server" / "Services" / f"{service_name}.lua"
        if not service_path.exists():
            errors.append(f"Missing service module for `{service_name}`.")
            continue
        service_text = service_path.read_text(encoding="utf-8")
        if f"function {service_name}.start(config)" not in service_text:
            errors.append(f"{service_name}.lua is missing `start(config)`.")
        if f"return {service_name}" not in service_text:
            errors.append(f"{service_name}.lua is missing `return {service_name}`.")

    bootstrap_path = root / "src" / "server" / "bootstrap.server.lua"
    if bootstrap_path.exists():
        bootstrap_text = bootstrap_path.read_text(encoding="utf-8")
        for system in systems:
            service_name = str(system.get("service_name", "")).strip()
            if not service_name:
                continue
            if service_name not in bootstrap_text:
                errors.append(f"bootstrap.server.lua does not reference `{service_name}`.")

    tools = _discover_tools()
    if tools["stylua"] is None:
        warnings.append("Optional tool `stylua` is not available on PATH.")
    if tools["selene"] is None:
        warnings.append("Optional tool `selene` is not available on PATH.")

    passed = not errors
    return {
        "project_dir": str(root),
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "tooling": tools,
        "checked_lua_file_count": len(lua_files),
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="domain_chip_roblox_development.quality")
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args()

    result = check_project(Path(args.project_dir))
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
