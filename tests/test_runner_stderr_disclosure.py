"""Tests: stderr_excerpt not included in run record returned to API callers."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spark_researcher.runner import build_record, CommandResult


def _minimal_config():
    from spark_researcher.config import ProjectConfig
    return MagicMock(
        spec=ProjectConfig,
        project_name="test-project",
        eval_metric="accuracy",
        eval_goal="maximize",
    )


def _command_result(stderr: str = "") -> CommandResult:
    return CommandResult(
        returncode=1,
        stdout="some output",
        stderr=stderr,
        command=["python", "eval.py"],
        cwd="/tmp/workspace",
    )


def _call_build_record(stderr: str = "ERROR: /internal/path/model.py failed") -> dict:
    return build_record(
        config=_minimal_config(),
        command_name="eval",
        command_result=_command_result(stderr=stderr),
        run_dir=Path("/tmp/run-001"),
        log_path=Path("/tmp/run-001/eval.log"),
        metrics={},
        baseline_value=None,
        verdict="unknown",
        trial=None,
        applied_mutations=[],
    )


def test_stderr_excerpt_not_present_in_run_record():
    record = _call_build_record("Traceback: /internal/models/v3.weights not found")
    assert "stderr_excerpt" not in record


def test_full_stderr_logged_server_side(caplog):
    import logging
    with caplog.at_level(logging.WARNING, logger="spark_researcher.runner"):
        _call_build_record("/internal/secret/path traceback error")
    assert any("/internal/secret/path" in r.message or "/internal/secret/path" in str(r) for r in caplog.records)


def test_crafted_mutation_error_does_not_leak_internal_paths():
    record = _call_build_record("FileNotFoundError: /usr/local/spark/research/config.db")
    record_str = json.dumps(record)
    assert "/usr/local/spark" not in record_str


def test_run_record_still_contains_all_safe_fields():
    record = _call_build_record()
    for field in ("run_id", "status", "returncode", "command_name", "project_name"):
        assert field in record


def test_stdout_excerpt_still_present_for_diagnostics():
    record = _call_build_record()
    assert "stdout_excerpt" in record
