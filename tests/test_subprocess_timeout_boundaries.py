from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from spark_researcher import self_edit
from spark_researcher.collective import _run_command
from spark_researcher.config import TrainerSpec
from spark_researcher.runner import run_process
from spark_researcher.trainers import read_state, run_trainer, trainer_state_path


def test_collective_timeout_is_reported_as_bounded_command_failure(tmp_path: Path) -> None:
    with patch(
        "spark_researcher.collective.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["node", "build.mjs"], timeout=120),
    ):
        with pytest.raises(RuntimeError, match="Command timed out after 120 seconds"):
            _run_command(["node", "build.mjs"], cwd=tmp_path)


def test_self_edit_git_status_timeout_fails_closed(tmp_path: Path) -> None:
    with patch(
        "spark_researcher.self_edit.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["git", "status"], timeout=30),
    ) as run_mock:
        with pytest.raises(RuntimeError, match="Git command timed out after 30 seconds"):
            self_edit.run_git_status(tmp_path)
    assert run_mock.call_args.kwargs["timeout"] == 30.0


def test_self_edit_git_helper_uses_the_same_bounded_timeout(tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess(args=["git"], returncode=0, stdout="", stderr="")
    with patch("spark_researcher.self_edit.subprocess.run", return_value=completed) as run_mock:
        self_edit._git(tmp_path, "rev-parse", "HEAD")
    assert run_mock.call_args.kwargs["timeout"] == 30.0


def test_self_edit_proposal_timeout_persists_failed_truth(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_path = repo_root / "spark.toml"
    config_path.write_text("[project]\n", encoding="utf-8")
    runtime_root = tmp_path / "runtime"
    workspace = tmp_path / "workspace"
    config = SimpleNamespace(
        self_edit=SimpleNamespace(
            mutable_targets=["README.md"],
            prompt_preamble="",
            command=["agent", "--request", "{request}"],
        ),
        mutable_targets=["README.md"],
        guardrails=SimpleNamespace(require_clean_git_for_self_edit=True, blocked_command_fragments=[]),
    )
    monkeypatch.setattr(self_edit, "load_config", lambda _path: config)
    monkeypatch.setattr(self_edit, "resolve_runtime_root", lambda _path: runtime_root)
    monkeypatch.setattr(self_edit, "run_git_status", lambda _root: "")
    monkeypatch.setattr(self_edit, "_workspace_dir", lambda _proposal_id: workspace)
    monkeypatch.setattr(self_edit, "copy_repo", lambda _source, target: target.mkdir(parents=True))
    monkeypatch.setattr(self_edit, "collect_changes", lambda *_args: ([], []))

    with patch(
        "spark_researcher.self_edit.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["agent"], timeout=600),
    ) as run_mock:
        proposal = self_edit.propose(config_path, "tighten the prompt")

    assert run_mock.call_args.kwargs["timeout"] == 600.0
    assert proposal["status"] == "failed"
    assert Path(proposal["stdout_path"]).read_text(encoding="utf-8") == "\n"
    assert Path(proposal["stderr_path"]).read_text(encoding="utf-8") == "Command timed out after 600 seconds.\n"


def test_runner_process_timeout_returns_a_bounded_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log_path = tmp_path / "private-run.log"
    monkeypatch.setenv("SPARK_RESEARCHER_SUBPROCESS_TIMEOUT_SECONDS", "7")

    with patch(
        "spark_researcher.runner.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["python", "eval.py"], timeout=7),
    ) as run_mock:
        result = run_process(["python", "eval.py"], tmp_path, log_path)

    assert run_mock.call_args.kwargs["timeout"] == 7.0
    assert result.returncode == -1
    assert result.stdout == ""
    assert result.stderr == "Command timed out after 7 seconds."
    assert log_path.read_text(encoding="utf-8") == "[stderr]\nCommand timed out after 7 seconds.\n"


def test_trainer_timeout_persists_private_truth_and_returns_public_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    examples_path = tmp_path / "private-examples.jsonl"
    examples_path.write_text('{"example": 1}\n', encoding="utf-8")
    runtime_root = tmp_path / "runtime"
    command = ["python", "compile.py"]
    spec = TrainerSpec(
        name="bounded-trainer",
        examples_path=examples_path.name,
        compile_command=command,
        min_examples=1,
        recompile_every=1,
        max_examples=8,
    )
    monkeypatch.setenv("SPARK_RESEARCHER_SUBPROCESS_TIMEOUT_SECONDS", "11")

    with patch(
        "spark_researcher.trainers.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            cmd=command,
            timeout=11,
            output="private partial output",
            stderr="private compiler path",
        ),
    ) as run_mock:
        result = run_trainer(spec, tmp_path, runtime_root)

    assert run_mock.call_args.kwargs["timeout"] == 11.0
    assert result["status"] == "timed_out"
    assert result["last_status"] == "timed_out"
    assert result["last_reason"] == "Trainer compile timed out after 11 seconds."
    assert "command" not in result
    assert "stdout_excerpt" not in result
    assert "stderr_excerpt" not in result

    private_state = read_state(trainer_state_path(runtime_root, "bounded-trainer"))
    assert private_state["command"] == command
    assert private_state["stdout_excerpt"] == "private partial output"
    assert private_state["stderr_excerpt"] == "private compiler path"
