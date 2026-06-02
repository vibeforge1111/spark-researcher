from __future__ import annotations

from pathlib import Path

import pytest

import spark_researcher.runner as runner
from spark_researcher.config import CandidateTrial, CommandSpec, GuardrailSpec, MetricSpec, ProjectConfig, save_config


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
