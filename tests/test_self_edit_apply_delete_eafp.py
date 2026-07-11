from __future__ import annotations

import json
from pathlib import Path

import pytest

from spark_researcher.config import CommandSpec, MetricSpec, ProjectConfig, save_config
from spark_researcher.self_edit import _proposal_path, _review_path, apply_proposal


def _write_delete_fixture(repo_root: Path, proposal_id: str, *, prepopulate_target: bool) -> tuple[Path, Path]:
    repo_root.mkdir(parents=True, exist_ok=True)
    config_path = repo_root / "spark-researcher.project.json"
    save_config(
        config_path,
        ProjectConfig(
            project_name="self-edit-delete-test",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
            metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
        ),
    )
    target = repo_root / "OBSOLETE.md"
    if prepopulate_target:
        target.write_text("stale\n", encoding="utf-8")
    workspace_root = repo_root / "proposal-workspace"
    workspace_root.mkdir()
    proposal = {
        "proposal_id": proposal_id,
        "status": "reviewed",
        "change_count": 1,
        "blocked_changes": [],
        "allowed_changes": [{"path": "OBSOLETE.md", "status": "deleted"}],
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


def test_apply_proposal_deletion_when_target_missing_does_not_raise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Race scenario: between the pre-patch exists() probe and the unlink() call a parallel
    cleanup removes the target. Post-patch the call uses unlink(missing_ok=True) and is a no-op.

    We trigger the same code path by passing a deletion proposal whose target was never created
    in the fixture (`prepopulate_target=False`). Pre-patch this still passed because exists()
    guarded the unlink; the regression value is that we now exercise the code path that the
    new EAFP idiom serves and assert it stays a no-op on the deletion side.
    """
    proposal_id = "proposal-del-missing"
    repo_root = tmp_path / "repo"
    config_path, target = _write_delete_fixture(repo_root, proposal_id, prepopulate_target=False)

    monkeypatch.setattr("spark_researcher.self_edit.run_git_status", lambda repo_root: False)
    monkeypatch.setattr("spark_researcher.self_edit._current_branch", lambda repo_root: "main")
    monkeypatch.setattr("spark_researcher.self_edit._remote_exists", lambda repo_root: True)

    result = apply_proposal(config_path, proposal_id, git_mode_override="manual", push_override=False)

    assert not target.exists()
    proposal = json.loads(_proposal_path(repo_root, proposal_id).read_text(encoding="utf-8"))
    assert proposal["status"] == "applied"
    assert result["applied_files"] == ["OBSOLETE.md"]


def test_apply_proposal_deletion_when_target_present_unlinks_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Happy-path regression: deletion proposal still unlinks the target when it exists."""
    proposal_id = "proposal-del-present"
    repo_root = tmp_path / "repo"
    config_path, target = _write_delete_fixture(repo_root, proposal_id, prepopulate_target=True)
    assert target.exists()

    monkeypatch.setattr("spark_researcher.self_edit.run_git_status", lambda repo_root: False)
    monkeypatch.setattr("spark_researcher.self_edit._current_branch", lambda repo_root: "main")
    monkeypatch.setattr("spark_researcher.self_edit._remote_exists", lambda repo_root: True)

    apply_proposal(config_path, proposal_id, git_mode_override="manual", push_override=False)

    assert not target.exists()
