from __future__ import annotations

from pathlib import Path

from spark_researcher.paths import resolve_runtime_root


def test_runtime_root_prefers_trimmed_researcher_home(
    monkeypatch,
    tmp_path: Path,
) -> None:
    home_root = tmp_path / "home-root"
    cli_root = tmp_path / "cli-root"
    monkeypatch.setenv("SPARK_RESEARCHER_HOME", f"  {home_root}  ")
    monkeypatch.setenv("SPARK_RESEARCHER_ROOT", str(cli_root))

    assert resolve_runtime_root(tmp_path / "spark-researcher.project.json") == home_root.resolve()


def test_runtime_root_accepts_spark_cli_alias_when_home_is_blank(
    monkeypatch,
    tmp_path: Path,
) -> None:
    cli_root = tmp_path / "cli-root"
    monkeypatch.setenv("SPARK_RESEARCHER_HOME", "   ")
    monkeypatch.setenv("SPARK_RESEARCHER_ROOT", f"  {cli_root}  ")

    assert resolve_runtime_root(tmp_path / "spark-researcher.project.json") == cli_root.resolve()


def test_runtime_root_falls_back_when_both_overrides_are_blank(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "project" / "spark-researcher.project.json"
    monkeypatch.setenv("SPARK_RESEARCHER_HOME", "   ")
    monkeypatch.setenv("SPARK_RESEARCHER_ROOT", "\t")

    assert resolve_runtime_root(config_path) == config_path.parent.resolve()
