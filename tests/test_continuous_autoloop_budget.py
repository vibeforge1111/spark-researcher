from __future__ import annotations

from pathlib import Path

from spark_researcher.candidates import (
    _continuous_status_path,
    _load_continuous_status,
    _write_continuous_status,
    run_continuous_autoloop,
)
from spark_researcher.config import CommandSpec, MetricSpec, ProjectConfig, save_config


def _write_config(root: Path) -> Path:
    config_path = root / "spark-researcher.project.json"
    save_config(
        config_path,
        ProjectConfig(
            project_name="budget-test",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
            metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
        ),
    )
    return config_path


def test_continuous_autoloop_stops_at_max_passes(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)

    monkeypatch.setattr(
        "spark_researcher.candidates.run_autoloop",
        lambda *args, **kwargs: {"round_count": 1, "history": [{"run_count": 0, "appended": {"appended_count": 0}}]},
    )
    monkeypatch.setattr("spark_researcher.candidates.time.sleep", lambda seconds: None)

    packet = run_continuous_autoloop(config_path, "research", max_passes=1, pause_seconds=1)

    assert packet["stopped"] == "max_passes"
    assert packet["pass_count"] == 1


def test_continuous_autoloop_stop_file_kills_before_work(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    stop_file = tmp_path / "STOP"
    stop_file.write_text("stop\n", encoding="utf-8")

    def fail_run(*args, **kwargs):
        raise AssertionError("stop file should prevent loop work")

    monkeypatch.setattr("spark_researcher.candidates.run_autoloop", fail_run)

    packet = run_continuous_autoloop(config_path, "research", stop_file=stop_file)

    assert packet["stopped"] == "stop_file"
    assert packet["pass_count"] == 0
    assert packet["stop_file"] == str(stop_file)


def test_continuous_status_uses_transient_lock_file(tmp_path: Path) -> None:
    _write_continuous_status(tmp_path, {"current_pass": {"status": "running"}})

    assert _load_continuous_status(tmp_path)["current_pass"]["status"] == "running"
    assert not _continuous_status_path(tmp_path).with_name("continuous_status.json.lock").exists()


def test_continuous_status_malformed_json_returns_empty(tmp_path: Path) -> None:
    path = _continuous_status_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")

    assert _load_continuous_status(tmp_path) == {}
