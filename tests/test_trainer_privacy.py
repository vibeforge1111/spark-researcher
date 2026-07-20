from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import spark_researcher.trainers as trainers_module
from spark_researcher.config import CommandSpec, MetricSpec, ProjectConfig, TrainerSpec, save_config
from spark_researcher.trainers import read_state, run_all_trainers, trainer_state_path, trainer_status


def test_trainer_public_results_are_metadata_only_while_private_state_keeps_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "private-token-repo"
    repo_root.mkdir()
    examples_path = repo_root / "private-token-examples.jsonl"
    examples_path.write_text('{"example": 1}\n', encoding="utf-8")
    config_path = repo_root / "spark-researcher.project.json"
    private_command = [sys.executable, str(repo_root / "private-token-compiler.py")]
    config = ProjectConfig(
        project_name="trainer-privacy",
        project_root=".",
        eval_metric="score",
        eval_goal="maximize",
        commands={"research": CommandSpec(args=[sys.executable, "-c", "print('noop')"])},
        metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
        trainers=[
            TrainerSpec(
                name="private-trainer",
                examples_path=examples_path.name,
                compile_command=private_command,
                min_examples=1,
                recompile_every=1,
                max_examples=8,
            )
        ],
    )
    save_config(config_path, config)
    private_stdout = f"compiled from {examples_path}"
    private_stderr = f"fatal: cannot read {repo_root / 'private-secret-token'}"
    monkeypatch.setattr(
        trainers_module.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(private_command, 1, private_stdout, private_stderr),
    )

    run_result = run_all_trainers(config_path)
    status_result = trainer_status(config_path)

    public_text = json.dumps({"run": run_result, "status": status_result}, sort_keys=True)
    assert str(repo_root) not in public_text
    assert private_stdout not in public_text
    assert private_stderr not in public_text
    public_row = run_result["results"][0]
    assert public_row["last_status"] == "failed"
    assert public_row["example_count"] == 1
    assert "stdout_excerpt" not in public_row
    assert "stderr_excerpt" not in public_row
    assert "command" not in public_row
    assert "examples_path" not in public_row

    private_state = read_state(trainer_state_path(repo_root, "private-trainer"))
    assert private_state["stdout_excerpt"] == private_stdout
    assert private_state["stderr_excerpt"] == private_stderr
    assert private_state["command"] == private_command

