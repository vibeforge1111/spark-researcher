from __future__ import annotations

import json
from pathlib import Path

import pytest

from spark_researcher.config import CommandSpec, MetricSpec, ProjectConfig, save_config
from spark_researcher.self_edit import _proposal_dir, _proposal_path, apply_proposal, review_proposal


def _write_self_edit_fixture(repo_root: Path, proposal_id: str) -> Path:
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
    proposal = {
        "proposal_id": proposal_id,
        "status": "reviewed",
        "change_count": 0,
        "blocked_changes": [],
        "allowed_changes": [],
        "workspace_root": str(repo_root / "workspace"),
    }
    proposal_path = _proposal_path(repo_root, proposal_id)
    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    review_path = proposal_path.parent / "review.json"
    review_path.write_text(
        json.dumps({"decision": "approve", "lineage_failures": ["a", "b", "c"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path


@pytest.mark.parametrize(
    "proposal_id",
    [
        "../../../outside-proposal",
        "nested/proposal",
        r"nested\proposal",
        "",
        "   ",
    ],
)
def test_validate_proposal_id_rejects_unsafe_values(tmp_path: Path, proposal_id: str) -> None:
    with pytest.raises(ValueError, match="proposal_id"):
        _proposal_dir(tmp_path / "runtime", proposal_id)


def test_review_proposal_rejects_path_traversal_proposal_id(tmp_path: Path) -> None:
    config_path = _write_self_edit_fixture(tmp_path / "repo", "safe-proposal")

    with pytest.raises(ValueError, match="proposal_id"):
        review_proposal(
            config_path,
            "../../../outside-proposal",
            decision="approve",
            root_lesson="lesson",
            lineage_failures=["a", "b", "c"],
            counterfactual="counter",
            ghost_improvement_check="ghost",
            rollback_condition="rollback",
        )


def test_apply_proposal_rejects_path_traversal_proposal_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proposal_id = "safe-proposal"
    config_path = _write_self_edit_fixture(tmp_path / "repo", proposal_id)
    monkeypatch.setattr("spark_researcher.self_edit.run_git_status", lambda repo_root: False)

    with pytest.raises(ValueError, match="proposal_id"):
        apply_proposal(config_path, "../../../outside-proposal", git_mode_override="manual")
