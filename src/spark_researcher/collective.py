from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
import argparse
import re
from typing import Any

from .config import ProjectConfig
from .paths import capsule_root, ledger_path
from .paths import spark_swarm_collective_payload_path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "generalist"


def _repo_key(value: str) -> str:
    repo_name = value.strip().split("/")[-1]
    if repo_name.startswith("domain-chip-"):
        repo_name = repo_name[len("domain-chip-") :]
    return _slug(repo_name)
def _parse_frontmatter(raw: str) -> dict[str, Any]:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    payload: dict[str, str] = {}
    current_key: str | None = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("  - ") and current_key is not None:
            payload.setdefault(current_key, [])
            payload[current_key].append(line[4:].strip())
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        parsed = value.strip()
        if parsed == "":
            payload[current_key] = []
            continue
        if parsed in {"true", "false"}:
            payload[current_key] = parsed == "true"
            continue
        try:
            payload[current_key] = json.loads(parsed)
        except json.JSONDecodeError:
            payload[current_key] = parsed
    return payload

def _parse_legacy_manifest_fields(raw: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    current_section: str | None = None
    for raw_line in raw.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if not raw_line.startswith(" "):
            current_section = line[:-1].strip() if line.endswith(":") else None
            continue
        if not current_section or ":" not in line:
            continue
        key, value = line.strip().split(":", 1)
        payload[f"{current_section}.{key.strip()}"] = value.strip()
    return payload


def _manifest_metadata(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "AUTORESEARCH.md"
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    metadata = _parse_frontmatter(raw)
    legacy_fields = _parse_legacy_manifest_fields(raw)
    metadata.update(legacy_fields)
    return metadata


def latest_metric_run(runtime_root: Path) -> dict[str, Any] | None:
    rows = read_jsonl(ledger_path(runtime_root))
    metric_rows = [row for row in rows if isinstance(row.get("metric_value"), (int, float))]
    return metric_rows[-1] if metric_rows else None


def _runtime_source(record: dict[str, Any], *, agent_id: str, run_id: str) -> dict[str, Any]:
    chip_result = record.get("chip_result", {})
    comparison_class = ""
    if isinstance(chip_result, dict):
        comparison_class = str(chip_result.get("comparison_class", "")).strip()

    loop_kind = "benchmark" if comparison_class == "benchmark_grounded" else "generalist"
    return {
        "kind": "spark_researcher",
        "version": "0.1.0",
        "loopKind": loop_kind,
        "sourceInstanceId": agent_id,
        "sourceRunId": f"spark-researcher:{run_id}",
        "chipKey": None,
        "chipLabel": None,
    }


def _agent_identity(repo_root: Path) -> tuple[str, str]:
    fields = _manifest_metadata(repo_root)
    agent_label = (
        str(fields.get("agent.name") or "").strip()
        or str(fields.get("name") or "").strip()
        or os.environ.get("SPARK_SWARM_AGENT_NAME")
        or repo_root.name
    )
    repo_value = str(fields.get("repo") or "").strip()
    agent_key = _repo_key(repo_value) if repo_value else _slug(agent_label)
    return f"agent:{agent_key}", agent_label


def _specialization_descriptor(repo_root: Path) -> dict[str, Any]:
    fields = _manifest_metadata(repo_root)
    repo_label = (
        str(fields.get("name") or "").strip()
        or str(fields.get("repo.name") or "").strip()
        or str(fields.get("repo") or "").strip().split("/")[-1]
        or repo_root.name
    )
    repo_value = str(fields.get("repo") or "").strip()
    key = _repo_key(repo_value) if repo_value else _slug(repo_label)
    return {
        "id": f"specialization:{key}",
        "key": key,
        "label": repo_label,
        "memoryPolicy": "selective",
    }


def _evolution_path_id(specialization_key: str, command_name: str) -> str:
    return f"evolution-path:{_slug(specialization_key)}:{_slug(command_name)}"


def _artifact_refs(record: dict[str, Any]) -> list[dict[str, Any]]:
    run_id = str(record.get("run_id") or "latest")
    refs = []
    for kind, label, path_key in (
        ("run_trace", "Run directory", "run_dir"),
        ("run_trace", "Run log", "log_path"),
        ("run_trace", "Trace file", "trace_path"),
    ):
        path_value = record.get(path_key)
        if not path_value:
            continue
        refs.append(
            {
                "id": f"{run_id}:{path_key}",
                "kind": kind,
                "label": label,
                "path": str(path_value),
                "url": None,
                "hash": None,
            }
        )
    return refs


def _benchmark_metrics(record: dict[str, Any]) -> dict[str, Any] | None:
    chip_result = record.get("chip_result", {})
    if not isinstance(chip_result, dict):
        return None
    if str(chip_result.get("comparison_class", "")).strip() != "benchmark_grounded":
        return None

    metrics: dict[str, Any] = {}
    scalar_fields = (
        ("benchmark_profile", "benchmarkProfile"),
        ("benchmark_profile_label", "benchmarkProfileLabel"),
        ("baseline_id", "baselineId"),
        ("benchmark_pass_rate", "benchmarkPassRate"),
        ("outcome_score", "outcomeScore"),
        ("constraint_score", "constraintScore"),
        ("track_count", "trackCount"),
        ("evidence_count", "evidenceCount"),
        ("total_tool_calls_mean", "totalToolCallsMean"),
    )
    for source_key, target_key in scalar_fields:
        value = chip_result.get(source_key)
        if value is None:
            continue
        metrics[target_key] = value

    track_summaries = chip_result.get("track_summaries", [])
    if isinstance(track_summaries, list) and track_summaries:
        metrics["trackSummaries"] = track_summaries
        strongest = max(
            (item for item in track_summaries if isinstance(item, dict)),
            key=lambda item: float(item.get("scenario_score_mean", 0.0) or 0.0),
            default=None,
        )
        weakest = min(
            (item for item in track_summaries if isinstance(item, dict)),
            key=lambda item: float(item.get("scenario_score_mean", 0.0) or 0.0),
            default=None,
        )
        if isinstance(strongest, dict):
            metrics["strongestTrack"] = strongest
        if isinstance(weakest, dict):
            metrics["weakestTrack"] = weakest

    suite_report = chip_result.get("suite_report")
    if isinstance(suite_report, dict):
        metrics["benchmarkVersion"] = suite_report.get("benchmark_version")
        metrics["scenarioPackVersion"] = suite_report.get("scenario_pack_version")
        metrics["benchmarkSplit"] = suite_report.get("split")

    return metrics or None


def _trading_benchmark_metrics(record: dict[str, Any]) -> dict[str, Any] | None:
    chip_result = record.get("chip_result", {})
    if not isinstance(chip_result, dict):
        return None
    if str(chip_result.get("data_mode", "")).strip() != "contract_window_backtest":
        return None

    metrics: dict[str, Any] = {
        "benchmarkProfile": "contract_window_backtest",
        "requestedAssetUniverse": chip_result.get("requested_asset_universe"),
        "requestedTimeframe": chip_result.get("requested_timeframe"),
        "evaluatedAsset": chip_result.get("evaluated_asset"),
        "evaluatedTimeframe": chip_result.get("evaluated_timeframe"),
        "fallbackReason": chip_result.get("data_fallback_reason"),
        "contractCount": chip_result.get("contract_count"),
        "coveredContractCount": chip_result.get("covered_contract_count"),
        "tradeCount": chip_result.get("trade_count"),
        "minimumTradeCount": chip_result.get("minimum_trade_count"),
        "tradeCountGatePass": chip_result.get("trade_count_gate_pass"),
        "holdoutProfitability": chip_result.get("holdout_profitability_score"),
        "walkForwardConsistency": chip_result.get("walk_forward_consistency"),
        "stressResilience": chip_result.get("stress_resilience"),
    }
    record_metrics = record.get("metrics", {})
    if isinstance(record_metrics, dict):
        metrics["paperTradeReadiness"] = record_metrics.get("paper_trade_readiness")
        metrics["maxDrawdown"] = record_metrics.get("max_drawdown")
        metrics["winRate"] = record_metrics.get("win_rate")
        metrics["sharpeRatio"] = record_metrics.get("sharpe_ratio")
    return {key: value for key, value in metrics.items() if value is not None} or None


def _benchmark_outcome_context(record: dict[str, Any], benchmark_metrics: dict[str, Any] | None) -> dict[str, Any] | None:
    if not benchmark_metrics:
        return None
    chip_result = record.get("chip_result", {})
    if not isinstance(chip_result, dict):
        return None
    if str(chip_result.get("comparison_class", "")).strip() != "benchmark_grounded":
        return None

    component_scores: dict[str, float] = {}
    for item in benchmark_metrics.get("trackSummaries", []):
        if not isinstance(item, dict):
            continue
        track = str(item.get("track") or "").strip()
        score = item.get("scenario_score_mean")
        if not track or not isinstance(score, (int, float)):
            continue
        component_scores[track] = float(score)

    strongest_track = benchmark_metrics.get("strongestTrack")
    weakest_track = benchmark_metrics.get("weakestTrack")
    scenario_pack = benchmark_metrics.get("scenarioPackVersion")
    if scenario_pack is None:
        suite_report = chip_result.get("suite_report")
        if isinstance(suite_report, dict):
            scenario_pack = suite_report.get("scenario_pack_version")

    scenario_id = chip_result.get("track_focus") or chip_result.get("factor_id") or record.get("candidate_id")

    return {
        "benchmark": {
            "benchmarkName": "TheStartupBench",
            "scenarioId": scenario_id,
            "scenarioPack": scenario_pack,
            "baselineId": benchmark_metrics.get("baselineId"),
            "strongestComponent": strongest_track.get("track") if isinstance(strongest_track, dict) else None,
            "weakestComponent": weakest_track.get("track") if isinstance(weakest_track, dict) else None,
            "componentScores": component_scores,
            "planner": None,
        }
    }


def _trading_outcome_context(record: dict[str, Any], benchmark_metrics: dict[str, Any] | None) -> dict[str, Any] | None:
    chip_result = record.get("chip_result", {})
    if not isinstance(chip_result, dict):
        return None
    if str(chip_result.get("data_mode", "")).strip() != "contract_window_backtest":
        return None

    component_scores: dict[str, float] = {}
    metric_sources = {
        "holdout": chip_result.get("holdout_profitability_score"),
        "walk_forward": chip_result.get("walk_forward_consistency"),
        "stress": chip_result.get("stress_resilience"),
    }
    record_metrics = record.get("metrics", {})
    if isinstance(record_metrics, dict):
        metric_sources["readiness"] = record_metrics.get("paper_trade_readiness")
    for key, value in metric_sources.items():
        if isinstance(value, (int, float)):
            component_scores[key] = float(value)
    strongest = max(component_scores, key=component_scores.get) if component_scores else None
    weakest = min(component_scores, key=component_scores.get) if component_scores else None

    return {
        "benchmark": {
            "benchmarkName": "TradingBacktest",
            "scenarioId": record.get("candidate_id") or chip_result.get("evaluated_asset"),
            "scenarioPack": chip_result.get("data_mode"),
            "baselineId": "global-baseline" if record.get("baseline_value") is not None else None,
            "strongestComponent": strongest,
            "weakestComponent": weakest,
            "componentScores": component_scores,
            "planner": None,
        },
        "trading": {
            "requestedAssetUniverse": chip_result.get("requested_asset_universe"),
            "requestedTimeframe": chip_result.get("requested_timeframe"),
            "evaluatedAsset": chip_result.get("evaluated_asset"),
            "evaluatedTimeframe": chip_result.get("evaluated_timeframe"),
            "fallbackReason": chip_result.get("data_fallback_reason"),
            "tradeCount": chip_result.get("trade_count"),
            "minimumTradeCount": chip_result.get("minimum_trade_count"),
            "tradeCountGatePass": chip_result.get("trade_count_gate_pass"),
        },
    }


def _scorecard_component(key: str, label: str, value: Any, *, goal: str = "higher") -> dict[str, Any] | None:
    if not isinstance(value, (int, float)):
        return None
    normalized = float(value)
    if normalized < 0.0 or normalized > 1.0:
        return None
    return {
        "key": key,
        "label": label,
        "value": normalized,
        "goal": goal,
    }


def _scorecard_detail(key: str, label: str, value: Any) -> dict[str, Any] | None:
    if value in {None, ""}:
        return None
    return {
        "key": key,
        "label": label,
        "value": str(value),
    }


def _outcome_scorecard(record: dict[str, Any], benchmark_metrics: dict[str, Any] | None) -> dict[str, Any] | None:
    metric_name = str(record.get("metric_name") or "").strip()
    metric_value = record.get("metric_value")
    chip_result = record.get("chip_result", {})
    record_metrics = record.get("metrics", {})
    headline_value = float(metric_value) if isinstance(metric_value, (int, float)) else None
    headline_label = metric_name.replace("_", " ") if metric_name else None
    headline_goal = "higher"
    model_label = "Spark normalized score"

    if isinstance(chip_result, dict) and str(chip_result.get("comparison_class", "")).strip() == "benchmark_grounded":
        benchmark_headline = benchmark_metrics.get("outcomeScore") if isinstance(benchmark_metrics, dict) else None
        if isinstance(benchmark_headline, (int, float)):
            headline_value = float(benchmark_headline)
            headline_label = "Outcome score"
        model_label = "Benchmark weighted score"

    if headline_value is None or headline_value < 0.0 or headline_value > 1.0:
        return None

    scorecard: dict[str, Any] = {
        "headlineLabel": headline_label,
        "headlineValue": headline_value,
        "headlineGoal": headline_goal,
        "modelLabel": model_label,
        "components": [],
        "details": [],
    }

    components: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []

    if isinstance(chip_result, dict) and str(chip_result.get("comparison_class", "")).strip() == "benchmark_grounded":
        if benchmark_metrics:
            for item in (
                _scorecard_component("outcome_score", "Outcome score", benchmark_metrics.get("outcomeScore")),
                _scorecard_component("constraint_score", "Constraint score", benchmark_metrics.get("constraintScore")),
                _scorecard_component("benchmark_pass_rate", "Benchmark pass rate", benchmark_metrics.get("benchmarkPassRate")),
            ):
                if item:
                    components.append(item)
        for item in (
            _scorecard_detail("benchmark_name", "Benchmark", "TheStartupBench"),
            _scorecard_detail("scenario_pack", "Scenario pack", benchmark_metrics.get("scenarioPackVersion") if benchmark_metrics else None),
            _scorecard_detail("baseline_id", "Baseline", benchmark_metrics.get("baselineId") if benchmark_metrics else None),
        ):
            if item:
                details.append(item)
    elif isinstance(chip_result, dict) and str(chip_result.get("data_mode", "")).strip() == "contract_window_backtest":
        scorecard["modelLabel"] = "Trading backtest quality"
        if isinstance(record_metrics, dict):
            for item in (
                _scorecard_component("profitability_score", "Profitability score", metric_value),
                _scorecard_component("win_rate", "Win rate", record_metrics.get("win_rate")),
                _scorecard_component("paper_trade_readiness", "Paper trade readiness", record_metrics.get("paper_trade_readiness")),
                _scorecard_component("holdout_profitability", "Holdout profitability", chip_result.get("holdout_profitability_score")),
                _scorecard_component("walk_forward_consistency", "Walk-forward consistency", chip_result.get("walk_forward_consistency")),
                _scorecard_component("stress_resilience", "Stress resilience", chip_result.get("stress_resilience")),
                _scorecard_component("max_drawdown", "Max drawdown", record_metrics.get("max_drawdown"), goal="lower"),
            ):
                if item:
                    components.append(item)
        for item in (
            _scorecard_detail("trade_count", "Trade count", chip_result.get("trade_count")),
            _scorecard_detail("minimum_trade_count", "Minimum trade count", chip_result.get("minimum_trade_count")),
            _scorecard_detail("evaluated_asset", "Evaluated asset", chip_result.get("evaluated_asset")),
            _scorecard_detail("evaluated_timeframe", "Evaluated timeframe", chip_result.get("evaluated_timeframe")),
            _scorecard_detail("fallback_reason", "Fallback", chip_result.get("data_fallback_reason")),
        ):
            if item:
                details.append(item)

    if not components and not details:
        return None
    scorecard["components"] = components
    scorecard["details"] = details
    return scorecard


def _spark_swarm_bridge_state_path() -> Path:
    return Path.home() / ".spark-swarm" / "bridge-state.json"


def _load_spark_swarm_bridge_state() -> dict[str, Any]:
    path = _spark_swarm_bridge_state_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolved_spark_swarm_workspace_id() -> str | None:
    explicit = os.environ.get("SPARK_SWARM_WORKSPACE_ID", "").strip()
    if explicit:
        return explicit
    bridge_state = _load_spark_swarm_bridge_state()
    workspace_id = str(bridge_state.get("workspace_id") or bridge_state.get("workspaceId") or "").strip()
    return workspace_id or None


def build_spark_swarm_collective_payload(
    repo_root: Path,
    runtime_root: Path,
    config: ProjectConfig,
    record: dict[str, Any],
) -> dict[str, Any]:
    emitted_at = str(record.get("created_at") or datetime.now(UTC).replace(microsecond=0).isoformat())
    run_id = str(record.get("run_id") or "latest")
    command_name = str(record.get("command_name") or "run")
    metric_name = str(record.get("metric_name") or config.eval_metric)
    metric_value = record.get("metric_value")
    status = str(record.get("status") or "failed")
    verdict = str(record.get("verdict") or "unknown")
    runtime_state = "running" if status == "ok" else "blocked"
    evidence_lane = "live_evidence"
    chip_result = record.get("chip_result", {})
    if isinstance(chip_result, dict) and str(chip_result.get("comparison_class", "")).strip() == "benchmark_grounded":
        evidence_lane = "benchmark_evidence"
    benchmark_metrics = _benchmark_metrics(record) or _trading_benchmark_metrics(record)
    benchmark_outcome_context = _benchmark_outcome_context(record, benchmark_metrics) or _trading_outcome_context(record, benchmark_metrics)
    outcome_scorecard = _outcome_scorecard(record, benchmark_metrics)

    workspace_id = _resolved_spark_swarm_workspace_id() or ""
    agent_id, agent_label = _agent_identity(repo_root)
    specialization = _specialization_descriptor(repo_root)
    specialization_id = str(specialization["id"])
    repo_id = f"repo:{_slug(str(specialization['key']))}"
    outcome_id = f"outcome:{run_id}"
    insight_like = status == "ok" and verdict not in {"regressed", "unknown"}
    improvement_like = status == "ok" and verdict in {"improved", "near_best"}
    contradiction_like = status != "ok" or verdict in {"regressed", "unknown"}

    insight_id = f"insight:{run_id}"
    mastery_id = f"mastery:{run_id}"
    contradiction_id = f"contradiction:{run_id}"
    path_id = _evolution_path_id(str(specialization["key"]), command_name)
    summary = f"{command_name} {verdict} on {metric_name}={metric_value}"

    insights: list[dict[str, Any]] = []
    masteries: list[dict[str, Any]] = []
    contradictions: list[dict[str, Any]] = []
    evidence = [
        {
            "lane": evidence_lane,
            "support": "strong" if evidence_lane == "benchmark_evidence" and improvement_like else "moderate" if improvement_like else "weak",
            "summary": summary,
            "artifactRefs": _artifact_refs(record),
            **({"benchmarkMetrics": benchmark_metrics} if benchmark_metrics else {}),
        }
    ]

    if insight_like:
        insights.append(
            {
                "id": insight_id,
                "specializationId": specialization_id,
                "summary": summary,
                "mechanism": str(record.get("candidate_summary") or "").strip() or None,
                "boundary": None,
                "contradiction": None,
                "confidence": 0.8 if evidence_lane == "benchmark_evidence" else 0.65,
                "evidenceLane": evidence_lane,
                "sourceRefs": [str(record.get("run_dir") or "")] if record.get("run_dir") else [],
                "status": (
                    "benchmark_supported"
                    if evidence_lane == "benchmark_evidence"
                    else "live_supported" if verdict in {"improved", "near_best"} else "captured"
                ),
                **({"benchmarkMetrics": benchmark_metrics} if benchmark_metrics else {}),
                "createdAt": emitted_at,
                "updatedAt": emitted_at,
            }
        )
        if evidence_lane == "benchmark_evidence":
            masteries.append(
                {
                    "id": mastery_id,
                    "derivedFromInsightId": insight_id,
                    "specializationScope": str(specialization["key"]),
                    "shareScope": "selective",
                    "status": "provisional_mastery",
                    "supportCount": 1,
                    "contradictionCount": 0,
                    "benchmarkStrength": 0.9,
                    "liveStrength": None,
                    "summary": f"{command_name} benchmark-backed mastery candidate",
                    **({"benchmarkMetrics": benchmark_metrics} if benchmark_metrics else {}),
                    "createdAt": emitted_at,
                    "updatedAt": emitted_at,
                }
            )

    if contradiction_like:
        contradictions.append(
            {
                "id": contradiction_id,
                "targetType": "insight" if insights else "upgrade",
                "targetId": insight_id if insights else path_id,
                "severity": "critical" if status != "ok" else "warn",
                "summary": summary,
                "sourceRef": str(record.get("log_path") or "") or None,
                "createdAt": emitted_at,
            }
        )

    outcome_verdict = "contradicted" if status != "ok" else verdict if verdict in {"improved", "flat", "regressed", "contradicted"} else "flat"

    return {
        "workspaceId": workspace_id,
        "agentId": agent_id,
        "runtimeSource": _runtime_source(record, agent_id=agent_id, run_id=run_id),
        "specialization": specialization,
        "runtimePulse": {
            "agentId": agent_id,
            "repoId": repo_id,
            "runtimeState": runtime_state,
            "passNumber": len(read_jsonl(ledger_path(runtime_root))),
            "stageKey": command_name,
            "stageLabel": command_name.replace("-", " ").title(),
            "blocker": str(record.get("stderr_excerpt") or "").strip() or None,
            "recommendation": "Review the newest insight and outcome." if improvement_like else "Review the contradiction and latest outcome.",
            "lastUpdatedAt": emitted_at,
        },
        "intelligencePulse": {
            "specializationId": specialization_id,
            "specializationLabel": agent_label,
            "activeEvolutionPathId": path_id,
            "activeEvolutionPathSummary": f"Improve {command_name} on {metric_name}",
            "newestInsightId": insight_id if insights else None,
            "newestInsightSummary": insights[0]["summary"] if insights else None,
            "strongestMasteryId": masteries[0]["id"] if masteries else None,
            "strongestMasterySummary": masteries[0]["summary"] if masteries else None,
            "pendingContradictionCount": len(contradictions),
            "pendingUpgradeCount": 0,
            "recommendedAbsorbTargetId": insight_id if insights else None,
            "recommendedUpgradeId": None,
            "evidence": evidence,
        },
        "evolutionPaths": [
            {
                "id": path_id,
                "scope": "specialization",
                "specializationId": specialization_id,
                "summary": f"Improve {command_name} on {metric_name}",
                "status": "open",
                "assignedAgentId": agent_id,
                "bestOutcomeId": outcome_id if improvement_like else None,
                "expiresAt": None,
                "createdAt": emitted_at,
                "updatedAt": emitted_at,
            }
        ],
        "insights": insights,
        "masteries": masteries,
        "masteryReviews": [],
        "contradictions": contradictions,
        "upgrades": [],
        "upgradeDeliveries": [],
        "outcomes": [
            {
                "id": outcome_id,
                "targetType": "evolution_path",
                "targetId": path_id,
                "evidenceLane": evidence_lane,
                "verdict": outcome_verdict,
                "summary": summary,
                "metricName": metric_name,
                "metricValue": float(metric_value) if isinstance(metric_value, (int, float)) else None,
                **({"context": {**(benchmark_outcome_context or {}), **({"scorecard": outcome_scorecard} if outcome_scorecard else {})}} if benchmark_outcome_context or outcome_scorecard else {}),
                **({"benchmarkMetrics": benchmark_metrics} if benchmark_metrics else {}),
                "createdAt": emitted_at,
            }
        ],
        "artifactRefs": _artifact_refs(record),
        "emittedAt": emitted_at,
    }


def write_spark_swarm_collective_payload(
    repo_root: Path,
    runtime_root: Path,
    config: ProjectConfig,
    record: dict[str, Any],
) -> dict[str, Any]:
    payload = build_spark_swarm_collective_payload(repo_root, runtime_root, config, record)
    path = spark_swarm_collective_payload_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "payload_path": str(path),
        "workspace_id": payload.get("workspaceId") or None,
        "agent_id": payload.get("agentId"),
        "insight_count": len(payload.get("insights", [])),
        "mastery_count": len(payload.get("masteries", [])),
        "contradiction_count": len(payload.get("contradictions", [])),
        "outcome_count": len(payload.get("outcomes", [])),
    }


def write_spark_swarm_collective_payload_from_latest(
    repo_root: Path,
    runtime_root: Path,
    config: ProjectConfig,
) -> dict[str, Any]:
    record = latest_metric_run(runtime_root)
    if record is None:
        raise RuntimeError("No metric runs available to export for Spark Swarm.")
    return write_spark_swarm_collective_payload(repo_root, runtime_root, config, record)


def publish_latest(repo_root: Path, runtime_root: Path) -> dict[str, Any]:
    run = latest_metric_run(runtime_root)
    if run is None:
        raise RuntimeError("No metric runs available to publish.")
    capsule_id = f"{now_stamp()}-{run.get('run_id')}"
    root = capsule_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    verdict = _normalized_collective_verdict(
        str(run.get("verdict") or ""),
        status=str(run.get("status") or ""),
    )
    payload = {
        "capsule_id": capsule_id,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "title": f"{run.get('project_name')} {run.get('candidate_id') or run.get('run_id')}",
        "summary": f"{verdict} on {run.get('metric_name')}={run.get('metric_value')}",
        "metric_name": run.get("metric_name"),
        "metric_value": run.get("metric_value"),
        "baseline_value": run.get("baseline_value"),
        "verdict": verdict,
        "run_id": run.get("run_id"),
        "artifact_paths": [run.get("run_dir"), run.get("log_path")],
    }
    markdown = "\n".join(
        [
            "---",
            *(f"{key}: {json.dumps(value) if isinstance(value, (dict, list)) else value}" for key, value in payload.items()),
            "export_kind: latest",
            "---",
            "",
            f"# {payload['title']}",
            "",
            payload["summary"],
            "",
            f"- metric: `{payload['metric_name']}` = `{payload['metric_value']}`",
            f"- baseline: `{payload['baseline_value']}`",
            f"- verdict: `{payload['verdict']}`",
            f"- run_id: `{payload['run_id']}`",
        ]
    )
    md_path = root / f"{capsule_id}.md"
    json_path = root / f"{capsule_id}.manifest.json"
    md_path.write_text(markdown + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"capsule_id": capsule_id, "markdown_path": str(md_path), "manifest_path": str(json_path)}


def _payload_run_id(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    for outcome in payload.get("outcomes", []):
        if not isinstance(outcome, dict):
            continue
        outcome_id = str(outcome.get("id") or "")
        if outcome_id.startswith("outcome:"):
            return outcome_id.split(":", 1)[1]
    return None


def _payload_workspace_id(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    workspace_id = str(payload.get("workspaceId") or "").strip()
    return workspace_id or None


def _payload_path_diagnostics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "reason": "missing_payload"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "reason": "invalid_json"}
    specialization = payload.get("specialization", {})
    if not isinstance(specialization, dict):
        return {"ok": False, "reason": "missing_specialization"}
    specialization_key = str(specialization.get("key") or "").strip()
    if not specialization_key:
        return {"ok": False, "reason": "missing_specialization_key"}

    evolution_paths = payload.get("evolutionPaths", [])
    outcomes = payload.get("outcomes", [])
    if not isinstance(evolution_paths, list) or not evolution_paths:
        return {"ok": False, "reason": "missing_evolution_paths"}
    if not isinstance(outcomes, list) or not outcomes:
        return {"ok": False, "reason": "missing_outcomes"}

    expected_path_ids: set[str] = set()
    for entry in evolution_paths:
        if not isinstance(entry, dict):
            return {"ok": False, "reason": "invalid_evolution_path_entry"}
        path_id = str(entry.get("id") or "").strip()
        summary = str(entry.get("summary") or "").strip()
        command_name = ""
        if summary.startswith("Improve ") and " on " in summary:
            command_name = summary[len("Improve ") :].split(" on ", 1)[0].strip()
        if not path_id or not command_name:
            return {"ok": False, "reason": "unparseable_evolution_path", "path_id": path_id, "summary": summary}
        expected_path_id = _evolution_path_id(specialization_key, command_name)
        if path_id != expected_path_id:
            return {
                "ok": False,
                "reason": "unexpected_evolution_path_id",
                "actual_path_id": path_id,
                "expected_path_id": expected_path_id,
                "command_name": command_name,
                "specialization_key": specialization_key,
            }
        expected_path_ids.add(expected_path_id)

    for outcome in outcomes:
        if not isinstance(outcome, dict):
            return {"ok": False, "reason": "invalid_outcome_entry"}
        if str(outcome.get("targetType") or "").strip() != "evolution_path":
            return {"ok": False, "reason": "unexpected_outcome_target_type", "target_type": outcome.get("targetType")}
        target_id = str(outcome.get("targetId") or "").strip()
        if target_id not in expected_path_ids:
            return {
                "ok": False,
                "reason": "unexpected_outcome_target_id",
                "actual_target_id": target_id,
                "expected_path_ids": sorted(expected_path_ids),
            }
    return {"ok": True, "specialization_key": specialization_key, "path_ids": sorted(expected_path_ids)}


def _payload_paths_match_specialization(path: Path) -> bool:
    diagnostics = _payload_path_diagnostics(path)
    return bool(diagnostics.get("ok"))


def _capsule_run_ids(root: Path) -> set[str]:
    run_ids: set[str] = set()
    if not root.exists():
        return run_ids
    for path in root.glob("*.manifest.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        run_id = str(payload.get("run_id") or "").strip()
        if run_id:
            run_ids.add(run_id)
    return run_ids


def _normalized_collective_verdict(verdict: str | None, *, status: str | None = None) -> str:
    raw = str(verdict or "").strip().lower()
    normalized_status = str(status or "").strip().lower()
    if normalized_status not in {"", "ok"}:
        return "regressed"
    if raw == "improved":
        return "improved"
    if raw in {"flat", "baseline", "near_best"}:
        return "flat"
    return "regressed"


def _collective_readiness_actions(
    *,
    config_path: Path,
    checks: dict[str, bool],
    hosted_checks: dict[str, bool],
    payload_path_diagnostics: dict[str, Any],
) -> list[str]:
    config_arg = str(config_path)
    actions: list[str] = []
    if not checks.get("manifest_present", False):
        actions.append("Add AUTORESEARCH.md with repo identity, run_command, and publish_command.")
    if not checks.get("manifest_has_run_command", False):
        actions.append("Add run_command to AUTORESEARCH.md.")
    if not checks.get("manifest_has_publish_command", False):
        actions.append("Add publish_command to AUTORESEARCH.md.")
    if not checks.get("latest_metric_run_present", False):
        actions.append(f"Run a metric pass first, then rerun `spark-researcher collective ready --config {config_arg}`.")
    if not checks.get("spark_swarm_payload_present", False):
        actions.append(f"Generate a Spark Swarm payload with `spark-researcher collective spark-swarm-payload --config {config_arg}`.")
    if not checks.get("spark_swarm_payload_current", False) and checks.get("latest_metric_run_present", False):
        actions.append(f"Regenerate the Spark Swarm payload for the latest run with `spark-researcher collective spark-swarm-payload --config {config_arg}`.")
    if not checks.get("spark_swarm_payload_paths_match_specialization", False):
        reason = str(payload_path_diagnostics.get('reason') or 'stale_payload')
        actions.append(
            f"Regenerate the Spark Swarm payload because the current one has `{reason}`: `spark-researcher collective spark-swarm-payload --config {config_arg}`."
        )
    if not checks.get("capsule_present_for_latest_run", False) and checks.get("latest_metric_run_present", False):
        actions.append(f"Publish the latest capsule with `spark-researcher collective publish --config {config_arg}`.")
    if not hosted_checks.get("spark_swarm_workspace_binding_present", False):
        actions.append("Bind the repo to a Spark Swarm workspace or set SPARK_SWARM_WORKSPACE_ID before hosted sync.")
    elif not hosted_checks.get("spark_swarm_payload_has_workspace_id", False):
        actions.append(f"Regenerate the Spark Swarm payload after workspace binding so it captures workspaceId: `spark-researcher collective spark-swarm-payload --config {config_arg}`.")
    return actions


def collective_readiness(repo_root: Path, runtime_root: Path) -> dict[str, Any]:
    config_path = repo_root / "spark-researcher.project.json"
    manifest_path = repo_root / "AUTORESEARCH.md"
    manifest = _load_manifest(repo_root)
    manifest_metadata = _manifest_metadata(repo_root)
    latest = latest_metric_run(runtime_root)
    spark_swarm_path = spark_swarm_collective_payload_path(repo_root)
    latest_run_id = str(latest.get("run_id") or "").strip() if latest else None
    payload_run_id = _payload_run_id(spark_swarm_path)
    payload_workspace_id = _payload_workspace_id(spark_swarm_path)
    payload_path_diagnostics = _payload_path_diagnostics(spark_swarm_path)
    bound_workspace_id = _resolved_spark_swarm_workspace_id()
    effective_workspace_id = payload_workspace_id or bound_workspace_id
    capsule_ids = _capsule_run_ids(capsule_root(repo_root))
    has_agent_identity = bool(
        str(manifest_metadata.get("agent.name") or "").strip()
        or str(manifest_metadata.get("name") or "").strip()
        or os.environ.get("SPARK_SWARM_AGENT_NAME", "").strip()
    )
    checks = {
        "manifest_present": manifest_path.exists(),
        "manifest_has_run_command": bool(str(manifest.get("run_command") or "").strip()),
        "manifest_has_publish_command": bool(str(manifest.get("publish_command") or "").strip()),
        "manifest_has_identity": has_agent_identity,
        "latest_metric_run_present": latest is not None,
        "spark_swarm_payload_present": spark_swarm_path.exists(),
        "spark_swarm_payload_current": latest_run_id is not None and payload_run_id == latest_run_id,
        "spark_swarm_payload_paths_match_specialization": bool(payload_path_diagnostics.get("ok")),
        "capsule_present_for_latest_run": latest_run_id is not None and latest_run_id in capsule_ids,
    }
    missing = [name for name, ok in checks.items() if not ok]
    hosted_checks = {
        "spark_swarm_payload_has_workspace_id": payload_workspace_id is not None,
        "spark_swarm_workspace_binding_present": effective_workspace_id is not None,
    }
    hosted_missing = [name for name, ok in hosted_checks.items() if not ok and name != "spark_swarm_payload_has_workspace_id"]
    recommended_actions = _collective_readiness_actions(
        config_path=config_path,
        checks=checks,
        hosted_checks=hosted_checks,
        payload_path_diagnostics=payload_path_diagnostics,
    )
    local_collective = repo_root.parent / "autoresearch-collective"
    return {
        "ready": not missing,
        "hosted_ready": not missing and not hosted_missing,
        "checks": checks,
        "missing": missing,
        "hosted_checks": hosted_checks,
        "hosted_missing": hosted_missing,
        "recommended_actions": recommended_actions,
        "manifest_path": str(manifest_path),
        "latest_metric_run": latest_run_id,
        "spark_swarm_payload_path": str(spark_swarm_path),
        "spark_swarm_workspace_id": effective_workspace_id,
        "spark_swarm_payload_workspace_id": payload_workspace_id,
        "spark_swarm_payload_path_diagnostics": payload_path_diagnostics,
        "spark_swarm_bound_workspace_id": bound_workspace_id,
        "capsule_root": str(capsule_root(repo_root)),
        "local_collective_repo_present": local_collective.exists(),
        "local_collective_repo_path": str(local_collective),
    }


def collective_status(repo_root: Path, runtime_root: Path) -> dict[str, Any]:
    root = capsule_root(repo_root)
    sibling_collective = repo_root.parent / "autoresearch-collective"
    latest = latest_metric_run(runtime_root)
    spark_swarm_path = spark_swarm_collective_payload_path(repo_root)
    return {
        "capsule_root": str(root),
        "capsule_count": len(list(root.glob("*.md"))) if root.exists() else 0,
        "latest_metric_run": latest.get("run_id") if latest else None,
        "collective_repo_present": sibling_collective.exists(),
        "collective_repo_path": str(sibling_collective),
        "spark_swarm_payload_path": str(spark_swarm_path),
        "spark_swarm_payload_present": spark_swarm_path.exists(),
        "readiness": collective_readiness(repo_root, runtime_root),
    }


def _repo_sources_path(collective_root: Path) -> Path:
    return collective_root / "dashboard" / "config" / "repo-sources.local.json"


def _generated_index_path(collective_root: Path) -> Path:
    return collective_root / "dashboard" / "public" / "data" / "collective.generated.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_repo_slug(repo_root: Path) -> str:
    path = repo_root / "AUTORESEARCH.md"
    if not path.exists():
        return repo_root.name
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("repo:"):
            return line.split(":", 1)[1].strip()
    return repo_root.name


def sync_local_collective(repo_root: Path, runtime_root: Path, *, label: str | None = None, rebuild: bool = True) -> dict[str, Any]:
    collective_root = repo_root.parent / "autoresearch-collective"
    if not collective_root.exists():
        raise RuntimeError(f"Collective repo not found: {collective_root}")
    config_path = _repo_sources_path(collective_root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _load_json(config_path) if config_path.exists() else {"sources": []}
    sources = list(payload.get("sources", []))
    repo_path_text = str(repo_root).replace("\\", "/")
    entry = next((item for item in sources if str(item.get("path", "")).replace("\\", "/") == repo_path_text), None)
    if entry is None:
        entry = {"kind": "repo", "label": label or repo_root.name, "path": repo_path_text}
        sources.append(entry)
    else:
        if label:
            entry["label"] = label
    payload["sources"] = sources
    config_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    commands_run = []
    if rebuild:
        for script_name in ("build-collective-data.mjs", "build-graph-data.mjs"):
            command = ["node", f"./scripts/{script_name}"]
            process = subprocess.run(
                command,
                cwd=str(collective_root / "dashboard"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            commands_run.append(
                {
                    "command": command,
                    "returncode": process.returncode,
                    "stdout_excerpt": process.stdout[:400],
                    "stderr_excerpt": process.stderr[:400],
                }
            )
            if process.returncode != 0:
                raise RuntimeError(f"Collective rebuild failed for {script_name}: {process.stderr.strip()}")
    generated = _load_json(_generated_index_path(collective_root))
    repo_slug = _manifest_repo_slug(repo_root)
    repo_connected = any(item.get("repo") == repo_slug for item in generated.get("repoDirectory", []))
    capsule_indexed = any(item.get("repo") == repo_slug for item in generated.get("capsuleLibrary", []))
    return {
        "collective_root": str(collective_root),
        "repo_sources_path": str(config_path),
        "repo_registered": True,
        "repo_connected": repo_connected,
        "capsule_indexed": capsule_indexed,
        "commands_run": commands_run,
        "collective_status": collective_status(repo_root, runtime_root),
    }


def _run_command(
    command: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd),
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()
        message = detail or f"Command failed: {' '.join(command)}"
        raise RuntimeError(message) from error


def _git_output(repo_root: Path, *args: str) -> str:
    result = _run_command(["git", "-C", str(repo_root), *args], cwd=repo_root)
    return result.stdout.strip()


def _repo_slug_from_remote(repo_root: Path) -> str | None:
    try:
        remote = _git_output(repo_root, "remote", "get-url", "origin")
    except RuntimeError:
        return None
    match = re.search(r"github\.com[:/](?P<slug>[^/]+/[^/.]+)(?:\.git)?$", remote)
    return match.group("slug") if match else None


def _default_base_branch(repo_root: Path) -> str:
    try:
        head = _git_output(repo_root, "symbolic-ref", "refs/remotes/origin/HEAD")
        if "/" in head:
            return head.rsplit("/", 1)[-1]
    except RuntimeError:
        pass
    try:
        current = _git_output(repo_root, "branch", "--show-current")
    except RuntimeError:
        current = ""
    if current and not current.startswith("absorb/"):
        return current
    return "main"


def _load_manifest(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "AUTORESEARCH.md"
    return _parse_frontmatter(path.read_text(encoding="utf-8")) if path.exists() else {}


def _load_collective_index(repo_root: Path) -> tuple[Path, dict[str, Any]]:
    collective_root = repo_root.parent / "autoresearch-collective"
    path = collective_root / "dashboard" / "public" / "data" / "collective.generated.json"
    if not path.exists():
        raise FileNotFoundError(f"Could not locate collective.generated.json at {path}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "absorb"


def _ensure_clean_worktree(repo_root: Path) -> None:
    status = _git_output(repo_root, "status", "--porcelain")
    if status.strip():
        raise RuntimeError("Absorb draft PR requires a clean git worktree in the target repo.")


def _gh_auth_ready(repo_root: Path) -> None:
    if _run_command(["gh", "--version"], cwd=repo_root, check=False).returncode != 0:
        raise RuntimeError("`gh` is required for absorb draft PR creation.")
    auth = _run_command(["gh", "auth", "status"], cwd=repo_root, check=False)
    if auth.returncode != 0:
        raise RuntimeError("GitHub CLI is not authenticated. Run `gh auth login` first.")


def _source_repo_entry(collective_data: dict[str, Any], repo: str) -> dict[str, Any] | None:
    return next((entry for entry in collective_data.get("repoDirectory", []) if entry.get("repo") == repo), None)


def _target_platform_summary(manifest: dict[str, Any]) -> str:
    platforms = manifest.get("platforms")
    if isinstance(platforms, list) and platforms:
        return ", ".join(str(item) for item in platforms)
    if isinstance(platforms, str) and platforms:
        return platforms
    return "unknown"


def _source_platform_summary(entry: dict[str, Any] | None) -> str:
    if not entry:
        return "unknown"
    platform = entry.get("platform")
    return str(platform) if platform else "unknown"


def _fit_assessment(target_platform: str, source_platform: str) -> tuple[str, str]:
    if target_platform == "unknown" or source_platform == "unknown":
        return "uncertain", "Platform fit is unknown from current repo metadata."
    if target_platform == source_platform:
        return "compatible", f"Source and target both advertise `{target_platform}`."
    if any(tag in source_platform.lower() for tag in ("cpu", "universal", "lightweight-autoresearch")):
        return "compatible", f"Source advertises broadly compatible platform `{source_platform}`."
    return "uncertain", f"Source `{source_platform}` differs from target `{target_platform}`; review manually."


def _write_absorb_review_files(
    *,
    repo_root: Path,
    stamp: str,
    source_repo: str,
    payload: dict[str, Any],
) -> dict[str, Path]:
    review_root = repo_root / ".autoresearch" / "absorbs" / f"{stamp}-{source_repo.replace('/', '--')}"
    review_root.mkdir(parents=True, exist_ok=True)

    absorbed_path = review_root / "absorbed-insights.json"
    absorbed_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    manifest = _load_manifest(repo_root)
    target_repo = _repo_slug_from_remote(repo_root) or manifest.get("repo") or repo_root.name
    target_platform = _target_platform_summary(manifest)
    source_platform = _source_platform_summary(payload.get("source_repo_entry"))
    fit_status, fit_reason = _fit_assessment(target_platform, source_platform)
    best_delta = next((entry.get("delta") for entry in payload["insights"] if entry.get("delta") is not None), None)

    plan_path = review_root / "ABSORB_PLAN.md"
    review_path = review_root / "AI_REVIEW.md"
    pr_body_path = review_root / "PR_BODY.md"

    plan_path.write_text(
        "\n".join(
            [
                f"# Absorb Plan: {source_repo}",
                "",
                "This PR is a review checkpoint for external Insights before any code transfer.",
                "",
                f"- Source repo: `{source_repo}`",
                f"- Target repo: `{target_repo}`",
                f"- Absorbed insights: `{len(payload['insights'])}`",
                f"- Best observed delta: `{best_delta}`",
                f"- System fit: `{fit_status}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    review_path.write_text(
        "\n".join(
            [
                f"# AI Review: {source_repo}",
                "",
                "- Mode: `review_only`",
                f"- System fit: `{fit_status}`",
                f"- Reason: {fit_reason}",
                "- Security: no external code is applied automatically.",
                "- Human/agent review is still required before any implementation PR.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    pr_body_path.write_text(
        "\n".join(
            [
                f"## Absorb Review: {source_repo}",
                "",
                "This PR is a review-only absorb checkpoint.",
                "",
                f"- Source repo: `{source_repo}`",
                f"- Absorbed insights: `{len(payload['insights'])}`",
                f"- System fit: `{fit_status}`",
                f"- Best observed delta: `{best_delta}`",
                "",
                "Files added:",
                "- `absorbed-insights.json`",
                "- `ABSORB_PLAN.md`",
                "- `AI_REVIEW.md`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "folder": review_root,
        "absorbed_json": absorbed_path,
        "plan": plan_path,
        "review": review_path,
        "pr_body": pr_body_path,
    }


def absorb_merge_policy(repo_root: Path) -> str:
    value = str(_load_manifest(repo_root).get("absorb_merge_policy", "human_review")).strip().lower()
    return value if value in {"human_review", "agent_review", "automerge"} else "human_review"


def absorb(
    repo_root: Path,
    runtime_root: Path,
    *,
    source_repo: str,
    limit: int = 5,
    dry_run: bool = False,
    bundle_only: bool = False,
    merge_policy: str | None = None,
) -> dict[str, Any]:
    index_path, collective_data = _load_collective_index(repo_root)
    capsule_library = collective_data.get("capsuleLibrary", [])
    matching = [entry for entry in capsule_library if entry.get("repo") == source_repo and entry.get("verdict") == "improved"]
    matching.sort(key=lambda entry: str(entry.get("createdAt") or ""), reverse=True)
    absorbed = matching[: max(limit, 0)]
    if not absorbed:
        raise RuntimeError(f"No improved Insights available to absorb from `{source_repo}`.")

    absorb_root = runtime_root / "artifacts" / "collective-absorb" / source_repo.replace("/", "--")
    absorb_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    bundle_path = absorb_root / f"{stamp}-absorb.json"
    resolved_merge_policy = merge_policy or absorb_merge_policy(repo_root)
    payload = {
        "source_repo": source_repo,
        "absorbed_count": len(absorbed),
        "limit": limit,
        "created_at": datetime.now(UTC).isoformat(),
        "collective_index_path": str(index_path),
        "output_path": str(bundle_path),
        "merge_policy": resolved_merge_policy,
        "source_repo_entry": _source_repo_entry(collective_data, source_repo),
        "insights": [
            {
                "insight_id": entry.get("id"),
                "title": entry.get("title"),
                "summary": entry.get("summary"),
                "metric_name": entry.get("metricName"),
                "metric_value": entry.get("metricValue"),
                "baseline_value": entry.get("baselineValue"),
                "delta": entry.get("delta"),
                "verdict": entry.get("verdict"),
                "artifact_url": entry.get("artifactUrl"),
                "source_links": entry.get("sourceLinks", []),
            }
            for entry in absorbed
        ],
    }
    bundle_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if bundle_only:
        return {**payload, "pr_summary": None}

    base_branch = _default_base_branch(repo_root)
    target_repo = _repo_slug_from_remote(repo_root)
    if not target_repo:
        raise RuntimeError("Could not determine target GitHub repo from the origin remote.")
    branch = f"absorb/{stamp}-{_slugify(source_repo.split('/')[-1])}"

    if dry_run:
        return {
            **payload,
            "pr_summary": {
                "mode": "dry_run",
                "base_branch": base_branch,
                "target_repo": target_repo,
                "branch": branch,
                "title": f"absorb: review {source_repo} insights",
                "merge_policy": resolved_merge_policy,
            },
        }

    _ensure_clean_worktree(repo_root)
    _gh_auth_ready(repo_root)
    review_paths = _write_absorb_review_files(repo_root=repo_root, stamp=stamp, source_repo=source_repo, payload=payload)
    rel_paths = [str(path.relative_to(repo_root)) for path in review_paths.values() if path.is_file()]
    title = f"absorb: review {source_repo} insights"

    _run_command(["git", "-C", str(repo_root), "checkout", base_branch], cwd=repo_root)
    _run_command(["git", "-C", str(repo_root), "checkout", "-b", branch], cwd=repo_root)
    _run_command(["git", "-C", str(repo_root), "add", *rel_paths], cwd=repo_root)
    _run_command(["git", "-C", str(repo_root), "commit", "-m", title], cwd=repo_root)
    _run_command(["git", "-C", str(repo_root), "push", "-u", "origin", branch], cwd=repo_root)

    create_args = [
        "gh",
        "pr",
        "create",
        "--repo",
        target_repo,
        "--base",
        base_branch,
        "--head",
        branch,
        "--title",
        title,
        "--body-file",
        str(review_paths["pr_body"]),
    ]
    if resolved_merge_policy == "human_review":
        create_args.append("--draft")
    pr = _run_command(create_args, cwd=repo_root)
    pr_url = pr.stdout.strip() or None

    auto_merge_enabled = False
    auto_merge_error = None
    if resolved_merge_policy == "automerge" and pr_url:
        merge = _run_command(
            ["gh", "pr", "merge", "--repo", target_repo, "--auto", "--squash", pr_url],
            cwd=repo_root,
            check=False,
        )
        auto_merge_enabled = merge.returncode == 0
        if merge.returncode != 0:
            auto_merge_error = (merge.stderr or merge.stdout or "").strip() or "auto merge request failed"

    return {
        **payload,
        "pr_summary": {
            "mode": (
                "draft_pr"
                if resolved_merge_policy == "human_review"
                else "review_pr"
                if resolved_merge_policy == "agent_review"
                else "auto_pr"
            ),
            "base_branch": base_branch,
            "target_repo": target_repo,
            "branch": branch,
            "title": title,
            "pr_url": pr_url,
            "merge_policy": resolved_merge_policy,
            "auto_merge_enabled": auto_merge_enabled,
            "auto_merge_error": auto_merge_error,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Spark Researcher collective bridge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--config", default="spark-researcher.project.json")
    publish_parser.add_argument("--stdout", action="store_true")

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--config", default="spark-researcher.project.json")
    status_parser.add_argument("--stdout", action="store_true")

    ready_parser = subparsers.add_parser("ready")
    ready_parser.add_argument("--config", default="spark-researcher.project.json")
    ready_parser.add_argument("--stdout", action="store_true")

    sync_parser = subparsers.add_parser("sync-local")
    sync_parser.add_argument("--config", default="spark-researcher.project.json")
    sync_parser.add_argument("--label")
    sync_parser.add_argument("--skip-rebuild", action="store_true")
    sync_parser.add_argument("--stdout", action="store_true")

    absorb_parser = subparsers.add_parser("absorb")
    absorb_parser.add_argument("--config", default="spark-researcher.project.json")
    absorb_parser.add_argument("--repo", required=True)
    absorb_parser.add_argument("--limit", type=int, default=5)
    absorb_parser.add_argument("--dry-run", action="store_true")
    absorb_parser.add_argument("--bundle-only", action="store_true")
    absorb_parser.add_argument("--merge-policy", choices=["human_review", "agent_review", "automerge"])
    absorb_parser.add_argument("--stdout", action="store_true")

    args = parser.parse_args(argv)
    config_path = Path(args.config).resolve()
    repo_root = config_path.parent.resolve()
    runtime_root = repo_root

    if args.command == "publish":
        payload = publish_latest(repo_root, runtime_root)
    elif args.command == "status":
        payload = collective_status(repo_root, runtime_root)
    elif args.command == "ready":
        payload = collective_readiness(repo_root, runtime_root)
    elif args.command == "sync-local":
        payload = sync_local_collective(repo_root, runtime_root, label=args.label, rebuild=not args.skip_rebuild)
    elif args.command == "absorb":
        payload = absorb(
            repo_root,
            runtime_root,
            source_repo=args.repo,
            limit=args.limit,
            dry_run=args.dry_run,
            bundle_only=args.bundle_only,
            merge_policy=args.merge_policy,
        )
    else:
        raise ValueError(f"Unknown command: {args.command}")

    if getattr(args, "stdout", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
