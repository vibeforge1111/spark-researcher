from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import CandidateTrial, load_config, save_config
from .paths import ledger_path, resolve_runtime_root
from .runner import read_jsonl, run_once


def _signature(mutations: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), str(value)) for key, value in mutations.items()))


def _signature_from_row(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(item["name"]), str(item["value"])) for item in row.get("applied_mutations", [])))


def _metric_is_better(candidate: float, baseline: float | None, goal: str) -> bool:
    if baseline is None:
        return True
    return candidate > baseline if goal == "maximize" else candidate < baseline


def _best_value(values: list[float], goal: str) -> float | None:
    if not values:
        return None
    return max(values) if goal == "maximize" else min(values)


def _format_value(value: str) -> str:
    return value.replace(".", "").replace("-", "m")


def _candidate_id(mutations: dict[str, str]) -> str:
    parts = [f"{name}-{_format_value(value)}" for name, value in sorted(mutations.items())]
    return "combo-" + "-".join(parts)


def _baseline_metric(rows: list[dict[str, Any]], command_name: str, goal: str) -> float | None:
    baseline_values = [
        float(row["metric_value"])
        for row in rows
        if row.get("command_name") == command_name
        and isinstance(row.get("metric_value"), (int, float))
        and not row.get("applied_mutations")
    ]
    return _best_value(baseline_values, goal)


def _tested_signatures(rows: list[dict[str, Any]], command_name: str) -> set[tuple[tuple[str, str], ...]]:
    return {
        _signature_from_row(row)
        for row in rows
        if row.get("command_name") == command_name
    }


def _best_single_primitives(rows: list[dict[str, Any]], command_name: str, goal: str, baseline_metric: float | None) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("command_name") != command_name:
            continue
        metric_value = row.get("metric_value")
        mutations = row.get("applied_mutations") or []
        if not isinstance(metric_value, (int, float)) or len(mutations) != 1:
            continue
        mutation = mutations[0]
        name = str(mutation["name"])
        value = str(mutation["value"])
        row_metric = float(metric_value)
        beneficial = _metric_is_better(row_metric, baseline_metric, goal) or row.get("verdict") == "improved"
        if not beneficial:
            continue
        current = best.get(name)
        if current is None or _metric_is_better(row_metric, float(current["metric_value"]), goal):
            best[name] = {
                "name": name,
                "value": value,
                "metric_value": row_metric,
                "candidate_id": row.get("candidate_id"),
                "reason": "beats baseline" if baseline_metric is not None and _metric_is_better(row_metric, baseline_metric, goal) else "improved run",
            }
    return best


def suggest_trials(config_path: Path, command_name: str, *, limit: int = 3) -> dict[str, Any]:
    config = load_config(config_path)
    runtime_root = resolve_runtime_root(config_path)
    rows = read_jsonl(ledger_path(runtime_root))
    baseline_metric = _baseline_metric(rows, command_name, config.eval_goal)
    tested = _tested_signatures(rows, command_name)
    existing = {_signature(trial.mutations) for trial in config.candidate_trials}
    primitives = _best_single_primitives(rows, command_name, config.eval_goal, baseline_metric)

    suggestions: list[CandidateTrial] = []
    reasons: list[str] = []

    if len(primitives) > 1:
        combined_mutations = {name: str(item["value"]) for name, item in sorted(primitives.items())}
        combined_signature = _signature(combined_mutations)
        if combined_signature not in tested and combined_signature not in existing:
            source_text = ", ".join(f"{name}={item['value']}" for name, item in sorted(primitives.items()))
            suggestions.append(
                CandidateTrial(
                    candidate_id=_candidate_id(combined_mutations),
                    candidate_summary=f"Combine baseline-beating primitives: {source_text}.",
                    hypothesis="Beneficial single mutations may compound when applied together.",
                    mutations=combined_mutations,
                )
            )
            reasons.append("Combine beneficial single-parameter mutations that each beat the baseline.")

    for name, item in sorted(primitives.items()):
        single_mutation = {name: str(item["value"])}
        sig = _signature(single_mutation)
        if sig in tested or sig in existing:
            continue
        suggestions.append(
            CandidateTrial(
                candidate_id=f"{name}-{_format_value(str(item['value']))}-retest",
                candidate_summary=f"Retest the best observed primitive for `{name}`.",
                hypothesis=f"The best observed value for `{name}` should be confirmed directly in the current loop.",
                mutations=single_mutation,
            )
        )
        reasons.append(f"Retest beneficial primitive {name}={item['value']}.")
        if len(suggestions) >= limit:
            break

    trimmed = suggestions[:limit]
    return {
        "command_name": command_name,
        "baseline_metric": baseline_metric,
        "beneficial_primitives": list(primitives.values()),
        "suggestion_count": len(trimmed),
        "reasons": reasons[: len(trimmed)],
        "suggestions": [asdict(item) for item in trimmed],
    }


def append_suggestions(config_path: Path, suggestions: list[dict[str, Any]]) -> dict[str, Any]:
    config = load_config(config_path)
    existing = {_signature(trial.mutations) for trial in config.candidate_trials}
    appended: list[dict[str, Any]] = []
    for item in suggestions:
        trial = CandidateTrial(
            candidate_id=str(item["candidate_id"]),
            candidate_summary=str(item.get("candidate_summary", "")),
            hypothesis=str(item.get("hypothesis", "")),
            mutations={str(key): str(value) for key, value in item.get("mutations", {}).items()},
        )
        sig = _signature(trial.mutations)
        if sig in existing:
            continue
        config.candidate_trials.append(trial)
        existing.add(sig)
        appended.append(asdict(trial))
    if appended:
        save_config(config_path, config)
    return {"appended_count": len(appended), "appended": appended, "config_path": str(config_path)}


def run_autoloop(
    config_path: Path,
    command_name: str,
    *,
    rounds: int = 3,
    suggest_limit: int = 3,
    dry_run: bool = False,
    apply_suggestions: bool = True,
) -> dict[str, Any]:
    history: list[dict[str, Any]] = []
    for round_index in range(1, rounds + 1):
        config = load_config(config_path)
        runtime_root = resolve_runtime_root(config_path)
        rows = read_jsonl(ledger_path(runtime_root))
        tested = _tested_signatures(rows, command_name)
        pending = [trial for trial in config.candidate_trials if _signature(trial.mutations) not in tested]

        if not pending:
            suggestion_packet = suggest_trials(config_path, command_name, limit=suggest_limit)
            append_packet = append_suggestions(config_path, suggestion_packet["suggestions"]) if apply_suggestions else {"appended_count": 0, "appended": []}
            if int(append_packet["appended_count"]) <= 0:
                history.append(
                    {
                        "round": round_index,
                        "run_count": 0,
                        "results": [],
                        "suggestions": suggestion_packet,
                        "appended": append_packet,
                        "stopped": "no_pending_trials_or_new_suggestions",
                    }
                )
                break
            config = load_config(config_path)
            pending = [trial for trial in config.candidate_trials if _signature(trial.mutations) not in tested]
        else:
            suggestion_packet = {"suggestion_count": 0, "suggestions": [], "reasons": []}
            append_packet = {"appended_count": 0, "appended": []}

        consecutive_discards = 0
        results: list[dict[str, Any]] = []
        for trial in pending[: config.guardrails.max_loop_iterations]:
            record = run_once(config_path, command_name, trial=trial, dry_run=dry_run)
            results.append(record)
            if record["verdict"] == "improved":
                consecutive_discards = 0
            elif record["verdict"] in {"regressed", "flat"}:
                consecutive_discards += 1
            if consecutive_discards >= config.guardrails.consecutive_discard_limit:
                break

        post_suggestions = suggest_trials(config_path, command_name, limit=suggest_limit)
        post_append = append_suggestions(config_path, post_suggestions["suggestions"]) if apply_suggestions else {"appended_count": 0, "appended": []}
        history.append(
            {
                "round": round_index,
                "run_count": len(results),
                "results": results,
                "suggestions": post_suggestions,
                "appended": post_append,
                "stopped_for_discard_limit": consecutive_discards >= config.guardrails.consecutive_discard_limit,
            }
        )
        if len(results) == 0 and int(post_append["appended_count"]) <= 0:
            break

    return {
        "command_name": command_name,
        "project_name": load_config(config_path).project_name,
        "round_count": len(history),
        "history": history,
    }
