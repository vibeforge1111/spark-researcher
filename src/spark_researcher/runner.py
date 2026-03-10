from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import CandidateTrial, ProjectConfig, load_config, mutation_lookup, resolve_project_root
from .paths import IGNORED_NAMES, ledger_path, resolve_runtime_root, runs_root


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    command: list[str]
    cwd: str


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def make_run_id(kind: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    return f"{stamp}-{kind}"


def copy_project_tree(source_root: Path, target_root: Path) -> None:
    shutil.copytree(
        source_root,
        target_root,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(*IGNORED_NAMES),
    )


def run_process(command: list[str], cwd: Path, log_path: Path, *, dry_run: bool = False) -> CommandResult:
    ensure_parent(log_path)
    if dry_run:
        preview = {"cwd": str(cwd), "command": command}
        log_path.write_text(json.dumps(preview, indent=2) + "\n", encoding="utf-8")
        return CommandResult(returncode=0, stdout=json.dumps(preview), stderr="", command=command, cwd=str(cwd))
    result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    log_path.write_text(result.stdout + ("\n[stderr]\n" + result.stderr if result.stderr else ""), encoding="utf-8")
    return CommandResult(result.returncode, result.stdout, result.stderr, command, str(cwd))


def parse_metric_value(kind: str, raw: str) -> float | int | str:
    if kind == "int":
        return int(float(raw))
    if kind == "str":
        return raw
    return float(raw)


def parse_metrics(log_path: Path, metrics: dict[str, Any]) -> dict[str, Any]:
    if not log_path.exists():
        return {}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    parsed: dict[str, Any] = {}
    for name, spec in metrics.items():
        match = re.search(spec.pattern, text, re.MULTILINE)
        parsed[name] = parse_metric_value(spec.kind, match.group(1)) if match else None
    return parsed


def apply_mutations(workspace_root: Path, config: ProjectConfig, mutations: dict[str, str]) -> list[dict[str, str]]:
    applied: list[dict[str, str]] = []
    lookup = mutation_lookup(config)
    for name, value in mutations.items():
        if name not in lookup:
            raise KeyError(f"Unknown mutable parameter: {name}")
        spec = lookup[name]
        target_path = (workspace_root / spec.file).resolve()
        text = target_path.read_text(encoding="utf-8-sig")
        replacement = spec.template.format(value=value)
        updated, count = re.subn(spec.pattern, replacement, text, count=1)
        if count != 1:
            raise RuntimeError(f"Expected exactly one replacement for {name} in {target_path}")
        target_path.write_text(updated, encoding="utf-8")
        applied.append({"name": name, "value": value, "file": str(target_path.relative_to(workspace_root))})
    return applied


def best_metric(runtime_root: Path, command_name: str, goal: str) -> float | None:
    values = [
        row.get("metric_value")
        for row in read_jsonl(ledger_path(runtime_root))
        if row.get("command_name") == command_name and isinstance(row.get("metric_value"), (int, float))
    ]
    if not values:
        return None
    return max(values) if goal == "maximize" else min(values)


def metric_verdict(metric_value: float | None, baseline_value: float | None, goal: str) -> str:
    if metric_value is None:
        return "unknown"
    if baseline_value is None:
        return "baseline"
    if metric_value == baseline_value:
        return "flat"
    improved = metric_value > baseline_value if goal == "maximize" else metric_value < baseline_value
    return "improved" if improved else "regressed"


def build_record(
    config: ProjectConfig,
    command_name: str,
    command_result: CommandResult,
    run_dir: Path,
    log_path: Path,
    metrics: dict[str, Any],
    baseline_value: float | None,
    verdict: str,
    trial: CandidateTrial | None,
    applied_mutations: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "run_id": run_dir.name,
        "created_at": now_iso(),
        "project_name": config.project_name,
        "command_name": command_name,
        "status": "ok" if command_result.returncode == 0 else "failed",
        "returncode": command_result.returncode,
        "metric_name": config.eval_metric,
        "metric_value": metrics.get(config.eval_metric),
        "baseline_value": baseline_value,
        "verdict": verdict,
        "candidate_id": trial.candidate_id if trial else None,
        "candidate_summary": trial.candidate_summary if trial else "",
        "hypothesis": trial.hypothesis if trial else "",
        "applied_mutations": applied_mutations,
        "command": command_result.command,
        "cwd": command_result.cwd,
        "run_dir": str(run_dir),
        "workspace_root": str(run_dir / "workspace"),
        "log_path": str(log_path),
        "metrics": metrics,
        "stdout_excerpt": command_result.stdout[:500],
        "stderr_excerpt": command_result.stderr[:500],
    }


def run_once(
    config_path: Path,
    command_name: str,
    *,
    trial: CandidateTrial | None = None,
    overrides: dict[str, str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    config = load_config(config_path)
    runtime_root = resolve_runtime_root(config_path)
    project_root = resolve_project_root(config_path, config)
    command_spec = config.commands[command_name]
    run_id = make_run_id(command_spec.kind)
    run_dir = runs_root(runtime_root) / run_id
    workspace_root = run_dir / "workspace"
    copy_project_tree(project_root, workspace_root)
    mutations = dict(trial.mutations if trial else {})
    mutations.update(overrides or {})
    applied_mutations = apply_mutations(workspace_root, config, mutations) if mutations else []
    log_path = run_dir / command_spec.log_name
    cwd = (workspace_root / command_spec.cwd).resolve()
    command_result = run_process(command_spec.args, cwd, log_path, dry_run=dry_run)
    metrics = parse_metrics(log_path, config.metrics)
    baseline_value = best_metric(runtime_root, command_name, config.eval_goal)
    metric_value = metrics.get(config.eval_metric)
    numeric_metric = metric_value if isinstance(metric_value, (int, float)) else None
    verdict = metric_verdict(numeric_metric, baseline_value, config.eval_goal)
    record = build_record(
        config,
        command_name,
        command_result,
        run_dir,
        log_path,
        metrics,
        baseline_value,
        verdict,
        trial,
        applied_mutations,
    )
    ensure_parent(run_dir / "result.json")
    (run_dir / "result.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_jsonl(ledger_path(runtime_root), record)
    return record


def parse_overrides(items: list[str] | None) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise RuntimeError(f"Override must look like name=value, got: {item}")
        name, value = item.split("=", 1)
        overrides[name.strip()] = value.strip()
    return overrides


def run_loop(config_path: Path, command_name: str, *, dry_run: bool = False, limit: int | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    max_iterations = min(limit or config.guardrails.max_loop_iterations, config.guardrails.max_loop_iterations)
    consecutive_discards = 0
    results: list[dict[str, Any]] = []
    for trial in config.candidate_trials[:max_iterations]:
        record = run_once(config_path, command_name, trial=trial, dry_run=dry_run)
        results.append(record)
        if record["verdict"] == "improved":
            consecutive_discards = 0
        elif record["verdict"] in {"regressed", "flat"}:
            consecutive_discards += 1
        if consecutive_discards >= config.guardrails.consecutive_discard_limit:
            break
    return {
        "project_name": config.project_name,
        "command_name": command_name,
        "run_count": len(results),
        "stopped_for_discard_limit": consecutive_discards >= config.guardrails.consecutive_discard_limit,
        "results": results,
    }


def ledger_summary(runtime_root: Path, *, limit: int = 10) -> dict[str, Any]:
    rows = read_jsonl(ledger_path(runtime_root))
    recent = list(reversed(rows[-limit:]))
    best_by_metric: dict[str, float] = {}
    for row in rows:
        metric_name = str(row.get("metric_name") or "")
        value = row.get("metric_value")
        if not metric_name or not isinstance(value, (int, float)):
            continue
        current = best_by_metric.get(metric_name)
        best_by_metric[metric_name] = value if current is None else min(current, value)
    return {"run_count": len(rows), "recent": recent, "best_by_metric": best_by_metric}
