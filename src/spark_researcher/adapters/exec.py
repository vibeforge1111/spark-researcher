from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..paths import advisory_root


ENV_KEYS = {
    "claude": "SPARK_RESEARCHER_ADAPTER_CLAUDE_COMMAND",
    "codex": "SPARK_RESEARCHER_ADAPTER_CODEX_COMMAND",
    "openclaw": "SPARK_RESEARCHER_ADAPTER_OPENCLAW_COMMAND",
    "generic": "SPARK_RESEARCHER_ADAPTER_GENERIC_COMMAND",
}


def _now_slug() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")


def _resolve_command(model: str, command_override: list[str] | None = None) -> list[str]:
    if command_override:
        parts: list[str] = []
        for item in command_override:
            parts.extend(shlex.split(str(item), posix=False))
        return parts
    raw = os.environ.get(ENV_KEYS[model], "").strip()
    return shlex.split(raw, posix=False) if raw else []


def execution_status() -> dict[str, Any]:
    rows = []
    for model, env_key in ENV_KEYS.items():
        raw = os.environ.get(env_key, "").strip()
        parts = shlex.split(raw, posix=False) if raw else []
        executable = parts[0] if parts else ""
        rows.append(
            {
                "model": model,
                "env_key": env_key,
                "configured": bool(parts),
                "command": parts,
                "executable_present": shutil.which(executable) is not None if executable else False,
                "template_placeholders": [
                    "{system_prompt_path}",
                    "{user_prompt_path}",
                    "{request_path}",
                    "{response_path}",
                ],
            }
        )
    return {"providers": rows}


def execute_advisory(
    runtime_root: Path,
    *,
    advisory: dict[str, Any],
    model: str,
    command_override: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    command = _resolve_command(model, command_override)
    if not command:
        raise RuntimeError(f"No execution command configured for model `{model}`.")
    root = advisory_root(runtime_root) / "requests"
    root.mkdir(parents=True, exist_ok=True)
    stamp = _now_slug()
    request_path = root / f"{stamp}.request.json"
    system_prompt_path = root / f"{stamp}.system.txt"
    user_prompt_path = root / f"{stamp}.user.txt"
    response_path = root / f"{stamp}.response.json"
    stdout_path = root / f"{stamp}.stdout.log"
    stderr_path = root / f"{stamp}.stderr.log"
    system_prompt = str(advisory.get("adapter_request", {}).get("system_prompt", ""))
    user_prompt = str(advisory.get("adapter_request", {}).get("user_prompt", ""))
    request_path.write_text(json.dumps(advisory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    system_prompt_path.write_text(system_prompt, encoding="utf-8")
    user_prompt_path.write_text(user_prompt, encoding="utf-8")
    expanded = [
        part.replace("{system_prompt_path}", str(system_prompt_path))
        .replace("{user_prompt_path}", str(user_prompt_path))
        .replace("{request_path}", str(request_path))
        .replace("{response_path}", str(response_path))
        for part in command
    ]
    if dry_run:
        return {
            "model": model,
            "dry_run": True,
            "command": expanded,
            "request_path": str(request_path),
            "system_prompt_path": str(system_prompt_path),
            "user_prompt_path": str(user_prompt_path),
            "response_path": str(response_path),
        }
    result = subprocess.run(expanded, capture_output=True, text=True, encoding="utf-8", errors="replace")
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    response_payload: dict[str, Any]
    if response_path.exists():
        try:
            response_payload = json.loads(response_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            response_payload = {"raw_response": response_path.read_text(encoding="utf-8", errors="replace")}
    else:
        response_payload = {"raw_response": result.stdout.strip()}
    return {
        "model": model,
        "returncode": result.returncode,
        "command": expanded,
        "request_path": str(request_path),
        "system_prompt_path": str(system_prompt_path),
        "user_prompt_path": str(user_prompt_path),
        "response_path": str(response_path),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "response": response_payload,
    }
