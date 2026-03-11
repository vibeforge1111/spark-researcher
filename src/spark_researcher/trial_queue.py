from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .config import CandidateTrial, ProjectConfig
from .paths import frontier_queue_path, resolve_runtime_root


def _signature(mutations: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), str(value)) for key, value in mutations.items()))


def _signature_from_row(row: dict[str, object]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(item["name"]), str(item["value"])) for item in row.get("applied_mutations", [])))


def queue_path_for_config(config_path: Path) -> Path:
    return frontier_queue_path(resolve_runtime_root(config_path))


def load_queue_trials(config_path: Path) -> list[CandidateTrial]:
    path = queue_path_for_config(config_path)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    items = payload.get("candidate_trials", [])
    if not isinstance(items, list):
        return []
    trials: list[CandidateTrial] = []
    for item in items:
        if not isinstance(item, dict) or "candidate_id" not in item:
            continue
        trials.append(
            CandidateTrial(
                candidate_id=str(item["candidate_id"]),
                candidate_summary=str(item.get("candidate_summary", "")),
                hypothesis=str(item.get("hypothesis", "")),
                mutations={str(key): str(value) for key, value in item.get("mutations", {}).items()},
            )
        )
    return trials


def merged_candidate_trials(config_path: Path, *, config: ProjectConfig | None = None) -> list[CandidateTrial]:
    merged: list[CandidateTrial] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for trial in (config.candidate_trials if config is not None else []):
        sig = _signature(trial.mutations)
        if sig in seen:
            continue
        seen.add(sig)
        merged.append(trial)
    for trial in load_queue_trials(config_path):
        sig = _signature(trial.mutations)
        if sig in seen:
            continue
        seen.add(sig)
        merged.append(trial)
    return merged


def append_queue_trials(config_path: Path, trials: list[CandidateTrial], *, config: ProjectConfig | None = None) -> dict[str, object]:
    path = queue_path_for_config(config_path)
    existing_trials = merged_candidate_trials(config_path, config=config)
    seen = {_signature(trial.mutations) for trial in existing_trials}
    queue_trials = load_queue_trials(config_path)
    appended: list[dict[str, object]] = []
    for trial in trials:
        sig = _signature(trial.mutations)
        if sig in seen:
            continue
        seen.add(sig)
        queue_trials.append(trial)
        appended.append(asdict(trial))
    if appended:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"candidate_trials": [asdict(item) for item in queue_trials]}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {"appended_count": len(appended), "appended": appended, "queue_path": str(path)}


def pending_queue_trials(config_path: Path, rows: list[dict[str, object]]) -> list[CandidateTrial]:
    tested = {_signature_from_row(row) for row in rows}
    return [trial for trial in load_queue_trials(config_path) if _signature(trial.mutations) not in tested]


def pending_queue_count(config_path: Path, rows: list[dict[str, object]]) -> int:
    return len(pending_queue_trials(config_path, rows))
