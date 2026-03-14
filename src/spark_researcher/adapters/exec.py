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
from ..tracing import start_trace


ENV_KEYS = {
    "claude": "SPARK_RESEARCHER_ADAPTER_CLAUDE_COMMAND",
    "codex": "SPARK_RESEARCHER_ADAPTER_CODEX_COMMAND",
    "openclaw": "SPARK_RESEARCHER_ADAPTER_OPENCLAW_COMMAND",
    "generic": "SPARK_RESEARCHER_ADAPTER_GENERIC_COMMAND",
}


def _now_slug() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _powershell_executable() -> str:
    for candidate in ("pwsh", "powershell"):
        if shutil.which(candidate):
            return candidate
    return ""


def _default_command(model: str) -> list[str]:
    if model != "codex":
        return []
    wrapper_path = _repo_root() / "scripts" / "codex_frontier_wrapper.ps1"
    powershell = _powershell_executable()
    if not powershell or not wrapper_path.exists():
        return []
    return [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(wrapper_path),
        "{system_prompt_path}",
        "{user_prompt_path}",
        "{response_path}",
    ]


def _resolve_command(model: str, command_override: list[str] | None = None) -> list[str]:
    if command_override:
        parts: list[str] = []
        for item in command_override:
            parts.extend(shlex.split(str(item), posix=False))
        return parts
    raw = os.environ.get(ENV_KEYS[model], "").strip()
    return shlex.split(raw, posix=False) if raw else _default_command(model)


def execution_status() -> dict[str, Any]:
    rows = []
    for model, env_key in ENV_KEYS.items():
        raw = os.environ.get(env_key, "").strip()
        source = "env"
        parts = shlex.split(raw, posix=False) if raw else _default_command(model)
        if not raw and parts:
            source = "default"
        elif not parts:
            source = "unset"
        executable = parts[0] if parts else ""
        rows.append(
            {
                "model": model,
                "env_key": env_key,
                "configured": bool(parts),
                "source": source,
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
    trace = start_trace(
        runtime_root,
        kind="advisory_execute",
        name=model,
        parent_trace_id=str(advisory.get("trace_id") or "") or None,
        attributes={"model": model, "dry_run": dry_run},
    )
    command = _resolve_command(model, command_override)
    if not command:
        trace.finish(status="error", attributes={"error": f"No execution command configured for model `{model}`."})
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
        trace.finish(status="ok", attributes={"mode": "dry_run", "command": expanded})
        return {
            "model": model,
            "dry_run": True,
            "command": expanded,
            "request_path": str(request_path),
            "system_prompt_path": str(system_prompt_path),
            "user_prompt_path": str(user_prompt_path),
            "response_path": str(response_path),
            "trace_id": trace.trace_id,
            "trace_path": str(trace.path),
        }
    with trace.span("subprocess", attributes={"command": expanded}):
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
    trace.finish(status="ok" if result.returncode == 0 else "error", attributes={"returncode": result.returncode, "response_path": str(response_path)})
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
        "trace_id": trace.trace_id,
        "trace_path": str(trace.path),
    }
