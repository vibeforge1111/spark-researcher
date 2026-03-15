from __future__ import annotations

import json
from pathlib import Path

import pytest

from spark_researcher.config import CommandSpec, MetricSpec, ProjectConfig, save_config
from spark_researcher.self_edit import _proposal_path, _review_path, apply_proposal


def _write_self_edit_fixture(repo_root: Path, proposal_id: str) -> tuple[Path, Path]:
    repo_root.mkdir(parents=True, exist_ok=True)
    config_path = repo_root / "spark-researcher.project.json"
    save_config(
        config_path,
        ProjectConfig(
            project_name="self-edit-test",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
            metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
        ),
    )
    target = repo_root / "README.md"
    target.write_text("old\n", encoding="utf-8")
    workspace_root = repo_root / "proposal-workspace"
    workspace_root.mkdir()
    (workspace_root / "README.md").write_text("new\n", encoding="utf-8")
    proposal = {
        "proposal_id": proposal_id,
        "status": "reviewed",
        "change_count": 1,
        "blocked_changes": [],
        "allowed_changes": [{"path": "README.md", "status": "modified"}],
        "workspace_root": str(workspace_root),
    }
    proposal_path = _proposal_path(repo_root, proposal_id)
    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    review_path = _review_path(repo_root, proposal_id)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        json.dumps({"decision": "approve", "lineage_failures": ["a", "b", "c"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path, target


def test_apply_proposal_checks_remote_before_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    proposal_id = "proposal-1"
    config_path, target = _write_self_edit_fixture(tmp_path / "repo", proposal_id)

    monkeypatch.setattr("spark_researcher.self_edit.run_git_status", lambda repo_root: False)
    monkeypatch.setattr("spark_researcher.self_edit._current_branch", lambda repo_root: "main")
    monkeypatch.setattr("spark_researcher.self_edit._remote_exists", lambda repo_root: False)

    with pytest.raises(RuntimeError, match="origin"):
        apply_proposal(config_path, proposal_id, git_mode_override="main", push_override=True)

    assert target.read_text(encoding="utf-8") == "old\n"
    proposal = json.loads(_proposal_path(tmp_path / "repo", proposal_id).read_text(encoding="utf-8"))
    assert proposal["status"] == "reviewed"
    assert "applied_at" not in proposal


def test_apply_proposal_records_push_failure_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    proposal_id = "proposal-2"
    repo_root = tmp_path / "repo"
    config_path, target = _write_self_edit_fixture(repo_root, proposal_id)

    monkeypatch.setattr("spark_researcher.self_edit.run_git_status", lambda repo_root: False)
    monkeypatch.setattr("spark_researcher.self_edit._current_branch", lambda repo_root: "main")
    monkeypatch.setattr("spark_researcher.self_edit._remote_exists", lambda repo_root: True)
    monkeypatch.setattr("spark_researcher.self_edit._commit_paths", lambda repo_root, paths, message: "abc123")

    def _raise_push(repo_root: Path, branch_name: str, remote_name: str = "origin") -> None:
        raise RuntimeError("push broke")

    monkeypatch.setattr("spark_researcher.self_edit._push_branch", _raise_push)

    with pytest.raises(RuntimeError, match="push broke"):
        apply_proposal(config_path, proposal_id, git_mode_override="main", push_override=True)

    assert target.read_text(encoding="utf-8") == "new\n"
    proposal = json.loads(_proposal_path(repo_root, proposal_id).read_text(encoding="utf-8"))
    assert proposal["status"] == "applied_push_failed"
    assert proposal["git_commit_sha"] == "abc123"
    assert proposal["git_pushed"] is False
    assert proposal["apply_error"] == "push broke"
