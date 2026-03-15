from __future__ import annotations

from pathlib import Path

from spark_researcher.config import CommandSpec, MetricSpec, ProjectConfig, load_config, save_config
from spark_researcher.runner import copy_project_tree


def test_copy_project_tree_honors_nested_workspace_excludes(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    excluded_root = source_root / "localhost" / "paperclip-control-plane" / ".paperclip-data"
    excluded_root.mkdir(parents=True)
    (excluded_root / "config.json").write_text("{}", encoding="utf-8")
    keep_root = source_root / "localhost" / "paperclip-control-plane" / "src"
    keep_root.mkdir(parents=True)
    (keep_root / "app.py").write_text("print('ok')\n", encoding="utf-8")
    artifacts_root = source_root / "artifacts"
    artifacts_root.mkdir()
    (artifacts_root / "run.log").write_text("ignore me\n", encoding="utf-8")

    copy_project_tree(
        source_root,
        target_root,
        extra_excludes=["localhost/paperclip-control-plane/.paperclip-data"],
    )

    assert not (target_root / "localhost" / "paperclip-control-plane" / ".paperclip-data").exists()
    assert (target_root / "localhost" / "paperclip-control-plane" / "src" / "app.py").read_text(encoding="utf-8") == "print('ok')\n"
    assert not (target_root / "artifacts").exists()


def test_workspace_excludes_round_trip_through_config(tmp_path: Path) -> None:
    config_path = tmp_path / "spark-researcher.project.json"
    save_config(
        config_path,
        ProjectConfig(
            project_name="copy-test",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
            metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
            workspace_excludes=[
                "localhost/paperclip-control-plane/.paperclip-data",
                ".cache/generated",
            ],
        ),
    )

    loaded = load_config(config_path)

    assert loaded.workspace_excludes == [
        "localhost/paperclip-control-plane/.paperclip-data",
        ".cache/generated",
    ]
