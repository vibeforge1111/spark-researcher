from __future__ import annotations

import json
import os
import re
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

GENERIC_ADAPTER_ENABLE_ENV = "SPARK_RESEARCHER_ENABLE_GENERIC_ADAPTER"
EXTRA_ALLOWED_EXECUTABLES_ENV = "SPARK_RESEARCHER_ADAPTER_ALLOWED_EXECUTABLES"

ALLOWED_ADAPTER_EXECUTABLES = {
    "claude": {"claude", "claude.cmd", "claude.exe"},
    "codex": {"codex", "codex.cmd", "codex.exe"},
    "openclaw": {"openclaw", "openclaw.cmd", "openclaw.exe"},
    "generic": set(),
}

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


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


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _executable_name(executable: str) -> str:
    normalized = executable.strip().strip("\"'")
    return Path(normalized).name.lower()


def _extra_allowed_executables() -> set[str]:
    raw = os.environ.get(EXTRA_ALLOWED_EXECUTABLES_ENV, "")
    return {_executable_name(item) for item in raw.split(",") if item.strip()}


def _validate_command(model: str, command: list[str]) -> list[str]:
    if model not in ENV_KEYS:
        raise RuntimeError(f"Unsupported execution model `{model}`. Supported: {', '.join(sorted(ENV_KEYS))}.")
    if not command:
        return command
    if model == "generic" and not _truthy_env(GENERIC_ADAPTER_ENABLE_ENV):
        raise RuntimeError(
            "The generic execution adapter is disabled by default. Set "
            f"{GENERIC_ADAPTER_ENABLE_ENV}=1 and {EXTRA_ALLOWED_EXECUTABLES_ENV} to an explicit executable allowlist."
        )
    executable = _executable_name(command[0])
    allowed = set(ALLOWED_ADAPTER_EXECUTABLES.get(model, set())) | _extra_allowed_executables()
    if executable not in allowed:
        allowed_text = ", ".join(sorted(allowed)) or "none"
        raise RuntimeError(
            f"Execution command for model `{model}` uses executable `{executable}`, which is not allowed. "
            f"Allowed executable names: {allowed_text}."
        )
    return command


def _resolve_command(model: str, command_override: list[str] | None = None) -> list[str]:
    if model not in ENV_KEYS:
        raise RuntimeError(f"Unsupported execution model `{model}`. Supported: {', '.join(sorted(ENV_KEYS))}.")
    if command_override:
        parts: list[str] = []
        for item in command_override:
            parts.extend(shlex.split(str(item), posix=False))
        return _validate_command(model, parts)
    raw = os.environ.get(ENV_KEYS[model], "").strip()
    if raw:
        return _validate_command(model, shlex.split(raw, posix=False))
    return _default_command(model)


def _expand_command_template(command: list[str], replacements: dict[str, str]) -> list[str]:
    allowed = set(replacements)
    expanded: list[str] = []
    for part in command:
        unknown = sorted({match.group(1) for match in _PLACEHOLDER_RE.finditer(part)} - allowed)
        if unknown:
            names = ", ".join(f"{{{name}}}" for name in unknown)
            raise RuntimeError(f"Execution command uses unsupported template placeholder(s): {names}.")
        next_part = str(part)
        for name, value in replacements.items():
            next_part = next_part.replace(f"{{{name}}}", value)
        expanded.append(next_part)
    return expanded


def execution_status() -> dict[str, Any]:
    rows = []
    for model, env_key in ENV_KEYS.items():
        raw = os.environ.get(env_key, "").strip()
        source = "env"
        validation_error = ""
        if raw:
            parts = shlex.split(raw, posix=False)
            try:
                _validate_command(model, parts)
            except RuntimeError as error:
                validation_error = str(error)
        else:
            parts = _default_command(model)
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
                "allowed": not validation_error,
                "validation_error": validation_error,
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
    expanded = _expand_command_template(
        command,
        {
            "system_prompt_path": str(system_prompt_path),
            "user_prompt_path": str(user_prompt_path),
            "request_path": str(request_path),
            "response_path": str(response_path),
        },
    )
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
