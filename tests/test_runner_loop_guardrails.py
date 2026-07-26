from __future__ import annotations

from pathlib import Path

import pytest

import spark_researcher.runner as runner
from spark_researcher.config import CandidateTrial, CommandSpec, GuardrailSpec, MetricSpec, MutationSpec, ProjectConfig, save_config


def _write_loop_config(tmp_path: Path, *, max_loop_iterations: int) -> Path:
    config_path = tmp_path / "spark-researcher.project.json"
    save_config(
        config_path,
        ProjectConfig(
            project_name="demo",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"train": CommandSpec(args=["python", "-c", "print('score=1')"])},
            metrics={"score": MetricSpec(pattern=r"score=(?P<value>\d+)")},
            candidate_trials=[CandidateTrial(candidate_id=f"trial-{index}") for index in range(6)],
            guardrails=GuardrailSpec(max_loop_iterations=max_loop_iterations, consecutive_discard_limit=99),
        ),
    )
    return config_path


def test_apply_mutations_unknown_param_names_known_parameters(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = ProjectConfig(
        project_name="demo",
        project_root=".",
        eval_metric="score",
        eval_goal="maximize",
        commands={"train": CommandSpec(args=["python", "-c", "print('score=1')"])},
        metrics={"score": MetricSpec(pattern=r"score=(?P<value>\d+)")},
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

    with pytest.raises(KeyError) as error:
        runner.apply_mutations(workspace, config, {"learnig_rate": "0.001"})

    message = str(error.value)
    assert "Unknown mutable parameter: learnig_rate" in message
    assert "Known mutable parameters: learning_rate, weight_decay" in message


def test_apply_mutations_unknown_param_when_none_defined_names_config_field(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = ProjectConfig(
        project_name="demo",
        project_root=".",
        eval_metric="score",
        eval_goal="maximize",
        commands={"train": CommandSpec(args=["python", "-c", "print('score=1')"])},
        metrics={"score": MetricSpec(pattern=r"score=(?P<value>\d+)")},
    )

    with pytest.raises(KeyError) as error:
        runner.apply_mutations(workspace, config, {"learning_rate": "0.001"})

    message = str(error.value)
    assert "Unknown mutable parameter: learning_rate" in message
    assert "`mutable_parameters`" in message


def test_run_loop_reports_when_requested_limit_is_capped_by_guardrail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_loop_config(tmp_path, max_loop_iterations=2)
    seen_trials: list[str] = []

    def fake_run_once(*args: object, trial: CandidateTrial, **kwargs: object) -> dict[str, object]:
        seen_trials.append(trial.candidate_id)
        return {"verdict": "flat", "status": "ok"}

    monkeypatch.setattr(runner, "run_once", fake_run_once)

    result = runner.run_loop(config_path, "train", limit=5)

    assert seen_trials == ["trial-0", "trial-1"]
    assert result["requested_limit"] == 5
    assert result["max_iterations"] == 2
    assert result["limit_clamped_to_guardrail"] is True


def test_run_loop_reports_unclamped_default_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = _write_loop_config(tmp_path, max_loop_iterations=3)

    monkeypatch.setattr(
        runner,
        "run_once",
        lambda *args, trial, **kwargs: {"verdict": "flat", "status": "ok"},
    )

    result = runner.run_loop(config_path, "train")

    assert result["run_count"] == 3
    assert result["requested_limit"] == 3
    assert result["max_iterations"] == 3
    assert result["limit_clamped_to_guardrail"] is False
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_run_loop_emits_opt_in_progress_to_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = _write_loop_config(tmp_path, max_loop_iterations=3)
    monkeypatch.setattr(
        runner,
        "run_once",
        lambda *args, trial, **kwargs: {"verdict": "flat", "status": "ok"},
    )

    runner.run_loop(config_path, "train", emit_progress=True)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        "[1/3] candidate=trial-0 verdict=flat",
        "[2/3] candidate=trial-1 verdict=flat",
        "[3/3] candidate=trial-2 verdict=flat",
    ]


def test_run_loop_progress_escapes_terminal_control_characters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = ProjectConfig(
        project_name="demo",
        project_root=".",
        eval_metric="score",
        eval_goal="maximize",
        commands={"train": CommandSpec(args=["python", "-c", "print('score=1')"])},
        metrics={"score": MetricSpec(pattern=r"score=(?P<value>\d+)")},
        candidate_trials=[CandidateTrial(candidate_id="trial\n\x1b[31m")],
        guardrails=GuardrailSpec(max_loop_iterations=1, consecutive_discard_limit=99),
    )
    monkeypatch.setattr(runner, "load_config", lambda _path: config)
    monkeypatch.setattr(
        runner,
        "run_once",
        lambda *args, trial, **kwargs: {"verdict": "flat\rresult", "status": "ok"},
    )

    runner.run_loop(tmp_path / "config.json", "train", emit_progress=True)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "[1/1] candidate=trial\\n\\u001b[31m verdict=flat\\rresult\n"
