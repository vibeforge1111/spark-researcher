from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import ProjectConfig, load_config
from .paths import chips_root, resolve_runtime_root

CHIP_SCHEMA_VERSION = "spark-chip.v1"
CHIP_IO_PROTOCOL = "spark-hook-io.v1"
HOOK_NAMES = ("evaluate", "suggest", "packets", "watchtower")
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class ChipContext:
    repo_root: Path
    runtime_root: Path
    chip_root: Path
    manifest_path: Path
    manifest: dict[str, Any]


def schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "spark-chip.schema.json"


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


def validate_manifest(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if str(manifest.get("schema_version", "")) != CHIP_SCHEMA_VERSION:
        errors.append(f"`schema_version` must be `{CHIP_SCHEMA_VERSION}`.")
    if str(manifest.get("io_protocol", "")) != CHIP_IO_PROTOCOL:
        errors.append(f"`io_protocol` must be `{CHIP_IO_PROTOCOL}`.")
    chip_name = str(manifest.get("chip_name", ""))
    if not _NAME_RE.fullmatch(chip_name):
        errors.append("`chip_name` must be a lowercase slug using letters, digits, `.`, `_`, or `-`.")
    domain = str(manifest.get("domain", ""))
    if not _NAME_RE.fullmatch(domain):
        errors.append("`domain` must be a lowercase slug using letters, digits, `.`, `_`, or `-`.")
    version = str(manifest.get("version", ""))
    if not _VERSION_RE.fullmatch(version):
        errors.append("`version` must use `MAJOR.MINOR.PATCH` semver.")
    description = str(manifest.get("description", "")).strip()
    if not description:
        errors.append("`description` is required.")
    capabilities = manifest.get("capabilities", [])
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("`capabilities` must be a non-empty array.")
        capabilities = []
    capability_names = [str(item) for item in capabilities]
    invalid_caps = [item for item in capability_names if item not in HOOK_NAMES]
    if invalid_caps:
        errors.append(f"`capabilities` contains unknown hooks: {', '.join(sorted(set(invalid_caps)))}.")
    commands = manifest.get("commands", {})
    if not isinstance(commands, dict) or not commands:
        errors.append("`commands` must be a non-empty object.")
        commands = {}
    command_names = [str(name) for name in commands.keys()]
    invalid_commands = [item for item in command_names if item not in HOOK_NAMES]
    if invalid_commands:
        errors.append(f"`commands` contains unknown hooks: {', '.join(sorted(set(invalid_commands)))}.")
    missing_commands = [item for item in capability_names if item not in commands]
    if missing_commands:
        errors.append(f"`commands` is missing capability entries: {', '.join(sorted(missing_commands))}.")
    extra_commands = [item for item in command_names if item not in capability_names]
    if extra_commands:
        warnings.append(f"`commands` declares hooks not listed in capabilities: {', '.join(sorted(extra_commands))}.")
    for hook_name, command in commands.items():
        try:
            _command_parts(command)
        except RuntimeError as exc:
            errors.append(f"`commands.{hook_name}` {exc}")
    return {
        "valid": not errors,
        "manifest_path": str(manifest_path),
        "schema_version": CHIP_SCHEMA_VERSION,
        "io_protocol": CHIP_IO_PROTOCOL,
        "errors": errors,
        "warnings": warnings,
    }


def chip_validation(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    context = load_chip_context(config_path, config)
    if context is None:
        return {
            "configured": False,
            "valid": False,
            "errors": ["No chip is configured for this project."],
            "schema_path": str(schema_path()),
        }
    result = validate_manifest(context.manifest, context.manifest_path)
    result.update(
        {
            "configured": True,
            "chip_name": str(context.manifest.get("chip_name", context.chip_root.name)),
            "domain": str(context.manifest.get("domain", "unknown")),
            "version": str(context.manifest.get("version", "0.0.0")),
            "chip_root": str(context.chip_root),
            "schema_path": str(schema_path()),
        }
    )
    return result


def chip_status(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    context = load_chip_context(config_path, config)
    if context is None:
        return {"configured": False, "notes": ["No chip is configured for this project."]}
    commands = context.manifest.get("commands", {})
    validation = validate_manifest(context.manifest, context.manifest_path)
    return {
        "configured": True,
        "chip_name": str(context.manifest.get("chip_name", context.chip_root.name)),
        "domain": str(context.manifest.get("domain", "unknown")),
        "version": str(context.manifest.get("version", "0.0.0")),
        "schema_version": str(context.manifest.get("schema_version", "")),
        "io_protocol": str(context.manifest.get("io_protocol", "")),
        "chip_root": str(context.chip_root),
        "manifest_path": str(context.manifest_path),
        "schema_path": str(schema_path()),
        "capabilities": [str(item) for item in context.manifest.get("capabilities", [])],
        "commands": sorted(str(name) for name in commands.keys()) if isinstance(commands, dict) else [],
        "valid": validation["valid"],
        "validation_errors": validation["errors"],
        "validation_warnings": validation["warnings"],
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
