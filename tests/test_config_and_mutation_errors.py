from __future__ import annotations

import json
from pathlib import Path

import pytest

from spark_researcher.config import CommandSpec, MetricSpec, MutationSpec, ProjectConfig, load_config, public_config_path
from spark_researcher.runner import apply_mutations


def _config_payload() -> dict[str, object]:
    return {
        "project_name": "demo",
        "eval_metric": "score",
        "commands": {"train": {"args": ["python", "-c", "print('score=1')"]}},
        "metrics": {"score": {"pattern": r"score=(\d+)"}},
    }


def _write_config(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


@pytest.mark.parametrize("missing_key", ["project_name", "eval_metric", "commands", "metrics"])
def test_load_config_names_missing_required_top_level_key(tmp_path: Path, missing_key: str) -> None:
    config_path = tmp_path / "spark-researcher.project.json"
    payload = _config_payload()
    del payload[missing_key]
    _write_config(config_path, payload)

    with pytest.raises(ValueError) as error:
        load_config(config_path)

    message = str(error.value)
    assert missing_key in message
    assert public_config_path(config_path) in message


def test_load_config_rejects_non_object_root_with_public_path(tmp_path: Path) -> None:
    config_path = tmp_path / "spark-researcher.project.json"
    _write_config(config_path, [])

    with pytest.raises(ValueError) as error:
        load_config(config_path)

    message = str(error.value)
    assert "JSON object" in message
    assert public_config_path(config_path) in message


@pytest.mark.parametrize(
    ("section", "entry", "missing_field"),
    [
        ("mutable_parameters", {"name": "rate", "file": "config.json", "pattern": "rate=1"}, "template"),
        ("trainers", {"name": "writer"}, "examples_path"),
    ],
)
def test_load_config_names_missing_nested_field(
    tmp_path: Path,
    section: str,
    entry: dict[str, str],
    missing_field: str,
) -> None:
    config_path = tmp_path / "spark-researcher.project.json"
    payload = _config_payload()
    payload[section] = [entry]
    _write_config(config_path, payload)

    with pytest.raises(ValueError) as error:
        load_config(config_path)

    message = str(error.value)
    assert f"{section}[0]" in message
    assert missing_field in message
    assert public_config_path(config_path) in message


@pytest.mark.parametrize("section", ["mutable_parameters", "trainers"])
def test_load_config_rejects_non_object_nested_entry(tmp_path: Path, section: str) -> None:
    config_path = tmp_path / "spark-researcher.project.json"
    payload = _config_payload()
    payload[section] = ["not-an-object"]
    _write_config(config_path, payload)

    with pytest.raises(ValueError) as error:
        load_config(config_path)

    message = str(error.value)
    assert f"{section}[0]" in message
    assert "JSON object" in message


def _mutation_config(*, file: str = "config.txt", pattern: str = r"rate=[^\n]+", template: str = "rate={value}") -> ProjectConfig:
    return ProjectConfig(
        project_name="demo",
        project_root=".",
        eval_metric="score",
        eval_goal="maximize",
        commands={"train": CommandSpec(args=["python", "-c", "print('score=1')"])},
        metrics={"score": MetricSpec(pattern=r"score=(\d+)")},
        mutable_parameters=[MutationSpec(name="rate", file=file, pattern=pattern, template=template)],
    )


@pytest.mark.parametrize("value", [r"\1", "C:\\new"])
def test_apply_mutations_treats_value_as_literal_replacement(tmp_path: Path, value: str) -> None:
    workspace = tmp_path.resolve()
    target = workspace / "config.txt"
    target.write_text("rate=old\n", encoding="utf-8")

    apply_mutations(workspace, _mutation_config(), {"rate": value})

    assert target.read_text(encoding="utf-8") == f"rate={value}\n"


def test_apply_mutations_does_not_evaluate_format_gadgets(tmp_path: Path) -> None:
    workspace = tmp_path.resolve()
    target = workspace / "config.txt"
    target.write_text("rate=old\n", encoding="utf-8")
    gadget = "{value.__class__.__name__}"

    apply_mutations(workspace, _mutation_config(template=f"rate={gadget}"), {"rate": "secret"})

    assert target.read_text(encoding="utf-8") == f"rate={gadget}\n"


def test_apply_mutations_names_missing_target_without_absolute_path(tmp_path: Path) -> None:
    workspace = tmp_path.resolve()

    with pytest.raises(RuntimeError) as error:
        apply_mutations(workspace, _mutation_config(file="missing.txt"), {"rate": "new"})

    message = str(error.value)
    assert "missing.txt" in message
    assert "missing" in message.lower()
    assert str(workspace) not in message


def test_apply_mutations_names_invalid_pattern(tmp_path: Path) -> None:
    workspace = tmp_path.resolve()
    (workspace / "config.txt").write_text("rate=old\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as error:
        apply_mutations(workspace, _mutation_config(pattern="["), {"rate": "new"})

    message = str(error.value)
    assert "invalid" in message.lower()
    assert "[" in message


def test_apply_mutations_names_pattern_that_did_not_match(tmp_path: Path) -> None:
    workspace = tmp_path.resolve()
    (workspace / "config.txt").write_text("rate=old\n", encoding="utf-8")
    pattern = r"missing=.+"

    with pytest.raises(RuntimeError) as error:
        apply_mutations(workspace, _mutation_config(pattern=pattern), {"rate": "new"})

    message = str(error.value)
    assert "did not match" in message
    assert pattern in message
    assert "config.txt" in message
    assert str(workspace) not in message
