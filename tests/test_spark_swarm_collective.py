from __future__ import annotations

import json
import sys
from pathlib import Path

from spark_researcher.collective import write_spark_swarm_collective_payload_from_latest
from spark_researcher.config import load_config
from spark_researcher.paths import ledger_path, spark_swarm_collective_payload_path
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
    assert payload["insights"][0]["status"] == "live_supported"
    assert payload["outcomes"][0]["verdict"] == "improved"


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
