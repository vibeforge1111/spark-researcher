from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from spark_researcher.collective import _run_command
from spark_researcher.self_edit import run_git_status
from spark_researcher.adapters.exec import execute_advisory


def test_collective_run_command_times_out_cleanly(tmp_path: Path) -> None:
    with patch(
        "spark_researcher.collective.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["node", "x"], timeout=1),
    ):
        with pytest.raises(RuntimeError, match=r"Command timed out"):
            _run_command(["node", "x"], cwd=tmp_path)


def test_self_edit_git_status_sets_timeout(tmp_path: Path) -> None:
    with patch("spark_researcher.self_edit.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess(args=["git"], returncode=0, stdout="", stderr="")
        run_git_status(tmp_path)
        assert "timeout" in run.call_args.kwargs


def test_execute_advisory_times_out_cleanly(tmp_path: Path) -> None:
    advisory_root = tmp_path / "advisory"
    advisory_root.mkdir()
    with patch(
        "spark_researcher.adapters.exec._resolve_command",
        return_value=["python", "-c", "sleep"],
    ), patch(
        "spark_researcher.adapters.exec.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["python", "-c", "sleep"], timeout=1),
    ):
        with pytest.raises(RuntimeError, match=r"timed out"):
            execute_advisory(
                runtime_root=tmp_path,
                advisory={"command": "python -c 'import time; time.sleep(5)'"},
                model="codex",
            )


def test_execute_advisory_respects_timeout_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPARK_RESEARCHER_SUBPROCESS_TIMEOUT_SECONDS", "900")
    advisory_root = tmp_path / "advisory"
    advisory_root.mkdir()
    with patch(
        "spark_researcher.adapters.exec._resolve_command",
        return_value=["echo", "ok"],
    ), patch("spark_researcher.adapters.exec.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess(args=["echo", "ok"], returncode=0, stdout="ok", stderr="")
        execute_advisory(
            runtime_root=tmp_path,
            advisory={"command": "echo ok"},
            model="codex",
        )
        assert "timeout" in run.call_args.kwargs
        assert run.call_args.kwargs["timeout"] == 900.0

