from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from spark_researcher import self_edit
from spark_researcher.collective import _run_command


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
