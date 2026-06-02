from __future__ import annotations

from pathlib import Path

import pytest

from spark_researcher.config import CommandSpec, MetricSpec, MutationSpec, ProjectConfig
from spark_researcher.runner import apply_mutations


def _config_with_two_params() -> ProjectConfig:
    return ProjectConfig(
        project_name="apply-mutations-test",
        project_root=".",
        eval_metric="score",
        eval_goal="maximize",
        commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
        metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
        mutable_parameters=[
            MutationSpec(
                name="learning_rate",
                file="config.json",
                pattern=r'"learning_rate":\s*[0-9.]+',
                template='"learning_rate": {value}',
            ),
            MutationSpec(
                name="weight_decay",
                file="config.json",
                pattern=r'"weight_decay":\s*[0-9.]+',
                template='"weight_decay": {value}',
            ),
        ],
    )


def _config_with_no_params() -> ProjectConfig:
    return ProjectConfig(
        project_name="apply-mutations-empty",
        project_root=".",
        eval_metric="score",
        eval_goal="maximize",
        commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
        metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
        mutable_parameters=[],
    )


def test_apply_mutations_unknown_param_names_known_parameters(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = _config_with_two_params()

    with pytest.raises(KeyError) as excinfo:
        apply_mutations(workspace, config, {"learnig_rate": "0.001"})

    message = str(excinfo.value)
    assert "Unknown mutable parameter: learnig_rate" in message
    assert "learning_rate" in message
    assert "weight_decay" in message
    assert "Known mutable parameters" in message


def test_apply_mutations_unknown_param_with_no_registered_params_names_config_file(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = _config_with_no_params()

    with pytest.raises(KeyError) as excinfo:
        apply_mutations(workspace, config, {"learning_rate": "0.001"})

    message = str(excinfo.value)
    assert "Unknown mutable parameter: learning_rate" in message
    assert "spark-researcher.project.json" in message
