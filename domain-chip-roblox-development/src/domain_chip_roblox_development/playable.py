from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def inspect_playable_loop(project_dir: Path) -> dict[str, Any]:
    root = project_dir.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    config_path = root / "game.config.json"
    if not config_path.exists():
        errors.append("Missing game.config.json")
        systems: list[dict[str, Any]] = []
        genre = ""
    else:
        config = _load_json(config_path)
        systems = config.get("systems", [])
        systems = systems if isinstance(systems, list) else []
        genre = str(config.get("genre", ""))

    system_names = {str(item.get("name", "")).strip().lower() for item in systems if isinstance(item, dict)}
    service_names = {str(item.get("service_name", "")).strip() for item in systems if isinstance(item, dict)}

    if genre == "obby":
        for required in ("checkpoint", "hazard", "timer"):
            if required not in system_names:
                errors.append(f"Obby scaffold is missing required gameplay system `{required}`.")

    bootstrap_server = root / "src" / "server" / "bootstrap.server.lua"
    bootstrap_client = root / "src" / "client" / "bootstrap.client.lua"
    if bootstrap_server.exists():
        server_text = bootstrap_server.read_text(encoding="utf-8")
        for service_name in service_names:
            if service_name and service_name not in server_text:
                errors.append(f"bootstrap.server.lua does not start `{service_name}`.")
    else:
        errors.append("Missing src/server/bootstrap.server.lua")

    if bootstrap_client.exists():
        client_text = bootstrap_client.read_text(encoding="utf-8")
        if "Session goal" not in client_text:
            warnings.append("bootstrap.client.lua does not expose the session goal yet.")
    else:
        errors.append("Missing src/client/bootstrap.client.lua")

    workspace_notes = root / "src" / "workspace" / "README.md"
    if workspace_notes.exists():
        notes = workspace_notes.read_text(encoding="utf-8")
        for phrase in ("spawn", "checkpoint", "finish"):
            if phrase not in notes.lower():
                warnings.append(f"Workspace notes do not mention `{phrase}`.")
    else:
        warnings.append("Missing workspace README for level assembly guidance.")

    status = "playable_stub_ready" if not errors else "blocked"
    return {
        "project_dir": str(root),
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "required_systems_present": sorted(system_names),
        "service_count": len(service_names),
        "acceptance_checks": [
            "checkpoint progression system is scaffolded",
            "hazard fail/reset system is scaffolded",
            "timer/progression feedback system is scaffolded",
            "server bootstrap starts generated gameplay services",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="domain_chip_roblox_development.playable")
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args()

    result = inspect_playable_loop(Path(args.project_dir))
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] != "blocked" else 1)


if __name__ == "__main__":
    main()
