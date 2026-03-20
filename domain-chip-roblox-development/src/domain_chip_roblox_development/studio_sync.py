from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _run_rojo_sourcemap(project_dir: Path, rojo_path: str) -> dict[str, Any]:
    command = [rojo_path, "sourcemap", "default.project.json", "--output", "-"]
    result = subprocess.run(
        command,
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "passed": result.returncode == 0,
    }


def inspect_project(project_dir: Path) -> dict[str, Any]:
    root = project_dir.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    project_path = root / "default.project.json"
    if not project_path.exists():
        errors.append("Missing default.project.json")
        tree: dict[str, Any] = {}
        project_name = root.name
    else:
        project_payload = _load_json(project_path)
        tree = project_payload.get("tree", {})
        tree = tree if isinstance(tree, dict) else {}
        project_name = str(project_payload.get("name", root.name))

    required_paths = (
        root / "src" / "server" / "bootstrap.server.lua",
        root / "src" / "client" / "bootstrap.client.lua",
        root / "src" / "replicated" / "Modules" / "GameConfig.lua",
    )
    for path in required_paths:
        if not path.exists():
            errors.append(f"Missing sync-critical file: {path.relative_to(root)}")

    rojo_path = shutil.which("rojo")
    plugin_needed = True
    if rojo_path is None:
        warnings.append("Rojo is not installed or not on PATH.")
        rojo_check = None
    else:
        rojo_check = _run_rojo_sourcemap(root, rojo_path)
        if not rojo_check["passed"]:
            warnings.append("Rojo is installed but `rojo sourcemap` failed for this project.")

    mappings = {
        "ReplicatedStorage": "src/replicated",
        "ServerScriptService": "src/server",
        "StarterPlayer": "src/client",
        "Workspace": "src/workspace",
    }
    present_mappings: list[dict[str, str]] = []
    for service_name, expected_path in mappings.items():
        if service_name not in tree:
            warnings.append(f"default.project.json is missing top-level `{service_name}`.")
            continue
        present_mappings.append({"service": service_name, "expected_path": expected_path})

    status = "ready_for_manual_sync" if not errors else "blocked"
    return {
        "project_dir": str(root),
        "project_name": project_name,
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "rojo_available": rojo_path is not None,
        "rojo_path": rojo_path,
        "rojo_check": rojo_check,
        "studio_plugin_required": plugin_needed,
        "serve_command": "rojo serve default.project.json --port 34872",
        "connect_target": "localhost:34872",
        "mappings": present_mappings,
        "operator_actions": [
            "Run scripts/run_rojo_serve.ps1 or scripts/run_rojo_serve.cmd.",
            "Open Roblox Studio with the Rojo plugin enabled.",
            "Connect the place to localhost:34872.",
            "Verify the generated tree appears in Studio before editing gameplay.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="domain_chip_roblox_development.studio_sync")
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args()

    result = inspect_project(Path(args.project_dir))
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] != "blocked" else 1)


if __name__ == "__main__":
    main()
