from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .authority import require_run_execution_authority
from .chips import invoke_chip_hook
from .collective import write_spark_swarm_collective_payload
from .config import CandidateTrial, ProjectConfig, intent_policy, load_config, mutation_lookup, resolve_project_root, trial_applies_to_command
from .failures import record_failure
from .paths import IGNORED_NAMES, ledger_path, resolve_runtime_root, runs_root
from .tracing import start_trace


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    command: list[str]
    cwd: str


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def run_authority_args_path(
    config_path: Path,
    command_name: str,
    *,
    mode: str = "once",
    candidate_id: str | None = None,
    overrides: dict[str, str] | None = None,
    limit: int | None = None,
    rounds: int | None = None,
    max_passes: int | None = None,
) -> str:
    payload = {
        "candidate_id": candidate_id or "baseline",
        "command_name": command_name,
        "config_path": str(config_path.resolve()),
        "limit": limit,
        "max_passes": max_passes,
        "mode": mode,
        "overrides": overrides or {},
        "rounds": rounds,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return (
        f"researcher-run://{config_path.resolve().as_posix()}"
        f"#mode={mode};command={command_name};candidate={payload['candidate_id']};binding={digest}"
    )


def _authority_summary(verification: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": verification.get("schema_version"),
        "allowed": bool(verification.get("allowed")),
        "decision_id": verification.get("decision_id"),
        "turn_id": verification.get("turn_id"),
        "tool_name": verification.get("tool_name"),
        "capability_id": verification.get("capability_id"),
        "authorization_decision_id": verification.get("authorization_decision_id"),
        "ledger_id": verification.get("ledger_id"),
    }


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


@contextmanager
def locked_file(path: Path, *, timeout_seconds: float = 30.0):
    ensure_parent(path)
    lock_path = path.with_name(path.name + ".lock")
    deadline = time.monotonic() + timeout_seconds
    handle: int | None = None
    while handle is None:
        try:
            handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                owner = None
                try:
                    owner = lock_path.read_text(encoding="utf-8", errors="ignore").strip()[:64] or None
                except OSError:
                    owner = None
                suffix = f" (owner={owner})" if owner else ""
                raise TimeoutError(f"Timed out waiting for ledger lock: {lock_path}{suffix}")
            time.sleep(0.05)
    try:
        os.write(handle, str(os.getpid()).encode("ascii", errors="ignore"))
        yield
    finally:
        os.close(handle)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    with locked_file(path):
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")


def make_run_id(kind: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    return f"{stamp}-{kind}"


def _normalize_workspace_excludes(excludes: list[str] | None) -> tuple[str, ...]:
    normalized: list[str] = []
    for item in excludes or []:
        value = str(item).strip().replace("\\", "/").strip("/")
        if not value or value == ".":
            continue
        normalized.append(value.casefold())
    return tuple(dict.fromkeys(normalized))


def _is_excluded_copy_path(rel_path: str, excludes: tuple[str, ...]) -> bool:
    path = rel_path.casefold()
    return any(path == excluded or path.startswith(f"{excluded}/") for excluded in excludes)


def _copytree_ignore(source_root: Path, extra_excludes: list[str] | None = None):
    source_root = source_root.resolve()
    excludes = _normalize_workspace_excludes(extra_excludes)

    def _ignore(current_root: str, names: list[str]) -> set[str]:
        ignored = {name for name in names if name in IGNORED_NAMES}
        if not excludes:
            return ignored
        current_path = Path(current_root)
        for name in names:
            rel_path = (current_path / name).relative_to(source_root).as_posix()
            if _is_excluded_copy_path(rel_path, excludes):
                ignored.add(name)
        return ignored

    return _ignore


def copy_project_tree(source_root: Path, target_root: Path, *, extra_excludes: list[str] | None = None) -> None:
    shutil.copytree(
        source_root,
        target_root,
        dirs_exist_ok=True,
        ignore=_copytree_ignore(source_root, extra_excludes),
    )


def cleanup_workspace(workspace_root: Path) -> None:
    if workspace_root.exists():
        shutil.rmtree(workspace_root, ignore_errors=True)


def safe_finish_trace(trace: Any, *, status: str, attributes: dict[str, Any] | None = None) -> None:
    try:
        trace.finish(status=status, attributes=attributes or {})
    except OSError:
        # Trace persistence should never hide the original run failure.
        return


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
            known = ", ".join(sorted(lookup))
            if known:
                raise KeyError(f"Unknown mutable parameter: {name}. Known mutable parameters: {known}.")
            raise KeyError(
                f"Unknown mutable parameter: {name}. "
                "No mutable parameters are defined; add entries under `mutable_parameters` in the project config."
            )
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


def _virtual_mutations(mutations: dict[str, str]) -> list[dict[str, str]]:
    return [{"name": name, "value": value, "file": "<chip>"} for name, value in sorted(mutations.items())]


def run_chip_evaluate(
    config_path: Path,
    command_name: str,
    config: ProjectConfig,
    command_spec: Any,
    workspace_root: Path,
    log_path: Path,
    trial: CandidateTrial | None,
    *,
    dry_run: bool = False,
) -> tuple[CommandResult, dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    ensure_parent(log_path)
    mutations = dict(trial.mutations if trial else {})
    applied_mutations = _virtual_mutations(mutations)
    payload = {
        "project_name": config.project_name,
        "command_name": command_name,
        "command_kind": command_spec.kind,
        "command_args": list(command_spec.args),
        "workspace_root": str(workspace_root),
        "candidate": {
            "candidate_id": trial.candidate_id if trial else "baseline",
            "candidate_summary": trial.candidate_summary if trial else "",
            "hypothesis": trial.hypothesis if trial else "",
            "mutations": mutations,
        },
        "metrics": {name: {"kind": spec.kind, "pattern": spec.pattern} for name, spec in config.metrics.items()},
        "eval_metric": config.eval_metric,
        "eval_goal": config.eval_goal,
        "intent": intent_policy(config),
    }
    response = invoke_chip_hook(config_path, "evaluate", payload, config=config, dry_run=dry_run)
    stdout = str(response.get("stdout", ""))
    stderr = str(response.get("stderr", ""))
    log_lines = [stdout]
    if stderr:
        log_lines.extend(["[stderr]", stderr])
    if response.get("metrics"):
        log_lines.extend(["[metrics]", json.dumps(response["metrics"], indent=2, sort_keys=True)])
    log_path.write_text("\n".join(item for item in log_lines if item).rstrip() + "\n", encoding="utf-8")
    command_result = CommandResult(
        returncode=int(response.get("returncode", 0)),
        stdout=stdout,
        stderr=stderr,
        command=["<chip:evaluate>"],
        cwd=str(workspace_root),
    )
    metrics = response.get("metrics", {})
    metrics = metrics if isinstance(metrics, dict) else {}
    chip_result = response.get("result", {})
    chip_result = chip_result if isinstance(chip_result, dict) else {}
    return command_result, {str(key): value for key, value in metrics.items()}, applied_mutations, chip_result


def best_metric(runtime_root: Path, command_name: str, goal: str, *, comparison_class: str | None = None) -> float | None:
    values = [
        row.get("metric_value")
        for row in read_jsonl(ledger_path(runtime_root))
        if row.get("command_name") == command_name
        and row.get("status") == "ok"
        and isinstance(row.get("metric_value"), (int, float))
        and (
            comparison_class is None
            or str((row.get("chip_result", {}) if isinstance(row.get("chip_result", {}), dict) else {}).get("comparison_class", "")) == comparison_class
        )
    ]
    if not values:
        return None
    return max(values) if goal == "maximize" else min(values)


def baseline_metric(runtime_root: Path, command_name: str, goal: str) -> float | None:
    values = [
        float(row["metric_value"])
        for row in read_jsonl(ledger_path(runtime_root))
        if row.get("command_name") == command_name
        and row.get("status") == "ok"
        and isinstance(row.get("metric_value"), (int, float))
        and not row.get("applied_mutations")
    ]
    if not values:
        return None
    return max(values) if goal == "maximize" else min(values)


def metric_verdict(metric_value: float | None, baseline_value: float | None, goal: str, tolerance: float = 0.0) -> str:
    if metric_value is None:
        return "unknown"
    if baseline_value is None:
        return "baseline"
    if metric_value == baseline_value:
        return "flat"
    improved = metric_value > baseline_value if goal == "maximize" else metric_value < baseline_value
    if improved:
        return "improved"
    if tolerance > 0 and baseline_value != 0:
        gap = abs(metric_value - baseline_value) / abs(baseline_value)
        if gap <= tolerance:
            return "near_best"
    return "regressed"


def row_counts_as_discard(row: dict[str, Any]) -> bool:
    if str(row.get("status") or "") != "ok":
        return True
    return str(row.get("verdict") or "") in {"regressed", "unknown"}


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
    chip_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
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
    if chip_result:
        record["chip_result"] = chip_result
    return record


def _refresh_chip_working_memory(
    config: ProjectConfig,
    runtime_root: Path,
    record: dict[str, Any],
    *,
    governor_decision: dict[str, Any] | None = None,
) -> None:
    from .memory import write_working_memory

    if governor_decision is None:
        return
    chip_result = record.get("chip_result", {})
    if not isinstance(chip_result, dict):
        return
    if str(chip_result.get("comparison_class", "")).strip() != "benchmark_grounded":
        return
    metric_value = record.get("metric_value")
    benchmark_profile = str(chip_result.get("benchmark_profile") or "unknown").strip() or "unknown"
    operator_label = str(chip_result.get("baseline_id") or "unknown").strip() or "unknown"
    if str(chip_result.get("operator_mode") or "").strip() == "script":
        model = str(chip_result.get("operator_model") or "unknown").strip() or "unknown"
        operator_label = f"{model} script operator"
    track_summaries = chip_result.get("track_summaries", [])
    best_track = None
    weakest_track = None
    if isinstance(track_summaries, list) and track_summaries:
        scored_tracks = [item for item in track_summaries if isinstance(item, dict)]
        if scored_tracks:
            best_track = max(scored_tracks, key=lambda item: float(item.get("scenario_score_mean", 0.0) or 0.0))
            weakest_track = min(scored_tracks, key=lambda item: float(item.get("scenario_score_mean", 0.0) or 0.0))
    focus = (
        f"{config.project_name} state: benchmark-grounded doctrine is led by {operator_label} "
        f"on {benchmark_profile} at {config.eval_metric} {metric_value}. "
        f"Frontier probes remain exploratory and should not be compared directly against "
        "benchmark-grounded doctrine."
    )
    if weakest_track is not None:
        focus += f" The active weakest grounded transfer surface is {weakest_track.get('track', 'unknown')}."
    notes = [
        "Grounded doctrine is stored in chip doctrine documents inside artifacts/memory/documents.",
        f"Latest benchmark-grounded run_id is {record.get('run_id')}.",
        "Frontier heuristics remain useful for idea generation but are a separate comparison lane.",
    ]
    lesson = str(chip_result.get("lesson") or "").strip()
    next_probe = str(chip_result.get("next_probe") or "").strip()
    if best_track is not None:
        notes.append(
            f"Strongest grounded track is {best_track.get('track', 'unknown')} at {best_track.get('scenario_score_mean', 'n/a')}."
        )
    if lesson:
        notes.append(lesson)
    questions = []
    if next_probe:
        questions.append(next_probe)
    if weakest_track is not None:
        questions.append(
            f"What grounded probe should target the weakest track {weakest_track.get('track', 'unknown')} next?"
        )
    questions.append("Should exploratory frontier ideas be promoted only after benchmark re-expression?")
    write_working_memory(
        runtime_root,
        kind="chip_state",
        focus=focus,
        status="active",
        trace_id=str(record.get("trace_id") or "") or None,
        notes=notes,
        questions=questions,
        governor_decision=governor_decision,
    )


def run_once(
    config_path: Path,
    command_name: str,
    *,
    trial: CandidateTrial | None = None,
    overrides: dict[str, str] | None = None,
    dry_run: bool = False,
    governor_decision: dict[str, Any] | None = None,
    authority_args_path: str | None = None,
    memory_governor_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    runtime_root = resolve_runtime_root(config_path)
    project_root = resolve_project_root(config_path, config)
    command_spec = config.commands[command_name]
    run_authority = None
    if not dry_run:
        run_authority = require_run_execution_authority(
            governor_decision,
            args_path=authority_args_path
            or run_authority_args_path(
                config_path,
                command_name,
                candidate_id=trial.candidate_id if trial else None,
                overrides=overrides,
            ),
        )
    trace = start_trace(
        runtime_root,
        kind="run",
        name=command_name,
        attributes={
            "project_name": config.project_name,
            "candidate_id": trial.candidate_id if trial else "baseline",
            "dry_run": dry_run,
        },
    )
    run_id = make_run_id(command_spec.kind)
    run_dir = runs_root(runtime_root) / run_id
    workspace_root = run_dir / "workspace"
    try:
        with trace.span("copy_project_tree", attributes={"project_root": str(project_root), "workspace_root": str(workspace_root)}):
            copy_project_tree(project_root, workspace_root, extra_excludes=config.workspace_excludes)
        log_path = run_dir / command_spec.log_name
        if command_spec.kind == "chip-evaluate":
            if overrides:
                raise RuntimeError("Direct overrides are not supported for chip-evaluate commands.")
            with trace.span("chip_evaluate", attributes={"command_kind": command_spec.kind}):
                command_result, hook_metrics, applied_mutations, chip_result = run_chip_evaluate(
                    config_path,
                    command_name,
                    config,
                    command_spec,
                    workspace_root,
                    log_path,
                    trial,
                    dry_run=dry_run,
                )
            with trace.span("parse_metrics", attributes={"metric_count": len(config.metrics)}):
                metrics = parse_metrics(log_path, config.metrics)
                metrics.update(hook_metrics)
        else:
            mutations = dict(trial.mutations if trial else {})
            mutations.update(overrides or {})
            with trace.span("apply_mutations", attributes={"mutation_count": len(mutations)}):
                applied_mutations = apply_mutations(workspace_root, config, mutations) if mutations else []
            cwd = (workspace_root / command_spec.cwd).resolve()
            with trace.span("run_process", attributes={"cwd": str(cwd), "command": command_spec.args, "dry_run": dry_run}):
                command_result = run_process(command_spec.args, cwd, log_path, dry_run=dry_run)
            with trace.span("parse_metrics", attributes={"metric_count": len(config.metrics)}):
                metrics = parse_metrics(log_path, config.metrics)
            chip_result = None
        comparison_class = str(chip_result.get("comparison_class", "")).strip() if isinstance(chip_result, dict) else ""
        baseline_only = not applied_mutations
        baseline_value = (
            baseline_metric(runtime_root, command_name, config.eval_goal)
            if baseline_only
            else best_metric(runtime_root, command_name, config.eval_goal, comparison_class=comparison_class or None)
        )
        metric_value = metrics.get(config.eval_metric)
        numeric_metric = metric_value if isinstance(metric_value, (int, float)) else None
        verdict = metric_verdict(numeric_metric, baseline_value, config.eval_goal, config.guardrails.near_best_tolerance)
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
            chip_result=chip_result,
        )
        if run_authority is not None:
            record["authority"] = _authority_summary(run_authority)
        record["trace_id"] = trace.trace_id
        record["trace_path"] = str(trace.path)
        if dry_run:
            record["dry_run"] = True
            safe_finish_trace(trace, status="ok", attributes={"mode": "dry_run", "verdict": verdict, "metric_value": numeric_metric})
            return record
        with trace.span("persist_record", attributes={"verdict": verdict, "metric_value": numeric_metric}):
            ensure_parent(run_dir / "result.json")
            (run_dir / "result.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            append_jsonl(ledger_path(runtime_root), record)
        write_spark_swarm_collective_payload(config_path.parent.resolve(), runtime_root, config, record)
        _refresh_chip_working_memory(config, runtime_root, record, governor_decision=memory_governor_decision)
        if record["status"] != "ok" or verdict in {"regressed", "unknown"}:
            failure_type = "run_failed" if record["status"] != "ok" else f"run_{verdict}"
            evidence = [
                f"command={command_name}",
                f"candidate_id={trial.candidate_id if trial else 'baseline'}",
                f"metric_name={config.eval_metric}",
                f"metric_value={record.get('metric_value')}",
            ]
            record_failure(
                runtime_root,
                failure_type=failure_type,
                summary=str(trial.candidate_summary if trial else f"{command_name} {verdict}").strip(),
                surface="runner",
                domain=config.project_name,
                severity="critical" if record["status"] != "ok" else "warn",
                novelty_key=f"{command_name}:{verdict}",
                evidence=evidence,
                trace_id=trace.trace_id,
                metadata={
                    "run_id": record["run_id"],
                    "candidate_id": record.get("candidate_id"),
                    "command_name": command_name,
                    "verdict": verdict,
                    "mutations": list(record.get("applied_mutations", [])),
                },
            )
        safe_finish_trace(trace, status="ok", attributes={"verdict": verdict, "metric_value": numeric_metric})
        return record
    except Exception as exc:
        safe_finish_trace(trace, status="error", attributes={"error": str(exc)})
        raise
    finally:
        cleanup_workspace(workspace_root)


def parse_overrides(items: list[str] | None) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise RuntimeError(f"Override must look like name=value, got: {item}")
        name, value = item.split("=", 1)
        overrides[name.strip()] = value.strip()
    return overrides


def run_loop(
    config_path: Path,
    command_name: str,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    governor_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    requested_limit = limit or config.guardrails.max_loop_iterations
    max_iterations = min(requested_limit, config.guardrails.max_loop_iterations)
    authority_args_path = run_authority_args_path(config_path, command_name, mode="loop", limit=max_iterations)
    consecutive_discards = 0
    results: list[dict[str, Any]] = []
    pending_trials = [trial for trial in config.candidate_trials if trial_applies_to_command(trial, command_name)]
    for trial in pending_trials[:max_iterations]:
        record = run_once(
            config_path,
            command_name,
            trial=trial,
            dry_run=dry_run,
            governor_decision=governor_decision,
            authority_args_path=authority_args_path,
        )
        results.append(record)
        if record["verdict"] == "improved":
            consecutive_discards = 0
        elif row_counts_as_discard(record):
            consecutive_discards += 1
        if consecutive_discards >= config.guardrails.consecutive_discard_limit:
            break
    return {
        "project_name": config.project_name,
        "command_name": command_name,
        "run_count": len(results),
        "requested_limit": requested_limit,
        "max_iterations": max_iterations,
        "limit_clamped_to_guardrail": requested_limit > max_iterations,
        "stopped_for_discard_limit": consecutive_discards >= config.guardrails.consecutive_discard_limit,
        "results": results,
    }


def ledger_summary(runtime_root: Path, *, limit: int = 10, goal: str = "minimize") -> dict[str, Any]:
    rows = read_jsonl(ledger_path(runtime_root))
    recent = list(reversed(rows[-limit:]))
    best_by_metric: dict[str, float] = {}
    for row in rows:
        metric_name = str(row.get("metric_name") or "")
        value = row.get("metric_value")
        if not metric_name or not isinstance(value, (int, float)):
            continue
        current = best_by_metric.get(metric_name)
        if current is None:
            best_by_metric[metric_name] = float(value)
            continue
        best_by_metric[metric_name] = max(float(current), float(value)) if goal == "maximize" else min(float(current), float(value))
    return {"run_count": len(rows), "recent": recent, "best_by_metric": best_by_metric}
