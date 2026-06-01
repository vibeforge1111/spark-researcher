from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import spark_researcher.collective as collective_module
from spark_researcher.collective import (
    _parse_frontmatter,
    absorb,
    build_spark_swarm_collective_payload,
    collective_readiness,
    publish_latest,
    write_spark_swarm_collective_payload_from_latest,
)
from spark_researcher.config import load_config
from spark_researcher.paths import ledger_path, resolve_runtime_root, spark_swarm_collective_payload_path
from spark_researcher.runner import run_once


def _write_config(repo_root: Path) -> Path:
    config_path = repo_root / "spark-researcher.project.json"
    payload = {
        "project_name": "toy-project",
        "project_root": ".",
        "eval_metric": "score",
        "eval_goal": "maximize",
        "commands": {
            "train": {
                "args": [sys.executable, "train.py"],
                "cwd": ".",
                "kind": "train-once",
                "log_name": "train.log",
            }
        },
        "metrics": {
            "score": {
                "pattern": r"score=([0-9.]+)",
                "kind": "float",
            }
        },
    }
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return config_path


def _write_manifest(repo_root: Path) -> None:
    (repo_root / "AUTORESEARCH.md").write_text(
        "\n".join(
            [
                "# AUTORESEARCH",
                "",
                "agent:",
                "  name: loopsmith",
                "  model: one-agent-per-workspace",
                "",
                "repo:",
                "  name: starter-lab",
                "  role: attached-specialization",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_frontmatter_manifest(repo_root: Path) -> None:
    (repo_root / "AUTORESEARCH.md").write_text(
        "\n".join(
            [
                "---",
                "schema_version: 1",
                "repo: vibeforge1111/starter-lab",
                "name: Loopsmith Lab",
                "run_command: spark-researcher run --command train",
                "publish_command: spark-researcher collective publish",
                "---",
                "",
                "# AUTORESEARCH",
                "",
                "Frontmatter-backed manifest.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_frontmatter_list_continuation_after_scalar_is_recoverable() -> None:
    payload = _parse_frontmatter(
        "\n".join(
            [
                "---",
                "name: Loopsmith Lab",
                "  - fallback label",
                "---",
            ]
        )
    )

    assert payload["name"] == ["Loopsmith Lab", "fallback label"]


def test_absorb_without_collective_index_fails_without_local_path_leak(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()

    with pytest.raises(RuntimeError, match="No improved Insights available"):
        absorb(repo_root, runtime_root, source_repo="vibeforge1111/example")

    captured = capsys.readouterr()
    assert str(tmp_path) not in captured.out
    assert str(tmp_path) not in captured.err


def test_absorb_cli_without_collective_index_returns_bounded_error(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(source_root / "src")}

    result = subprocess.run(
        [sys.executable, "-m", "spark_researcher.cli", "collective", "absorb", "--repo", "vibeforge1111/example"],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload == {
        "error": "No improved Insights available to absorb from `vibeforge1111/example`.",
        "ok": False,
    }
    assert "Traceback" not in result.stderr
    assert str(tmp_path) not in result.stdout
    assert str(tmp_path) not in result.stderr


def test_collective_read_jsonl_skips_malformed_and_non_object_rows(tmp_path: Path) -> None:
    path = tmp_path / "runs.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"run_id":"one","metric_value":1}',
                "not-json",
                '["not", "an", "object"]',
                '{"run_id":"two","metric_value":2}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = collective_module.read_jsonl(path)

    assert [row["run_id"] for row in rows] == ["one", "two"]


def test_write_spark_swarm_collective_payload_from_latest(tmp_path: Path) -> None:
    repo_root = tmp_path
    _write_manifest(repo_root)
    config_path = _write_config(repo_root)
    runtime_root = repo_root
    row = {
        "run_id": "20260319-train",
        "created_at": "2026-03-19T12:00:00+00:00",
        "command_name": "train",
        "status": "ok",
        "metric_name": "score",
        "metric_value": 1.25,
        "verdict": "improved",
        "candidate_id": "baseline",
        "candidate_summary": "A stronger training lane",
        "chip_result": {
            "comparison_class": "benchmark_grounded",
            "benchmark_profile": "strategy_test",
            "benchmark_profile_label": "Hidden strategy suite",
            "baseline_id": "heuristic_governance_operator",
            "benchmark_pass_rate": 1.0,
            "outcome_score": 0.81,
            "constraint_score": 1.0,
            "track_count": 2,
            "evidence_count": 7,
            "total_tool_calls_mean": 24.5,
            "track_summaries": [
                {"track": "board", "scenario_score_mean": 0.72, "pass_rate_mean": 1.0},
                {"track": "scale", "scenario_score_mean": 0.84, "pass_rate_mean": 1.0},
            ],
            "suite_report": {
                "benchmark_version": "0.2.0-draft",
                "scenario_pack_version": "strategy-test-pack-0.9.0",
                "split": "test",
            },
        },
        "run_dir": str(repo_root / "artifacts" / "runs" / "20260319-train"),
        "log_path": str(repo_root / "artifacts" / "runs" / "20260319-train" / "train.log"),
        "trace_path": str(repo_root / "artifacts" / "traces" / "run.jsonl"),
    }
    ledger = ledger_path(runtime_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    result = write_spark_swarm_collective_payload_from_latest(repo_root, runtime_root, load_config(config_path))

    payload_path = spark_swarm_collective_payload_path(repo_root)
    assert result["payload_path"] == str(payload_path)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["agentId"] == "agent:loopsmith"
    assert payload["specialization"]["key"] == "starter-lab"
    assert payload["runtimeSource"]["sourceInstanceId"] == "agent:loopsmith"
    assert payload["runtimeSource"]["sourceRunId"] == "spark-researcher:20260319-train"
    assert payload["insights"][0]["status"] == "benchmark_supported"
    assert payload["outcomes"][0]["verdict"] == "improved"
    assert payload["outcomes"][0]["evidenceLane"] == "benchmark_evidence"
    assert payload["outcomes"][0]["context"]["benchmark"]["benchmarkName"] == "TheStartupBench"
    assert payload["outcomes"][0]["context"]["benchmark"]["scenarioId"] == "baseline"
    assert payload["outcomes"][0]["context"]["benchmark"]["scenarioPack"] == "strategy-test-pack-0.9.0"
    assert payload["outcomes"][0]["context"]["benchmark"]["baselineId"] == "heuristic_governance_operator"
    assert payload["outcomes"][0]["context"]["benchmark"]["strongestComponent"] == "scale"
    assert payload["outcomes"][0]["context"]["benchmark"]["weakestComponent"] == "board"
    assert payload["outcomes"][0]["context"]["benchmark"]["componentScores"]["scale"] == 0.84
    assert payload["outcomes"][0]["benchmarkMetrics"]["outcomeScore"] == 0.81
    assert payload["outcomes"][0]["benchmarkMetrics"]["constraintScore"] == 1.0
    assert payload["outcomes"][0]["benchmarkMetrics"]["benchmarkPassRate"] == 1.0
    assert payload["outcomes"][0]["benchmarkMetrics"]["strongestTrack"]["track"] == "scale"
    assert payload["masteries"][0]["benchmarkMetrics"]["benchmarkVersion"] == "0.2.0-draft"
    assert payload["outcomes"][0]["context"]["scorecard"]["headlineValue"] == 0.81
    assert payload["outcomes"][0]["context"]["scorecard"]["headlineLabel"] == "Outcome score"
    assert payload["outcomes"][0]["context"]["scorecard"]["components"][0]["key"] == "outcome_score"


def test_frontmatter_manifest_drives_identity(tmp_path: Path) -> None:
    repo_root = tmp_path
    _write_frontmatter_manifest(repo_root)
    config_path = _write_config(repo_root)
    runtime_root = repo_root
    row = {
        "run_id": "20260319-train",
        "created_at": "2026-03-19T12:00:00+00:00",
        "command_name": "train",
        "status": "ok",
        "metric_name": "score",
        "metric_value": 1.25,
        "verdict": "improved",
    }
    ledger = ledger_path(runtime_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    write_spark_swarm_collective_payload_from_latest(repo_root, runtime_root, load_config(config_path))

    payload = json.loads(spark_swarm_collective_payload_path(repo_root).read_text(encoding="utf-8"))
    assert payload["agentId"] == "agent:starter-lab"
    assert payload["specialization"]["key"] == "starter-lab"
    assert payload["specialization"]["label"] == "Loopsmith Lab"


def test_repo_identity_stays_stable_when_manifest_label_changes(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AUTORESEARCH.md").write_text(
        "\n".join(
            [
                "---",
                "schema_version: 1",
                "repo: vibeforge1111/domain-chip-trading-crypto",
                "name: Crypto Trading",
                "run_command: spark-researcher run --command train",
                "publish_command: spark-researcher collective publish",
                "---",
                "",
                "# AUTORESEARCH",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config_path = _write_config(repo_root)
    runtime_root = repo_root
    row = {
        "run_id": "20260408-train",
        "created_at": "2026-04-08T16:00:00+00:00",
        "command_name": "train",
        "status": "ok",
        "metric_name": "score",
        "metric_value": 0.5,
        "verdict": "flat",
    }
    ledger = ledger_path(runtime_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    write_spark_swarm_collective_payload_from_latest(repo_root, runtime_root, load_config(config_path))

    payload = json.loads(spark_swarm_collective_payload_path(repo_root).read_text(encoding="utf-8"))
    assert payload["agentId"] == "agent:trading-crypto"
    assert payload["specialization"]["id"] == "specialization:trading-crypto"
    assert payload["specialization"]["label"] == "Crypto Trading"


def test_write_spark_swarm_collective_payload_from_trading_backtest(tmp_path: Path) -> None:
    repo_root = tmp_path
    _write_frontmatter_manifest(repo_root)
    config_path = _write_config(repo_root)
    runtime_root = repo_root
    row = {
        "run_id": "20260408-trading",
        "created_at": "2026-04-08T14:43:59+00:00",
        "command_name": "research",
        "status": "ok",
        "metric_name": "profitability_score",
        "metric_value": 0.4086,
        "verdict": "improved",
        "candidate_id": "trend-ema-btceth-4h",
        "candidate_summary": "Trend doctrine with EMA pullback continuation on BTC and ETH 4h.",
        "baseline_value": 0.3883,
        "metrics": {
            "paper_trade_readiness": 0.024,
            "max_drawdown": 0.99,
            "win_rate": 0.4286,
            "sharpe_ratio": -1.093,
        },
        "chip_result": {
            "data_mode": "contract_window_backtest",
            "requested_asset_universe": "BTC,ETH",
            "requested_timeframe": "4h",
            "evaluated_asset": "BTC",
            "evaluated_timeframe": "1h",
            "data_fallback_reason": "requested timeframe `4h` unavailable",
            "trade_count": 35,
            "minimum_trade_count": 25,
            "trade_count_gate_pass": True,
            "holdout_profitability_score": 0.4086,
            "walk_forward_consistency": 0.2,
            "stress_resilience": 0.0,
        },
    }
    ledger = ledger_path(runtime_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    write_spark_swarm_collective_payload_from_latest(repo_root, runtime_root, load_config(config_path))

    payload = json.loads(spark_swarm_collective_payload_path(repo_root).read_text(encoding="utf-8"))
    outcome = payload["outcomes"][0]
    assert outcome["context"]["benchmark"]["benchmarkName"] == "TradingBacktest"
    assert outcome["context"]["benchmark"]["scenarioId"] == "trend-ema-btceth-4h"
    assert outcome["context"]["benchmark"]["scenarioPack"] == "contract_window_backtest"
    assert outcome["context"]["benchmark"]["baselineId"] == "global-baseline"
    assert outcome["context"]["benchmark"]["strongestComponent"] == "holdout"
    assert outcome["context"]["trading"]["evaluatedAsset"] == "BTC"
    assert outcome["context"]["trading"]["evaluatedTimeframe"] == "1h"
    assert outcome["context"]["trading"]["fallbackReason"] == "requested timeframe `4h` unavailable"
    assert outcome["context"]["scorecard"]["modelLabel"] == "Trading backtest quality"
    assert outcome["context"]["scorecard"]["components"][1]["key"] == "win_rate"
    assert outcome["context"]["scorecard"]["details"][0]["key"] == "trade_count"
    assert outcome["benchmarkMetrics"]["requestedAssetUniverse"] == "BTC,ETH"
    assert outcome["benchmarkMetrics"]["tradeCount"] == 35
    assert outcome["benchmarkMetrics"]["paperTradeReadiness"] == 0.024
def test_repo_identity_stays_stable_when_manifest_label_changes(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "AUTORESEARCH.md").write_text(
        "\n".join(
            [
                "---",
                "schema_version: 1",
                "repo: vibeforge1111/domain-chip-trading-crypto",
                "name: Crypto Trading",
                "run_command: spark-researcher run --command train",
                "publish_command: spark-researcher collective publish",
                "---",
                "",
                "# AUTORESEARCH",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config_path = _write_config(repo_root)
    runtime_root = repo_root
    row = {
        "run_id": "20260408-train",
        "created_at": "2026-04-08T16:00:00+00:00",
        "command_name": "train",
        "status": "ok",
        "metric_name": "score",
        "metric_value": 0.5,
        "verdict": "flat",
    }
    ledger = ledger_path(runtime_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    write_spark_swarm_collective_payload_from_latest(repo_root, runtime_root, load_config(config_path))

    payload = json.loads(spark_swarm_collective_payload_path(repo_root).read_text(encoding="utf-8"))
    assert payload["agentId"] == "agent:trading-crypto"
    assert payload["specialization"]["id"] == "specialization:trading-crypto"
    assert payload["specialization"]["label"] == "Crypto Trading"


def test_evolution_path_ids_are_scoped_by_specialization(tmp_path: Path) -> None:
    startup_root = tmp_path / "startup"
    startup_root.mkdir()
    (startup_root / "AUTORESEARCH.md").write_text(
        "\n".join(
            [
                "---",
                "schema_version: 1",
                "repo: vibeforge1111/domain-chip-startup-yc",
                "name: Startup YC",
                "run_command: spark-researcher run --command research",
                "publish_command: spark-researcher collective publish",
                "---",
                "",
                "# AUTORESEARCH",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    trading_root = tmp_path / "trading"
    trading_root.mkdir()
    (trading_root / "AUTORESEARCH.md").write_text(
        "\n".join(
            [
                "---",
                "schema_version: 1",
                "repo: vibeforge1111/domain-chip-trading-crypto",
                "name: Crypto Trading",
                "run_command: spark-researcher run --command research",
                "publish_command: spark-researcher collective publish",
                "---",
                "",
                "# AUTORESEARCH",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    startup_config = load_config(_write_config(startup_root))
    trading_config = load_config(_write_config(trading_root))
    startup_record = {
        "run_id": "startup-run",
        "created_at": "2026-04-08T16:00:00+00:00",
        "command_name": "research",
        "status": "ok",
        "metric_name": "score",
        "metric_value": 0.71,
        "verdict": "improved",
    }
    trading_record = {
        "run_id": "trading-run",
        "created_at": "2026-04-08T16:05:00+00:00",
        "command_name": "research",
        "status": "ok",
        "metric_name": "profitability_score",
        "metric_value": 0.41,
        "verdict": "flat",
    }

    startup_payload = build_spark_swarm_collective_payload(startup_root, startup_root, startup_config, startup_record)
    trading_payload = build_spark_swarm_collective_payload(trading_root, trading_root, trading_config, trading_record)

    assert startup_payload["evolutionPaths"][0]["id"] == "evolution-path:startup-yc:research"
    assert trading_payload["evolutionPaths"][0]["id"] == "evolution-path:trading-crypto:research"
    assert startup_payload["evolutionPaths"][0]["id"] != trading_payload["evolutionPaths"][0]["id"]
    assert startup_payload["outcomes"][0]["targetId"] == startup_payload["evolutionPaths"][0]["id"]
    assert trading_payload["outcomes"][0]["targetId"] == trading_payload["evolutionPaths"][0]["id"]
def test_run_once_writes_spark_swarm_collective_payload(tmp_path: Path) -> None:
    repo_root = tmp_path
    _write_manifest(repo_root)
    (repo_root / "train.py").write_text("print('score=1.5')\n", encoding="utf-8")
    config_path = _write_config(repo_root)

    record = run_once(config_path, "train")

    payload_path = spark_swarm_collective_payload_path(repo_root)
    assert payload_path.exists()
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["outcomes"][0]["metricValue"] == 1.5
    assert payload["runtimePulse"]["stageKey"] == "train"
    assert payload["insights"][0]["id"] == f"insight:{record['run_id']}"
    assert "benchmarkMetrics" not in payload["outcomes"][0]
    assert not Path(record["workspace_root"]).exists()
    assert Path(record["log_path"]).exists()
    assert Path(record["run_dir"], "result.json").exists()


def test_run_once_dry_run_does_not_persist_ledger_or_swarm_payload(tmp_path: Path) -> None:
    repo_root = tmp_path
    _write_manifest(repo_root)
    (repo_root / "train.py").write_text("print('score=1.5')\n", encoding="utf-8")
    config_path = _write_config(repo_root)
    runtime_root = resolve_runtime_root(config_path)

    record = run_once(config_path, "train", dry_run=True)

    assert record["status"] == "ok"
    assert record["dry_run"] is True
    assert not ledger_path(runtime_root).exists()
    assert not spark_swarm_collective_payload_path(repo_root).exists()
    assert not Path(record["workspace_root"]).exists()


def test_collective_readiness_tracks_latest_payload_and_capsule(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    _write_frontmatter_manifest(repo_root)
    (repo_root / "train.py").write_text("print('score=1.5')\n", encoding="utf-8")
    config_path = _write_config(repo_root)
    runtime_root = resolve_runtime_root(config_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("SPARK_SWARM_WORKSPACE_ID", raising=False)

    readiness = collective_readiness(repo_root, runtime_root)
    assert readiness["ready"] is False
    assert "latest_metric_run_present" in readiness["missing"]

    record = run_once(config_path, "train")
    assert record["status"] == "ok"
    readiness = collective_readiness(repo_root, runtime_root)
    assert readiness["checks"]["spark_swarm_payload_current"] is True, readiness
    assert readiness["checks"]["capsule_present_for_latest_run"] is False

    publish_latest(repo_root, runtime_root)
    readiness = collective_readiness(repo_root, runtime_root)
    assert readiness["ready"] is True
    assert readiness["hosted_ready"] is False
    assert readiness["hosted_checks"]["spark_swarm_payload_has_workspace_id"] is False
    assert readiness["latest_metric_run"] == record["run_id"]


def test_collective_readiness_marks_hosted_ready_when_workspace_id_is_present(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    _write_frontmatter_manifest(repo_root)
    config_path = _write_config(repo_root)
    runtime_root = repo_root
    row = {
        "run_id": "20260319-train",
        "created_at": "2026-03-19T12:00:00+00:00",
        "command_name": "train",
        "status": "ok",
        "metric_name": "score",
        "metric_value": 1.25,
        "verdict": "improved",
    }
    ledger = ledger_path(runtime_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    monkeypatch.setenv("SPARK_SWARM_WORKSPACE_ID", "ws_demo")
    write_spark_swarm_collective_payload_from_latest(repo_root, runtime_root, load_config(config_path))
    publish_latest(repo_root, runtime_root)

    readiness = collective_readiness(repo_root, runtime_root)
    assert readiness["ready"] is True
    assert readiness["hosted_ready"] is True
    assert readiness["spark_swarm_workspace_id"] == "ws_demo"


def test_collective_readiness_rejects_stale_unscoped_path_ids(tmp_path: Path) -> None:
    repo_root = tmp_path
    _write_frontmatter_manifest(repo_root)
    config_path = _write_config(repo_root)
    runtime_root = repo_root
    row = {
        "run_id": "20260319-train",
        "created_at": "2026-03-19T12:00:00+00:00",
        "command_name": "research",
        "status": "ok",
        "metric_name": "score",
        "metric_value": 1.25,
        "verdict": "improved",
    }
    ledger = ledger_path(runtime_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    write_spark_swarm_collective_payload_from_latest(repo_root, runtime_root, load_config(config_path))
    payload_path = spark_swarm_collective_payload_path(repo_root)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["evolutionPaths"][0]["id"] = "evolution-path:research"
    payload["outcomes"][0]["targetId"] = "evolution-path:research"
    payload_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    readiness = collective_readiness(repo_root, runtime_root)
    assert readiness["ready"] is False
    assert readiness["checks"]["spark_swarm_payload_paths_match_specialization"] is False
    assert "spark_swarm_payload_paths_match_specialization" in readiness["missing"]
    assert readiness["spark_swarm_payload_path_diagnostics"]["reason"] == "unexpected_evolution_path_id"
    assert readiness["spark_swarm_payload_path_diagnostics"]["actual_path_id"] == "evolution-path:research"
    assert readiness["spark_swarm_payload_path_diagnostics"]["expected_path_id"] == "evolution-path:starter-lab:research"
    assert any("spark-researcher collective spark-swarm-payload --config" in action for action in readiness["recommended_actions"])


def test_collective_uses_bridge_bound_workspace_id_when_env_is_missing(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    _write_frontmatter_manifest(repo_root)
    config_path = _write_config(repo_root)
    runtime_root = repo_root
    row = {
        "run_id": "20260319-train",
        "created_at": "2026-03-19T12:00:00+00:00",
        "command_name": "train",
        "status": "ok",
        "metric_name": "score",
        "metric_value": 1.25,
        "verdict": "improved",
    }
    ledger = ledger_path(runtime_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    home = tmp_path / "home"
    bridge_root = home / ".spark-swarm"
    bridge_root.mkdir(parents=True)
    (bridge_root / "bridge-state.json").write_text(json.dumps({"workspace_id": "ws_bound"}) + "\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("SPARK_SWARM_WORKSPACE_ID", raising=False)

    write_spark_swarm_collective_payload_from_latest(repo_root, runtime_root, load_config(config_path))
    publish_latest(repo_root, runtime_root)

    payload = json.loads(spark_swarm_collective_payload_path(repo_root).read_text(encoding="utf-8"))
    readiness = collective_readiness(repo_root, runtime_root)
    assert payload["workspaceId"] == "ws_bound"
    assert readiness["hosted_ready"] is True
    assert readiness["spark_swarm_workspace_id"] == "ws_bound"
    assert readiness["spark_swarm_payload_workspace_id"] == "ws_bound"
    assert readiness["spark_swarm_bound_workspace_id"] == "ws_bound"
    assert readiness["hosted_checks"]["spark_swarm_workspace_binding_present"] is True


def test_collective_git_commands_use_bounded_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append({"command": command, **kwargs})
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(collective_module.subprocess, "run", fake_run)

    result = collective_module._run_command(["git", "status"], cwd=tmp_path)

    assert result.stdout == "ok\n"
    assert calls == [
        {
            "command": ["git", "status"],
            "cwd": str(tmp_path),
            "check": True,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "timeout": collective_module.COLLECTIVE_COMMAND_TIMEOUT_SECONDS,
        }
    ]


def test_sync_local_collective_rebuild_uses_bounded_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_frontmatter_manifest(repo_root)
    runtime_root = tmp_path / "runtime"
    collective_root = tmp_path / "autoresearch-collective"
    generated_path = collective_root / "dashboard" / "public" / "data" / "collective.generated.json"
    generated_path.parent.mkdir(parents=True)
    generated_path.write_text(
        json.dumps(
            {
                "repoDirectory": [{"repo": "vibeforge1111/starter-lab"}],
                "capsuleLibrary": [{"repo": "vibeforge1111/starter-lab"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    calls: list[dict[str, object]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append({"command": command, **kwargs})
        return subprocess.CompletedProcess(command, 0, stdout="rebuilt\n", stderr="")

    monkeypatch.setattr(collective_module.subprocess, "run", fake_run)

    result = collective_module.sync_local_collective(repo_root, runtime_root)

    assert result["repo_registered"] is True
    assert [call["command"] for call in calls] == [
        ["node", "./scripts/build-collective-data.mjs"],
        ["node", "./scripts/build-graph-data.mjs"],
    ]
    assert all(call["timeout"] == collective_module.COLLECTIVE_COMMAND_TIMEOUT_SECONDS for call in calls)
    assert all(call["check"] is False for call in calls)


def test_publish_latest_normalizes_non_collective_verdicts(tmp_path: Path) -> None:
    repo_root = tmp_path
    _write_frontmatter_manifest(repo_root)
    config_path = _write_config(repo_root)
    runtime_root = repo_root
    row = {
        "run_id": "20260319-train",
        "created_at": "2026-03-19T12:00:00+00:00",
        "command_name": "train",
        "status": "ok",
        "metric_name": "score",
        "metric_value": 1.25,
        "baseline_value": 1.25,
        "verdict": "near_best",
        "candidate_id": "baseline",
    }
    ledger = ledger_path(runtime_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    published = publish_latest(repo_root, runtime_root)

    payload = json.loads(Path(published["manifest_path"]).read_text(encoding="utf-8"))
    assert payload["verdict"] == "flat"
    markdown = Path(published["markdown_path"]).read_text(encoding="utf-8")
    assert "verdict: flat" in markdown
