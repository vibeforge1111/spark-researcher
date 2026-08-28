from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from typing import Any


DEFAULT_COMMAND = "npx ruvector"
MAX_QUERY_LENGTH = 500


def _executable_name(value: str) -> str:
    return value.replace("\\", "/").rsplit("/", 1)[-1].lower()


def _resolve_command() -> list[str]:
    command = os.environ.get("SPARK_RUVECTOR_COMMAND", DEFAULT_COMMAND).strip() or DEFAULT_COMMAND
    resolved = shlex.split(command)
    if not resolved:
        raise RuntimeError("RuVector command is empty.")
    executable = _executable_name(resolved[0])
    direct_launcher = len(resolved) == 1 and executable in {"ruvector", "ruvector.cmd"}
    npx_launcher = (
        len(resolved) == 2
        and executable in {"npx", "npx.cmd"}
        and resolved[1].lower() == "ruvector"
    )
    if not direct_launcher and not npx_launcher:
        raise RuntimeError("RuVector launcher configuration is invalid.")
    return resolved


def _normalize_query(query: str) -> str:
    normalized = " ".join(query.split())
    if not normalized:
        raise RuntimeError("Search query must not be empty.")
    if len(normalized) > MAX_QUERY_LENGTH:
        raise RuntimeError(f"Search query is too long. Keep it under {MAX_QUERY_LENGTH} characters.")
    return normalized


def _has_pi_identity() -> bool:
    return bool(os.environ.get("PI", "").strip())


def ruvector_status() -> dict[str, Any]:
    command = _resolve_command()
    executable = shutil.which(command[0]) if command and len(command) > 0 else None
    available = executable is not None
    has_pi = _has_pi_identity()
    status = "available" if available and has_pi else "missing_pi" if available else "missing_cli"
    return {
        "backend": "ruvector",
        "status": status,
        "command": command,
        "executable": executable,
        "available": available,
        "has_pi_identity": has_pi,
        "api_key_required": False,
        "notes": [
            "RuVector is Spark's recommended retrieval backend once the corpus grows.",
            "Spark delegates external/shared-brain retrieval to the RuVector CLI.",
            "Spark local memory remains the source of truth.",
        ],
    }


def run_search(query: str, *, timeout_seconds: int = 60) -> dict[str, Any]:
    normalized_query = _normalize_query(query)
    command = [*_resolve_command(), "brain", "--json", "search", "--", normalized_query]
    executable = shutil.which(command[0])
    if executable is None:
        raise RuntimeError(
            "RuVector CLI is not available. Install it first, for example with `npm install ruvector`."
        )
    if not _has_pi_identity():
        raise RuntimeError("RuVector search requires a Pi identity. Run `npx ruvector identity generate`, set `PI`, then retry.")
    command[0] = executable
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        if "missing authorization header" in detail.lower():
            raise RuntimeError("RuVector search requires RuVector CLI auth/setup. Run the RuVector CLI setup first, then retry.")
        raise RuntimeError(f"RuVector search failed: {detail}")
    stdout = completed.stdout.strip()
    try:
        parsed_results: Any = json.loads(stdout)
    except json.JSONDecodeError:
        parsed_results = stdout
    return {
        "backend": "ruvector",
        "result_scope": "external_shared_brain",
        "command": command,
        "query": normalized_query,
        "result_format": "json" if not isinstance(parsed_results, str) else "text",
        "results": parsed_results,
        "notes": [
            "These results come from RuVector shared-brain search, not Spark local Markdown memory.",
        ],
    }
