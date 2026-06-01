from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import spark_researcher.cli as cli


def test_autoloop_rejects_non_positive_max_passes() -> None:
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["autoloop", "--command", "train", "--continuous", "--max-passes", "0"])


def test_run_rejects_unknown_candidate_id_before_baseline_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "spark-researcher.project.json"
    config_path.write_text("{}", encoding="utf-8")
    called_run_once = False

    monkeypatch.setattr(sys, "argv", ["spark-researcher", "run", "--config", str(config_path), "--command", "train", "--candidate-id", "missing"])
    monkeypatch.setattr(cli, "load_config", lambda path: object())
    monkeypatch.setattr(cli, "merged_candidate_trials", lambda path, *, config: [SimpleNamespace(candidate_id="known")])

    def fake_run_once(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal called_run_once
        called_run_once = True
        return {"ok": True}

    monkeypatch.setattr(cli, "run_once", fake_run_once)

    with pytest.raises(SystemExit, match="Candidate id 'missing' was not found"):
        cli.main()
    assert called_run_once is False
