from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from spark_researcher.config import CommandSpec, MetricSpec, MutationSpec, ProjectConfig
from spark_researcher.runner import apply_mutations
from spark_researcher.self_edit import (
    _proposal_dir,
    _validated_workspace_root,
    _workspace_dir,
)


@pytest.mark.parametrize(
    "proposal_id",
    ["", "../outside", "nested/proposal", r"nested\proposal", "/absolute", r"C:\absolute"],
)
def test_proposal_id_is_one_nonreflecting_identifier(tmp_path: Path, proposal_id: str) -> None:
    with pytest.raises(ValueError) as error:
        _proposal_dir(tmp_path, proposal_id)
    assert proposal_id not in str(error.value)


def test_valid_proposal_id_stays_inside_self_edit_root(tmp_path: Path) -> None:
    path = _proposal_dir(tmp_path, "proposal-safe")
    assert path == (tmp_path / "artifacts" / "self-edit" / "proposal-safe").resolve()


def test_stored_workspace_must_be_the_private_proposal_workspace(tmp_path: Path) -> None:
    workspace = _workspace_dir("proposal-safe")
    workspace.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    try:
        assert _validated_workspace_root("proposal-safe", str(workspace)) == workspace.resolve()
        with pytest.raises(RuntimeError, match="workspace authority"):
            _validated_workspace_root("proposal-safe", str(external))
    finally:
        shutil.rmtree(workspace.parent, ignore_errors=True)


@pytest.mark.skipif(os.name == "nt", reason="symlink setup differs on Windows")
def test_stored_workspace_rejects_symlink_escape(tmp_path: Path) -> None:
    workspace = _workspace_dir("proposal-safe")
    external = tmp_path / "external"
    external.mkdir()
    workspace.parent.mkdir(parents=True, exist_ok=True)
    workspace.symlink_to(external, target_is_directory=True)
    try:
        with pytest.raises(RuntimeError, match="workspace authority"):
            _validated_workspace_root("proposal-safe", str(workspace))
    finally:
        shutil.rmtree(workspace.parent, ignore_errors=True)


def test_runner_mutation_target_cannot_escape_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("value=old\n", encoding="utf-8")
    config = ProjectConfig(
        project_name="demo",
        project_root=".",
        eval_metric="score",
        eval_goal="maximize",
        commands={"train": CommandSpec(args=["python", "-c", "print('score=1')"])},
        metrics={"score": MetricSpec(pattern=r"score=(?P<value>\d+)")},
        mutable_parameters=[
            MutationSpec(
                name="value",
                file="../outside.txt",
                pattern="value=old",
                template="value={value}",
            )
        ],
    )

    with pytest.raises(ValueError, match="owned root"):
        apply_mutations(workspace, config, {"value": "new"})
    assert outside.read_text(encoding="utf-8") == "value=old\n"
