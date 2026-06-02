from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import ProjectConfig, load_config, resolve_project_root
from .paths import chips_root, resolve_runtime_root

CHIP_SCHEMA_VERSION = "spark-chip.v1"
CHIP_IO_PROTOCOL = "spark-hook-io.v1"
HOOK_NAMES = ("evaluate", "suggest", "packets", "watchtower")
FRONTIER_MODELS = ("claude", "codex", "openclaw", "generic")
FRONTIER_KEYS = ("allowed_mutations", "open_mutation_fields", "field_patterns", "prompt_hints", "required_fields", "model", "web_search", "enabled")
LOCAL_STATE_DIR_NAMES = (".paperclip-data", ".next", ".nuxt", ".svelte-kit", ".turbo", ".cache")
LOCAL_PATH_SUFFIXES = (".py", ".sh", ".ps1", ".cmd", ".bat", ".exe")
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
    misplaced_frontier_keys = [key for key in FRONTIER_KEYS if key in manifest]
    if misplaced_frontier_keys:
        errors.append(
            "`frontier` configuration keys must live under the `frontier` object, not at top level: "
            + ", ".join(sorted(misplaced_frontier_keys))
            + "."
        )
    frontier = manifest.get("frontier")
    if frontier is not None:
        if not isinstance(frontier, dict):
            errors.append("`frontier` must be an object when present.")
        else:
            if not isinstance(frontier.get("enabled", True), bool):
                errors.append("`frontier.enabled` must be a boolean.")
            model = str(frontier.get("model", "generic"))
            if model not in FRONTIER_MODELS:
                errors.append(f"`frontier.model` must be one of: {', '.join(FRONTIER_MODELS)}.")
            if not isinstance(frontier.get("web_search", False), bool):
                errors.append("`frontier.web_search` must be a boolean.")
            allowed = frontier.get("allowed_mutations", {})
            if not isinstance(allowed, dict) or not allowed:
                errors.append("`frontier.allowed_mutations` must be a non-empty object.")
                allowed = {}
            for field_name, values in allowed.items():
                if not _NAME_RE.fullmatch(str(field_name)):
                    errors.append(f"`frontier.allowed_mutations.{field_name}` must use a lowercase field slug.")
                if not isinstance(values, list) or not values or not all(isinstance(item, str) and str(item).strip() for item in values):
                    errors.append(f"`frontier.allowed_mutations.{field_name}` must be a non-empty array of strings.")
            open_fields = frontier.get("open_mutation_fields", [])
            if not isinstance(open_fields, list) or not all(isinstance(item, str) for item in open_fields):
                errors.append("`frontier.open_mutation_fields` must be an array of strings when present.")
            elif any(str(item) not in allowed for item in open_fields):
                errors.append("`frontier.open_mutation_fields` must refer only to keys in `frontier.allowed_mutations`.")
            field_patterns = frontier.get("field_patterns", {})
            if not isinstance(field_patterns, dict):
                errors.append("`frontier.field_patterns` must be an object when present.")
                field_patterns = {}
            for field_name, pattern in field_patterns.items():
                if str(field_name) not in allowed:
                    errors.append("`frontier.field_patterns` must refer only to keys in `frontier.allowed_mutations`.")
                    continue
                try:
                    re.compile(str(pattern))
                except re.error as exc:
                    errors.append(f"`frontier.field_patterns.{field_name}` is not a valid regex: {exc}.")
            prompt_hints = frontier.get("prompt_hints", [])
            if not isinstance(prompt_hints, list) or not all(isinstance(item, str) and str(item).strip() for item in prompt_hints):
                errors.append("`frontier.prompt_hints` must be an array of non-empty strings when present.")
            required_fields = frontier.get("required_fields", [])
            if not isinstance(required_fields, list) or not all(isinstance(item, str) for item in required_fields):
                errors.append("`frontier.required_fields` must be an array of strings when present.")
            elif any(str(item) not in allowed for item in required_fields):
                errors.append("`frontier.required_fields` must refer only to keys in `frontier.allowed_mutations`.")
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
            "schema_version": CHIP_SCHEMA_VERSION,
            "io_protocol": CHIP_IO_PROTOCOL,
        }
    result = validate_manifest(context.manifest, context.manifest_path)
    command_checks = _command_preflight(context.manifest, context.chip_root)
    result["errors"].extend(command_checks["errors"])
    result["warnings"].extend(command_checks["warnings"])
    workspace_warnings = _workspace_exclusion_warnings(resolve_project_root(config_path, config), config.workspace_excludes)
    result["warnings"].extend(workspace_warnings)
    result["valid"] = not result["errors"]
    result.update(
        {
            "configured": True,
            "chip_name": str(context.manifest.get("chip_name", context.chip_root.name)),
            "domain": str(context.manifest.get("domain", "unknown")),
            "version": str(context.manifest.get("version", "0.0.0")),
            "chip_root": str(context.chip_root),
            "schema_path": str(schema_path()),
            "command_checks": command_checks,
            "workspace_excludes": list(config.workspace_excludes),
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


def _looks_like_local_command_path(part: str) -> bool:
    if not part or part.startswith("-"):
        return False
    if "/" in part or "\\" in part:
        return True
    return Path(part).suffix.lower() in LOCAL_PATH_SUFFIXES


def _command_preflight(manifest: dict[str, Any], chip_root: Path) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    commands = manifest.get("commands", {})
    if not isinstance(commands, dict):
        return {"errors": errors, "warnings": warnings}
    for hook_name, raw_command in commands.items():
        try:
            command = _command_parts(raw_command)
        except RuntimeError:
            continue
        for index, part in enumerate(command):
            if not _looks_like_local_command_path(part):
                continue
            candidate = Path(part)
            if not candidate.is_absolute():
                candidate = (chip_root / candidate).resolve()
            if candidate.exists():
                continue
            errors.append(
                f"`commands.{hook_name}[{index}]` points to a missing local path: {part} "
                f"(resolved to {candidate})."
            )
    return {"errors": errors, "warnings": warnings}


def _normalize_relative_paths(paths: list[str]) -> set[str]:
    normalized: set[str] = set()
    for item in paths:
        value = str(item).strip().replace("\\", "/").strip("/")
        if not value or value == ".":
            continue
        normalized.add(value.casefold())
    return normalized


def _workspace_exclusion_warnings(project_root: Path, workspace_excludes: list[str]) -> list[str]:
    warnings: list[str] = []
    normalized_excludes = _normalize_relative_paths(workspace_excludes)
    for dir_name in LOCAL_STATE_DIR_NAMES:
        for path in project_root.rglob(dir_name):
            if not path.is_dir():
                continue
            rel_path = path.relative_to(project_root).as_posix()
            folded = rel_path.casefold()
            if any(folded == excluded or folded.startswith(f"{excluded}/") for excluded in normalized_excludes):
                continue
            warnings.append(
                f"Local state directory `{rel_path}` is not excluded from run workspace copies. "
                "Add it to `workspace_excludes` if it should stay out of Spark workspaces."
            )
    return sorted(set(warnings))


def _validate_hook_response(hook: str, response: dict[str, Any]) -> None:
    if hook == "evaluate":
        if "returncode" in response and not isinstance(response.get("returncode"), int):
            raise RuntimeError("Chip hook `evaluate` must return an integer `returncode` when present.")
        if "stdout" in response and not isinstance(response.get("stdout"), str):
            raise RuntimeError("Chip hook `evaluate` must return string `stdout` when present.")
        if "stderr" in response and not isinstance(response.get("stderr"), str):
            raise RuntimeError("Chip hook `evaluate` must return string `stderr` when present.")
        if "metrics" in response and not isinstance(response.get("metrics"), dict):
            raise RuntimeError("Chip hook `evaluate` must return object `metrics` when present.")
        if "result" in response and not isinstance(response.get("result"), dict):
            raise RuntimeError("Chip hook `evaluate` must return object `result` when present.")
        return
    if hook == "suggest":
        suggestions = response.get("suggestions", [])
        if not isinstance(suggestions, list):
            raise RuntimeError("Chip hook `suggest` must return array `suggestions` when present.")
        for index, item in enumerate(suggestions):
            if not isinstance(item, dict):
                raise RuntimeError(f"Chip hook `suggest` suggestions[{index}] must be an object.")
            candidate_id = str(item.get("candidate_id", "")).strip()
            if not candidate_id:
                raise RuntimeError(f"Chip hook `suggest` suggestions[{index}].candidate_id is required.")
            mutations = item.get("mutations", {})
            if not isinstance(mutations, dict):
                raise RuntimeError(f"Chip hook `suggest` suggestions[{index}].mutations must be an object.")
            if "metadata" in item and not isinstance(item.get("metadata"), dict):
                raise RuntimeError(f"Chip hook `suggest` suggestions[{index}].metadata must be an object when present.")
        return
    if hook == "packets":
        documents = response.get("documents", [])
        if not isinstance(documents, list):
            raise RuntimeError("Chip hook `packets` must return array `documents`.")
        for index, item in enumerate(documents):
            if not isinstance(item, dict):
                raise RuntimeError(f"Chip hook `packets` documents[{index}] must be an object.")
            for key in ("kind", "title", "content"):
                if not isinstance(item.get(key), str) or not str(item.get(key)).strip():
                    raise RuntimeError(f"Chip hook `packets` documents[{index}].{key} must be a non-empty string.")
            for key in ("slug", "memory_tier"):
                if key in item and not isinstance(item.get(key), str):
                    raise RuntimeError(f"Chip hook `packets` documents[{index}].{key} must be a string when present.")
        return
    if hook == "watchtower":
        pages = response.get("pages", [])
        if not isinstance(pages, list):
            raise RuntimeError("Chip hook `watchtower` must return array `pages`.")
        for index, item in enumerate(pages):
            if not isinstance(item, dict):
                raise RuntimeError(f"Chip hook `watchtower` pages[{index}] must be an object.")
            for key in ("path", "content"):
                if not isinstance(item.get(key), str) or not str(item.get(key)).strip():
                    raise RuntimeError(f"Chip hook `watchtower` pages[{index}].{key} must be a non-empty string.")
        return


def _build_hook_env(context: ChipContext) -> dict[str, str]:
    env = os.environ.copy()
    pythonpath_parts: list[str] = []
    spark_src = Path(__file__).resolve().parents[1]
    chip_src = context.chip_root / "src"
    for path in (spark_src, chip_src, context.chip_root):
        if path.exists():
            pythonpath_parts.append(str(path))
    existing = env.get("PYTHONPATH", "").strip()
    if existing:
        pythonpath_parts.append(existing)
    if pythonpath_parts:
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    return env


def _public_hook_failure_detail(hook: str, returncode: int) -> str:
    return (
        f"Chip hook `{hook}` failed with exit code {returncode}. "
        "Details were written to the local chip hook log."
    )


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
        raise RuntimeError("No chip configured for this project. Set `chip.path` (and optionally `chip.manifest`) in spark-researcher.json to point at a chip directory containing a manifest.")
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
    try:
        result = subprocess.run(
            invoked,
            cwd=str(context.chip_root),
            env=_build_hook_env(context),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Chip hook `{hook}` timed out after {exc.timeout}s") from None
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
        raise RuntimeError(_public_hook_failure_detail(hook, result.returncode))
    if not output_path.exists():
        raise RuntimeError(f"Chip hook `{hook}` did not produce an output file: {output_path}")
    response = json.loads(output_path.read_text(encoding="utf-8-sig"))
    if not isinstance(response, dict):
        raise RuntimeError(f"Chip hook `{hook}` must return a JSON object.")
    _validate_hook_response(hook, response)
    response.setdefault("chip_name", str(context.manifest.get("chip_name", context.chip_root.name)))
    response.setdefault("domain", str(context.manifest.get("domain", "unknown")))
    response.setdefault("hook", hook)
    response.setdefault("log_path", str(log_path))
    return response
