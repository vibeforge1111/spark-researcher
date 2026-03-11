from __future__ import annotations

import time
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .chips import chip_has_hook, invoke_chip_hook
from .config import CandidateTrial, MutationSpec, intent_policy, load_config, save_config
from .failures import load_failures, surprise_status
from .frontier import frontier_suggest
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


def _parse_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _format_decimal(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


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


def _numeric_specs(config: Any) -> dict[str, MutationSpec]:
    specs: dict[str, MutationSpec] = {}
    for spec in config.mutable_parameters:
        if spec.value_step and len(spec.value_range) == 2:
            specs[spec.name] = spec
    return specs


def _beneficial_numeric_anchors(
    rows: list[dict[str, Any]],
    command_name: str,
    goal: str,
    baseline_metric: float | None,
    specs: dict[str, MutationSpec],
) -> dict[str, dict[str, Any]]:
    anchors: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("command_name") != command_name:
            continue
        metric_value = row.get("metric_value")
        if not isinstance(metric_value, (int, float)):
            continue
        mutation_map = {str(item["name"]): str(item["value"]) for item in row.get("applied_mutations", [])}
        if not mutation_map:
            continue
        row_metric = float(metric_value)
        beneficial = _metric_is_better(row_metric, baseline_metric, goal) or row.get("verdict") == "improved"
        if not beneficial:
            continue
        for name, value in mutation_map.items():
            spec = specs.get(name)
            if spec is None or _parse_decimal(value) is None:
                continue
            current = anchors.get(name)
            if current is None or _metric_is_better(row_metric, float(current["metric_value"]), goal):
                anchors[name] = {
                    "name": name,
                    "value": value,
                    "metric_value": row_metric,
                    "candidate_id": row.get("candidate_id"),
                    "base_mutations": mutation_map,
                }
    return anchors


def _neighborhood_suggestions(
    anchors: dict[str, dict[str, Any]],
    specs: dict[str, MutationSpec],
    *,
    tested: set[tuple[tuple[str, str], ...]],
    existing: set[tuple[tuple[str, str], ...]],
    limit: int,
) -> tuple[list[CandidateTrial], list[str]]:
    suggestions: list[CandidateTrial] = []
    reasons: list[str] = []
    queued = set(tested | existing)
    for name, anchor in sorted(anchors.items()):
        if len(suggestions) >= limit:
            break
        spec = specs[name]
        step = _parse_decimal(spec.value_step)
        lower = _parse_decimal(spec.value_range[0])
        upper = _parse_decimal(spec.value_range[1])
        current_value = _parse_decimal(str(anchor["value"]))
        if None in {step, lower, upper, current_value}:
            continue
        base_mutations = {str(key): str(value) for key, value in dict(anchor["base_mutations"]).items()}
        for direction in (-1, 1):
            if len(suggestions) >= limit:
                break
            neighbor = current_value + (step * direction)
            if neighbor < lower or neighbor > upper:
                continue
            neighbor_value = _format_decimal(neighbor)
            if neighbor_value == str(anchor["value"]):
                continue
            candidate_mutations = dict(base_mutations) if base_mutations else {name: str(anchor["value"])}
            candidate_mutations[name] = neighbor_value
            sig = _signature(candidate_mutations)
            if sig in queued:
                continue
            queued.add(sig)
            focused = len(candidate_mutations) > 1
            focus_text = "best combo" if focused else "best observed primitive"
            suggestions.append(
                CandidateTrial(
                    candidate_id=f"neighbor-{_candidate_id(candidate_mutations)}",
                    candidate_summary=(
                        f"Probe `{name}` near the {focus_text} by moving from {anchor['value']} to {neighbor_value}."
                    ),
                    hypothesis=(
                        f"A small numeric move around the current winning value for `{name}` may improve further without changing the search axis."
                    ),
                    mutations=candidate_mutations,
                )
            )
            reasons.append(
                f"Explore the numeric neighborhood around {name}={anchor['value']} within the declared range {spec.value_range[0]}..{spec.value_range[1]}."
            )
    return suggestions, reasons


def _trial_from_packet(item: dict[str, Any]) -> CandidateTrial:
    return CandidateTrial(
        candidate_id=str(item["candidate_id"]),
        candidate_summary=str(item.get("candidate_summary", "")),
        hypothesis=str(item.get("hypothesis", "")),
        mutations={str(key): str(value) for key, value in item.get("mutations", {}).items()},
    )


def _serialize_trials(trials: list[CandidateTrial], *, limit: int) -> list[dict[str, Any]]:
    return [asdict(item) for item in trials[:limit]]


def _pending_trials(config: Any, tested: set[tuple[tuple[str, str], ...]]) -> list[CandidateTrial]:
    return [trial for trial in config.candidate_trials if _signature(trial.mutations) not in tested]


def _recent_runner_failures(runtime_root: Path, command_name: str, *, limit: int = 5) -> list[dict[str, Any]]:
    selected = []
    for row in reversed(load_failures(runtime_root)):
        if str(row.get("surface") or "") != "runner":
            continue
        metadata = row.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        if str(metadata.get("command_name") or "") != command_name:
            continue
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def _failure_guided_suggestions(
    runtime_root: Path,
    command_name: str,
    *,
    tested: set[tuple[tuple[str, str], ...]],
    existing: set[tuple[tuple[str, str], ...]],
    primitives: dict[str, dict[str, Any]],
    limit: int,
) -> tuple[list[CandidateTrial], list[str], list[dict[str, Any]]]:
    suggestions: list[CandidateTrial] = []
    reasons: list[str] = []
    focus = _recent_runner_failures(runtime_root, command_name, limit=5)
    queued = set(tested | existing)
    for failure in focus:
        if len(suggestions) >= limit:
            break
        metadata = failure.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        mutations = {
            str(item.get("name")): str(item.get("value"))
            for item in metadata.get("mutations", [])
            if isinstance(item, dict) and item.get("name") is not None and item.get("value") is not None
        }
        if len(mutations) > 1:
            for name, value in sorted(mutations.items()):
                if len(suggestions) >= limit:
                    break
                isolate = {name: value}
                sig = _signature(isolate)
                if sig in queued:
                    continue
                queued.add(sig)
                suggestions.append(
                    CandidateTrial(
                        candidate_id=f"isolate-{name}-{_format_value(value)}",
                        candidate_summary=f"Isolate `{name}={value}` from a recent failing combo to locate the failure source.",
                        hypothesis="Breaking a surprising failed combo into single-axis tests can reveal which mutation is causing the miss.",
                        mutations=isolate,
                    )
                )
                reasons.append(f"Recent surprising failure suggests isolating `{name}` from a failed combo before more comfort-zone optimization.")
        elif len(mutations) == 1:
            name, value = next(iter(mutations.items()))
            primitive = primitives.get(name)
            if primitive is None:
                continue
            recover = {name: str(primitive["value"])}
            sig = _signature(recover)
            if sig in queued or str(primitive["value"]) == value:
                continue
            queued.add(sig)
            suggestions.append(
                CandidateTrial(
                    candidate_id=f"recover-{name}-{_format_value(str(primitive['value']))}",
                    candidate_summary=f"Recover `{name}` from the failing value {value} back toward the best observed value {primitive['value']}.",
                    hypothesis="A recent single-axis failure suggests moving back toward the strongest known primitive before exploring further.",
                    mutations=recover,
                )
            )
            reasons.append(f"Recent surprising failure suggests recovering `{name}` toward its strongest observed primitive.")
    focus_packet = [
        {
            "failure_type": item.get("failure_type"),
            "summary": item.get("summary"),
            "created_at": item.get("created_at"),
            "metadata": item.get("metadata"),
        }
        for item in focus
    ]
    return suggestions, reasons, focus_packet


def _chip_suggestion_packet(
    config_path: Path,
    config: Any,
    command_name: str,
    rows: list[dict[str, Any]],
    *,
    limit: int,
) -> dict[str, Any]:
    runtime_root = resolve_runtime_root(config_path)
    failure_priorities = surprise_status(runtime_root, limit=5)
    packet = invoke_chip_hook(
        config_path,
        "suggest",
        {
            "project_name": config.project_name,
            "command_name": command_name,
            "limit": limit,
            "eval_metric": config.eval_metric,
            "eval_goal": config.eval_goal,
            "intent": intent_policy(config),
            "failure_priorities": failure_priorities,
            "ledger_rows": rows,
            "candidate_trials": [asdict(item) for item in config.candidate_trials],
        },
        config=config,
    )
    suggestions = [_trial_from_packet(item) for item in packet.get("suggestions", [])]
    if suggestions:
        return {
            "command_name": command_name,
            "baseline_metric": packet.get("baseline_metric"),
            "beneficial_primitives": packet.get("beneficial_primitives", []),
            "failure_priorities": failure_priorities,
            "suggestion_count": len(suggestions[:limit]),
            "reasons": [str(item) for item in packet.get("reasons", [])][:limit],
            "suggestions": _serialize_trials(suggestions, limit=limit),
            "source": "chip",
            "chip_name": packet.get("chip_name"),
        }
    frontier_packet = frontier_suggest(config_path, command_name, rows=rows, limit=limit)
    if int(frontier_packet.get("suggestion_count", 0)) > 0:
        return frontier_packet
    return {
        "command_name": command_name,
        "baseline_metric": packet.get("baseline_metric"),
        "beneficial_primitives": packet.get("beneficial_primitives", []),
        "failure_priorities": failure_priorities,
        "suggestion_count": 0,
        "reasons": [*packet.get("reasons", []), *frontier_packet.get("reasons", [])][:limit],
        "suggestions": [],
        "source": "chip",
        "chip_name": packet.get("chip_name"),
    }


def _core_suggestion_packet(config: Any, runtime_root: Path, command_name: str, rows: list[dict[str, Any]], *, limit: int) -> dict[str, Any]:
    baseline_metric = _baseline_metric(rows, command_name, config.eval_goal)
    tested = _tested_signatures(rows, command_name)
    existing = {_signature(trial.mutations) for trial in config.candidate_trials}
    primitives = _best_single_primitives(rows, command_name, config.eval_goal, baseline_metric)
    numeric_specs = _numeric_specs(config)
    anchors = _beneficial_numeric_anchors(rows, command_name, config.eval_goal, baseline_metric, numeric_specs)
    failure_priorities = surprise_status(runtime_root, limit=5)

    suggestions: list[CandidateTrial] = []
    reasons: list[str] = []
    failure_trials, failure_reasons, failure_focus = _failure_guided_suggestions(
        runtime_root,
        command_name,
        tested=tested,
        existing=existing,
        primitives=primitives,
        limit=limit,
    )
    suggestions.extend(failure_trials)
    reasons.extend(failure_reasons)

    if len(suggestions) < limit and len(primitives) > 1:
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

    if len(suggestions) < limit:
        neighborhood_trials, neighborhood_reasons = _neighborhood_suggestions(
            anchors,
            numeric_specs,
            tested=tested,
            existing=existing,
            limit=max(limit - len(suggestions), 0),
        )
        suggestions.extend(neighborhood_trials)
        reasons.extend(neighborhood_reasons)

    for name, item in sorted(primitives.items()):
        if len(suggestions) >= limit:
            break
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

    return {
        "command_name": command_name,
        "baseline_metric": baseline_metric,
        "beneficial_primitives": list(primitives.values()),
        "failure_focus": failure_focus,
        "failure_priorities": failure_priorities,
        "suggestion_count": len(suggestions[:limit]),
        "reasons": reasons[: len(suggestions[:limit])],
        "suggestions": _serialize_trials(suggestions, limit=limit),
        "source": "core",
    }


def suggest_trials(config_path: Path, command_name: str, *, limit: int = 3) -> dict[str, Any]:
    config = load_config(config_path)
    runtime_root = resolve_runtime_root(config_path)
    rows = read_jsonl(ledger_path(runtime_root))
    if chip_has_hook(config_path, "suggest", config):
        return _chip_suggestion_packet(config_path, config, command_name, rows, limit=limit)
    return _core_suggestion_packet(config, runtime_root, command_name, rows, limit=limit)


def append_suggestions(config_path: Path, suggestions: list[dict[str, Any]]) -> dict[str, Any]:
    config = load_config(config_path)
    existing = {_signature(trial.mutations) for trial in config.candidate_trials}
    appended: list[dict[str, Any]] = []
    for item in suggestions:
        trial = _trial_from_packet(item)
        sig = _signature(trial.mutations)
        if sig in existing:
            continue
        config.candidate_trials.append(trial)
        existing.add(sig)
        appended.append(asdict(trial))
    if appended:
        save_config(config_path, config)
    return {"appended_count": len(appended), "appended": appended, "config_path": str(config_path)}


def _run_pending_trials(
    config_path: Path,
    command_name: str,
    *,
    pending: list[CandidateTrial],
    max_iterations: int,
    discard_limit: int,
    dry_run: bool,
) -> tuple[list[dict[str, Any]], bool]:
    consecutive_discards = 0
    results: list[dict[str, Any]] = []
    for trial in pending[:max_iterations]:
        record = run_once(config_path, command_name, trial=trial, dry_run=dry_run)
        results.append(record)
        if record["verdict"] == "improved":
            consecutive_discards = 0
        elif record["verdict"] == "regressed":
            consecutive_discards += 1
        if consecutive_discards >= discard_limit:
            return results, True
    return results, False


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
    queued_packet: dict[str, Any] | None = None
    for round_index in range(1, rounds + 1):
        config = load_config(config_path)
        runtime_root = resolve_runtime_root(config_path)
        rows = read_jsonl(ledger_path(runtime_root))
        tested = _tested_signatures(rows, command_name)
        pending = _pending_trials(config, tested)

        if not pending:
            suggestion_packet = queued_packet or suggest_trials(config_path, command_name, limit=suggest_limit)
            queued_packet = None
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
            pending = _pending_trials(config, tested)
        else:
            suggestion_packet = {"suggestion_count": 0, "suggestions": [], "reasons": []}
            append_packet = {"appended_count": 0, "appended": []}

        results, stopped_for_discard_limit = _run_pending_trials(
            config_path,
            command_name,
            pending=pending,
            max_iterations=config.guardrails.max_loop_iterations,
            discard_limit=config.guardrails.consecutive_discard_limit,
            dry_run=dry_run,
        )

        next_suggestions = suggest_trials(config_path, command_name, limit=suggest_limit)
        queued_packet = next_suggestions if next_suggestions.get("suggestion_count", 0) else None
        history.append(
            {
                "round": round_index,
                "run_count": len(results),
                "results": results,
                "suggestions": suggestion_packet,
                "appended": append_packet,
                "next_suggestions": next_suggestions,
                "stopped_for_discard_limit": stopped_for_discard_limit,
            }
        )
        if len(results) == 0 and queued_packet is None:
            break

    return {
        "command_name": command_name,
        "project_name": load_config(config_path).project_name,
        "round_count": len(history),
        "history": history,
    }


def run_continuous_autoloop(
    config_path: Path,
    command_name: str,
    *,
    rounds: int = 2,
    suggest_limit: int = 2,
    pause_seconds: int = 60,
    dry_run: bool = False,
    apply_suggestions: bool = True,
) -> dict[str, Any]:
    passes: list[dict[str, Any]] = []
    try:
        while True:
            packet = run_autoloop(
                config_path,
                command_name,
                rounds=rounds,
                suggest_limit=suggest_limit,
                dry_run=dry_run,
                apply_suggestions=apply_suggestions,
            )
            passes.append({
                "pass": len(passes) + 1,
                "round_count": packet["round_count"],
                "run_count": sum(int(item.get("run_count", 0)) for item in packet["history"]),
                "appended_count": sum(int(item["appended"]["appended_count"]) for item in packet["history"]),
                "stopped": packet["history"][-1].get("stopped") if packet["history"] else None,
            })
            time.sleep(max(pause_seconds, 1))
    except KeyboardInterrupt:
        return {"command_name": command_name, "project_name": load_config(config_path).project_name, "continuous": True, "pass_count": len(passes), "passes": passes, "interrupted": True}
