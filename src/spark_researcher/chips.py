from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import ProjectConfig, load_config
from .paths import chips_root, resolve_runtime_root


@dataclass(frozen=True)
class ChipContext:
    repo_root: Path
    runtime_root: Path
    chip_root: Path
    manifest_path: Path
    manifest: dict[str, Any]


def _now_slug() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")


def _resolve_chip_root(config_path: Path, config: ProjectConfig) -> Path | None:
    raw = str(config.chip.path or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (config_path.parent / path).resolve()
    return path


def load_chip_context(config_path: Path, config: ProjectConfig | None = None) -> ChipContext | None:
    loaded = config or load_config(config_path)
    chip_root = _resolve_chip_root(config_path, loaded)
    if chip_root is None:
        return None
    manifest_path = chip_root / str(loaded.chip.manifest or "spark-chip.json")
    if not manifest_path.exists():
        raise RuntimeError(f"Chip manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(manifest, dict):
        raise RuntimeError(f"Chip manifest must be a JSON object: {manifest_path}")
    return ChipContext(
        repo_root=config_path.parent.resolve(),
        runtime_root=resolve_runtime_root(config_path),
        chip_root=chip_root,
        manifest_path=manifest_path,
        manifest=manifest,
    )


def chip_status(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    context = load_chip_context(config_path, config)
    if context is None:
        return {"configured": False, "notes": ["No chip is configured for this project."]}
    commands = context.manifest.get("commands", {})
    return {
        "configured": True,
        "chip_name": str(context.manifest.get("chip_name", context.chip_root.name)),
        "domain": str(context.manifest.get("domain", "unknown")),
        "version": str(context.manifest.get("version", "0.0.0")),
        "chip_root": str(context.chip_root),
        "manifest_path": str(context.manifest_path),
        "capabilities": [str(item) for item in context.manifest.get("capabilities", [])],
        "commands": sorted(str(name) for name in commands.keys()) if isinstance(commands, dict) else [],
    }


def chip_has_hook(config_path: Path, hook: str, config: ProjectConfig | None = None) -> bool:
    context = load_chip_context(config_path, config)
    if context is None:
        return False
    commands = context.manifest.get("commands", {})
    return isinstance(commands, dict) and hook in commands


def _command_parts(raw: Any) -> list[str]:
    if isinstance(raw, list) and all(isinstance(item, (str, int, float)) for item in raw):
        return [str(item) for item in raw]
    raise RuntimeError("Chip command entries must be arrays of command parts.")


def invoke_chip_hook(
    config_path: Path,
    hook: str,
    payload: dict[str, Any],
    *,
    config: ProjectConfig | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    context = load_chip_context(config_path, config)
    if context is None:
        raise RuntimeError("No chip configured for this project.")
    commands = context.manifest.get("commands", {})
    if not isinstance(commands, dict) or hook not in commands:
        raise RuntimeError(f"Chip hook `{hook}` is not defined in {context.manifest_path}.")
    command = _command_parts(commands[hook])
    hook_root = chips_root(context.runtime_root) / str(context.manifest.get("chip_name", context.chip_root.name)) / hook
    hook_root.mkdir(parents=True, exist_ok=True)
    stamp = _now_slug()
    input_path = hook_root / f"{stamp}.input.json"
    output_path = hook_root / f"{stamp}.output.json"
    log_path = hook_root / f"{stamp}.log"
    envelope = {
        "hook": hook,
        "repo_root": str(context.repo_root),
        "runtime_root": str(context.runtime_root),
        "chip_root": str(context.chip_root),
        "manifest_path": str(context.manifest_path),
        **payload,
    }
    input_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    invoked = command + ["--input", str(input_path), "--output", str(output_path)]
    if dry_run:
        preview = {
            "hook": hook,
            "command": invoked,
            "cwd": str(context.chip_root),
            "input_path": str(input_path),
            "output_path": str(output_path),
        }
        log_path.write_text(json.dumps(preview, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return preview
    result = subprocess.run(
        invoked,
        cwd=str(context.chip_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log_path.write_text(
        json.dumps(
            {
                "command": invoked,
                "cwd": str(context.chip_root),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "input_path": str(input_path),
                "output_path": str(output_path),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"Chip hook `{hook}` failed with exit code {result.returncode}: {result.stderr.strip()}")
    if not output_path.exists():
        raise RuntimeError(f"Chip hook `{hook}` did not produce an output file: {output_path}")
    response = json.loads(output_path.read_text(encoding="utf-8-sig"))
    if not isinstance(response, dict):
        raise RuntimeError(f"Chip hook `{hook}` must return a JSON object.")
    response.setdefault("chip_name", str(context.manifest.get("chip_name", context.chip_root.name)))
    response.setdefault("domain", str(context.manifest.get("domain", "unknown")))
    response.setdefault("hook", hook)
    response.setdefault("log_path", str(log_path))
    return response
