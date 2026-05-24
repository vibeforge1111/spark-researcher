from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import TrainerSpec, load_config, resolve_project_root
from .paths import resolve_runtime_root, trainers_root


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def count_examples(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def trainer_state_path(runtime_root: Path, name: str) -> Path:
    return trainers_root(runtime_root) / f"{name}.json"


def trainer_should_run(spec: TrainerSpec, example_count: int, state: dict[str, Any]) -> tuple[bool, str]:
    if example_count < spec.min_examples:
        return False, f"need {spec.min_examples}, have {example_count}"
    compiled_count = int(state.get("compiled_example_count", 0))
    unseen = example_count - compiled_count
    if compiled_count == 0:
        return True, "first eligible compile"
    if unseen >= spec.recompile_every:
        return True, f"{unseen} new examples since last compile"
    return False, f"only {unseen} new examples since last compile"


def run_trainer(spec: TrainerSpec, project_root: Path, runtime_root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    examples_path = (project_root / spec.examples_path).resolve()
    state_path = trainer_state_path(runtime_root, spec.name)
    state = read_state(state_path)
    example_count = count_examples(examples_path)
    should_run, reason = trainer_should_run(spec, example_count, state)
    result = {
        "trainer": spec.name,
        "examples_path": str(examples_path),
        "example_count": example_count,
        "should_run": should_run,
        "reason": reason,
        "dry_run": dry_run,
    }
    if not should_run:
        write_state(
            state_path,
            {
                **state,
                "name": spec.name,
                "example_count": example_count,
                "last_seen_at": now_iso(),
                "last_status": "skipped",
                "last_reason": reason,
            },
        )
        return result
    if dry_run:
        result["command"] = spec.compile_command
        result["status"] = "dry_run"
        return result
    process = subprocess.run(
        spec.compile_command,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    updated = {
        "name": spec.name,
        "example_count": example_count,
        "compiled_example_count": min(example_count, spec.max_examples),
        "compile_count": int(state.get("compile_count", 0)) + (1 if process.returncode == 0 else 0),
        "last_seen_at": now_iso(),
        "last_status": "ok" if process.returncode == 0 else "failed",
        "last_reason": reason,
        "stdout_excerpt": process.stdout[:400],
        "stderr_excerpt": process.stderr[:400],
        "command": spec.compile_command,
    }
    write_state(state_path, updated)
    result.update(updated)
    return result


def run_all_trainers(config_path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    config = load_config(config_path)
    project_root = resolve_project_root(config_path, config)
    runtime_root = resolve_runtime_root(config_path)
    return {
        "project_name": config.project_name,
        "results": [run_trainer(spec, project_root, runtime_root, dry_run=dry_run) for spec in config.trainers],
    }


def trainer_status(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    runtime_root = resolve_runtime_root(config_path)
    rows = []
    for spec in config.trainers:
        state_path = trainer_state_path(runtime_root, spec.name)
        rows.append(read_state(state_path) if state_path.exists() else {"name": spec.name, "last_status": "never_run"})
    return {"project_name": config.project_name, "trainers": rows}

