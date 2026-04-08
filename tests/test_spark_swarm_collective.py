from __future__ import annotations

import json
import sys
from pathlib import Path

from spark_researcher.collective import collective_readiness, publish_latest, write_spark_swarm_collective_payload_from_latest
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
