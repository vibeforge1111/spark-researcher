from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import spark_researcher.presets as presets
from spark_researcher.presets import init_project, preset_names


def test_preset_names_include_toy() -> None:
    assert "toy" in preset_names()


def test_init_toy_project_writes_runnable_files(tmp_path: Path) -> None:
    target = tmp_path / "toy-demo"

    config_path = init_project(target, preset="toy", project_name="toy-demo")

    assert config_path == target / "spark-researcher.project.json"
    assert (target / "SPARK_RESEARCHER_PRESET.md").exists()
    assert (target / "train.py").exists()
    assert (target / "trainer.py").exists()
    assert (target / "config.json").exists()
    assert (target / "training_examples.jsonl").exists()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["project_root"] == "."
    assert payload["eval_metric"] == "val_loss"
    assert payload["eval_goal"] == "minimize"
    assert payload["metrics"]["val_loss"]["pattern"] == r"^val_loss:\s+([0-9.]+)$"
    assert {item["candidate_id"] for item in payload["candidate_trials"]} == {"baseline", "lr-0003", "wd-002"}
    assert {item["name"] for item in payload["mutable_parameters"]} == {"learning_rate", "weight_decay"}

    config_json = json.loads((target / "config.json").read_text(encoding="utf-8"))
    assert config_json == {"learning_rate": 0.001, "weight_decay": 0.01}

    preset_notes = (target / "SPARK_RESEARCHER_PRESET.md").read_text(encoding="utf-8")
    assert "runnable immediately" in preset_notes
    assert "spark-researcher autoloop --command train" in preset_notes


def test_init_project_does_not_publish_config_when_atomic_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "interrupted"

    def fail_replace(_source: str, _target: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(presets.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        init_project(target, preset="research", project_name="interrupted")

    assert not (target / "spark-researcher.project.json").exists()
    assert list(target.glob(".spark-researcher.project.json.*.tmp")) == []


def test_concurrent_init_publishes_one_consistent_project(tmp_path: Path) -> None:
    target = tmp_path / "concurrent"
    ready = threading.Barrier(2)

    def initialize(project_name: str) -> tuple[str, str]:
        ready.wait()
        try:
            init_project(target, preset="research", project_name=project_name)
        except FileExistsError:
            return "exists", project_name
        return "created", project_name

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(initialize, ["project-a", "project-b"]))

    assert sorted(status for status, _ in results) == ["created", "exists"]
    winner = next(name for status, name in results if status == "created")
    config = json.loads((target / "spark-researcher.project.json").read_text(encoding="utf-8"))
    readme = (target / "SPARK_RESEARCHER_PRESET.md").read_text(encoding="utf-8")
    assert config["project_name"] == winner
    assert winner in readme
