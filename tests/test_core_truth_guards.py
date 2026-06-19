from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from memory_governor import memory_governor_decision
from spark_researcher import obsidian
from spark_researcher.obsidian import vault_authority_refs
from spark_researcher import candidates, runner, trainers, trial_queue
from spark_researcher.config import CandidateTrial, CommandSpec, MetricSpec, ProjectConfig, load_config
from spark_researcher.outcomes import load_advisory_outcomes
from spark_researcher.paths import ledger_path, trainers_root
from spark_researcher.trainers import read_state, write_state
from spark_researcher.tracing import start_trace, trace_status
from spark_researcher.trial_queue import append_queue_trials, load_queue_trials, queue_path_for_config


def _write_ledger(runtime_root: Path, rows: list[dict]) -> None:
    path = ledger_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_best_metric_ignores_failed_rows(tmp_path: Path) -> None:
    runtime_root = tmp_path
    _write_ledger(
        runtime_root,
        [
            {"command_name": "research", "status": "ok", "metric_value": 1.0, "applied_mutations": []},
            {"command_name": "research", "status": "failed", "metric_value": 9.0, "applied_mutations": [{"name": "x", "value": "9"}]},
            {"command_name": "research", "status": "ok", "metric_value": 5.0, "applied_mutations": [{"name": "x", "value": "5"}]},
        ],
    )

    assert runner.best_metric(runtime_root, "research", "maximize") == 5.0


def test_baseline_metric_only_uses_ok_baseline_rows(tmp_path: Path) -> None:
    runtime_root = tmp_path
    _write_ledger(
        runtime_root,
        [
            {"command_name": "research", "status": "ok", "metric_value": 0.6, "applied_mutations": []},
            {"command_name": "research", "status": "ok", "metric_value": 0.95, "applied_mutations": [{"name": "mode", "value": "candidate"}]},
            {"command_name": "research", "status": "failed", "metric_value": 0.99, "applied_mutations": []},
        ],
    )

    assert runner.baseline_metric(runtime_root, "research", "maximize") == 0.6


def test_candidate_primitive_selection_ignores_failed_rows() -> None:
    rows = [
        {"command_name": "research", "status": "ok", "metric_value": 1.0, "applied_mutations": []},
        {
            "command_name": "research",
            "status": "failed",
            "metric_value": 9.0,
            "verdict": "improved",
            "candidate_id": "bad",
            "applied_mutations": [{"name": "lane", "value": "bad"}],
        },
        {
            "command_name": "research",
            "status": "ok",
            "metric_value": 2.0,
            "verdict": "improved",
            "candidate_id": "good",
            "applied_mutations": [{"name": "lane", "value": "good"}],
        },
    ]

    best = candidates._best_single_primitives(rows, "research", "maximize", baseline_metric=1.0)

    assert best == {
        "lane": {
            "name": "lane",
            "value": "good",
            "metric_value": 2.0,
            "candidate_id": "good",
            "reason": "beats baseline",
        }
    }


def test_candidate_ids_do_not_collapse_decimal_values() -> None:
    assert candidates._candidate_id({"learning_rate": "1.5"}) != candidates._candidate_id({"learning_rate": "15"})
    assert candidates._candidate_id({"learning_rate": "1.5"}) != candidates._candidate_id({"learning_rate": "1_dot_5"})


def test_failed_and_unknown_rows_count_as_discards() -> None:
    assert runner.row_counts_as_discard({"status": "failed", "verdict": "baseline"}) is True
    assert runner.row_counts_as_discard({"status": "ok", "verdict": "unknown"}) is True
    assert runner.row_counts_as_discard({"status": "ok", "verdict": "regressed"}) is True
    assert runner.row_counts_as_discard({"status": "ok", "verdict": "improved"}) is False

    assert candidates._row_counts_as_discard({"status": "failed", "verdict": "baseline"}) is True
    assert candidates._row_counts_as_discard({"status": "ok", "verdict": "unknown"}) is True
    assert candidates._row_counts_as_discard({"status": "ok", "verdict": "regressed"}) is True
    assert candidates._row_counts_as_discard({"status": "ok", "verdict": "improved"}) is False


def test_advisory_outcomes_skip_malformed_jsonl_rows(tmp_path: Path) -> None:
    path = tmp_path / "artifacts" / "advisory" / "outcomes.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                json.dumps({"status": "ok", "packet_ids": ["packet-a"]}),
                "{not-json",
                json.dumps(["not", "an", "object"]),
                json.dumps({"status": "fail", "packet_ids": ["packet-b"]}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = load_advisory_outcomes(tmp_path)

    assert [row["status"] for row in rows] == ["ok", "fail"]


def test_trace_status_skips_malformed_jsonl_rows(tmp_path: Path) -> None:
    recorder = start_trace(tmp_path, kind="advisory_research", name="retry")
    recorder.event("citation_check", attributes={"used_note_ids": ["a"], "relevant_note_ids": ["b"]})
    recorder.finish()
    index_path = tmp_path / "artifacts" / "traces" / "index.jsonl"
    trace_path = recorder.path
    index_path.write_text(index_path.read_text(encoding="utf-8") + "{not-json\n", encoding="utf-8")
    trace_path.write_text(trace_path.read_text(encoding="utf-8") + "{not-json\n", encoding="utf-8")

    status = trace_status(tmp_path)

    assert status["trace_count"] == 1
    assert status["research_signals"]["research_retry_count"] == 1
    assert status["research_signals"]["citation_check_count"] == 1
    assert status["research_signals"]["citation_mismatch_count"] == 1


def test_trainer_state_recovers_from_malformed_or_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "trainer.json"

    path.write_text("{not-json", encoding="utf-8")
    assert read_state(path) == {}

    path.write_text(json.dumps(["not", "a", "state"]), encoding="utf-8")
    assert read_state(path) == {}


def test_trainer_state_write_preserves_existing_file_when_replace_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "trainer.json"
    path.write_text(json.dumps({"name": "writer", "last_status": "old"}) + "\n", encoding="utf-8")
    replace_calls: list[tuple[Path, Path]] = []

    def fail_replace(source: str | bytes | Path, target: str | bytes | Path) -> None:
        replace_calls.append((Path(source), Path(target)))
        raise OSError("simulated replace failure")

    monkeypatch.setattr(trainers.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        write_state(path, {"name": "writer", "last_status": "new"})

    assert json.loads(path.read_text(encoding="utf-8"))["last_status"] == "old"
    assert replace_calls and replace_calls[0][1] == path
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_trial_queue_recovers_from_malformed_or_non_object_json(tmp_path: Path) -> None:
    config_path = tmp_path / "spark-researcher.project.json"
    queue_path = tmp_path / "artifacts" / "frontier" / "queue.json"
    queue_path.parent.mkdir(parents=True)

    queue_path.write_text("{not-json", encoding="utf-8")
    assert load_queue_trials(config_path) == []

    queue_path.write_text(json.dumps(["not", "a", "queue"]), encoding="utf-8")
    assert load_queue_trials(config_path) == []


def test_trial_queue_append_preserves_existing_file_when_replace_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "spark-researcher.project.json"
    path = queue_path_for_config(config_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "candidate_trials": [
                    {
                        "candidate_id": "existing",
                        "mutations": {"learning_rate": "0.001"},
                        "commands": ["train"],
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    replace_calls: list[tuple[Path, Path]] = []

    def fail_replace(source: str | bytes | Path, target: str | bytes | Path) -> None:
        replace_calls.append((Path(source), Path(target)))
        raise OSError("simulated replace failure")

    monkeypatch.setattr(trial_queue.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        append_queue_trials(
            config_path,
            [
                CandidateTrial(
                    candidate_id="new",
                    mutations={"learning_rate": "0.002"},
                    commands=["train"],
                )
            ],
        )

    assert [trial.candidate_id for trial in load_queue_trials(config_path)] == ["existing"]
    assert replace_calls and replace_calls[0][1] == path
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_self_edit_queue_skips_malformed_and_non_object_proposals(tmp_path: Path) -> None:
    root = tmp_path / "artifacts" / "self-edit"
    (root / "bad").mkdir(parents=True)
    (root / "bad" / "proposal.json").write_text("{not-json", encoding="utf-8")
    (root / "list").mkdir()
    (root / "list" / "proposal.json").write_text(json.dumps(["not", "a", "proposal"]), encoding="utf-8")
    (root / "good").mkdir()
    (root / "good" / "proposal.json").write_text(
        json.dumps({"proposal_id": "proposal-good", "status": "queued", "blocked_changes": [], "prompt": "keep"}),
        encoding="utf-8",
    )

    rendered = obsidian.render_self_edit_queue(tmp_path)

    assert "proposal-good" in rendered
    assert "not-json" not in rendered


def test_build_vault_skips_malformed_and_non_object_trainer_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    trainer_dir = trainers_root(runtime_root)
    trainer_dir.mkdir(parents=True)
    (trainer_dir / "bad.json").write_text("{not-json", encoding="utf-8")
    (trainer_dir / "list.json").write_text(json.dumps(["not", "a", "trainer"]), encoding="utf-8")
    (trainer_dir / "good.json").write_text(json.dumps({"name": "writer", "last_status": "ok"}), encoding="utf-8")
    config_path = repo_root / "spark-researcher.project.json"
    config = ProjectConfig(
        project_name="demo",
        project_root=".",
        eval_metric="score",
        eval_goal="maximize",
        commands={"research": CommandSpec(args=["python", "-c", "print('ok')"])},
        metrics={"score": MetricSpec(pattern=r"score=(\d+)")},
    )

    monkeypatch.setattr(obsidian, "sync_memory", lambda *args, **kwargs: {"document_count": 0, "episode_count": 0, "kinds": {}, "outcomes": []})
    monkeypatch.setattr(
        obsidian,
        "build_beliefs",
        lambda *args, **kwargs: {
            "belief_count": 0,
            "durable_belief_count": 0,
            "provisional_belief_count": 0,
            "contradiction_count": 0,
        },
    )
    monkeypatch.setattr(obsidian, "packet_status", lambda *args, **kwargs: {"packet_count": 0, "kinds": {}})
    monkeypatch.setattr(obsidian, "ledger_summary", lambda *args, **kwargs: {"run_count": 0, "best_by_metric": {}, "recent": []})
    monkeypatch.setattr(obsidian, "trace_status", lambda *args, **kwargs: {"research_signals": {}})
    monkeypatch.setattr(obsidian, "pending_queue_count", lambda *args, **kwargs: 0)
    monkeypatch.setattr(obsidian, "load_working_memory", lambda *args, **kwargs: {})
    monkeypatch.setattr(obsidian, "load_episode_memory", lambda *args, **kwargs: [])
    monkeypatch.setattr(obsidian, "chip_has_hook", lambda *args, **kwargs: False)

    result = obsidian.build_vault(
        repo_root,
        runtime_root,
        config,
        config_path=config_path,
        governor_decision=memory_governor_decision(vault_authority_refs(repo_root, runtime_root, config_path)),
    )

    assert result["trainer_entries"] == 1
    trainer_state = (runtime_root / "obsidian-vault" / "05-Runtime" / "Trainer State.md").read_text(encoding="utf-8")
    assert "writer" in trainer_state


def test_trace_appends_use_locked_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    locked_paths: list[Path] = []

    @contextmanager
    def fake_lock(path: Path):
        locked_paths.append(path)
        yield

    monkeypatch.setattr("spark_researcher.runner.locked_file", fake_lock)

    recorder = start_trace(tmp_path, kind="advisory_research", name="retry")
    recorder.event("citation_check")

    assert locked_paths == [recorder.path, tmp_path / "artifacts" / "traces" / "index.jsonl", recorder.path]


def test_load_config_falls_back_for_invalid_optional_numeric_values(tmp_path: Path) -> None:
    config_path = tmp_path / "spark-researcher.project.json"
    config_path.write_text(
        json.dumps(
            {
                "project_name": "demo",
                "eval_metric": "score",
                "commands": {"research": {"args": ["python", "-c", "print('ok')"]}},
                "metrics": {"score": {"pattern": "score=(?P<value>\\d+)"}},
                "trainers": [
                    {
                        "name": "writer",
                        "examples_path": "examples.jsonl",
                        "compile_command": ["python", "compile.py"],
                        "min_examples": "many",
                        "recompile_every": None,
                        "max_examples": "all",
                    }
                ],
                "guardrails": {
                    "max_loop_iterations": "forever",
                    "consecutive_discard_limit": None,
                    "near_best_tolerance": "close",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.trainers[0].min_examples == 20
    assert config.trainers[0].recompile_every == 10
    assert config.trainers[0].max_examples == 96
    assert config.guardrails.max_loop_iterations == 8
    assert config.guardrails.consecutive_discard_limit == 3
    assert config.guardrails.near_best_tolerance == 0.03
