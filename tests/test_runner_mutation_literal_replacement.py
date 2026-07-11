from __future__ import annotations

from pathlib import Path

import spark_researcher.runner as runner
from spark_researcher.config import CommandSpec, MetricSpec, MutationSpec, ProjectConfig


def _learning_rate_config() -> ProjectConfig:
    """Config mirroring the real default ``learning_rate`` mutable parameter."""
    return ProjectConfig(
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
        ],
    )


def _workspace(tmp_path: Path) -> Path:
    # resolve() so apply_mutations' relative_to() works on macOS (/var vs /private/var).
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "config.json").write_text('{"learning_rate": 0.01}', encoding="utf-8")
    return workspace


def test_apply_mutations_value_with_group_reference_is_literal(tmp_path: Path) -> None:
    """A value of ``\\1`` must not be interpreted as a regex backreference.

    Before the fix the user-supplied value flowed into ``re.subn`` as the
    replacement template, so ``\\1`` raised ``re.error: invalid group reference``
    and crashed the run.
    """
    workspace = _workspace(tmp_path)

    applied = runner.apply_mutations(workspace, _learning_rate_config(), {"learning_rate": r"\1"})

    written = (workspace / "config.json").read_text(encoding="utf-8")
    assert written == r'{"learning_rate": \1}'
    assert applied == [{"name": "learning_rate", "value": r"\1", "file": "config.json"}]


def test_apply_mutations_value_with_backslash_escape_is_verbatim(tmp_path: Path) -> None:
    """A value like ``C:\\new`` must be written verbatim, not as a newline byte.

    Before the fix ``\\n`` inside the value was interpreted by ``re.subn`` and a
    literal newline character was injected into the config (silent corruption).
    """
    workspace = _workspace(tmp_path)

    runner.apply_mutations(workspace, _learning_rate_config(), {"learning_rate": "C:\\new"})

    written = (workspace / "config.json").read_text(encoding="utf-8")
    assert "\n" not in written
    assert written == r'{"learning_rate": C:\new}'


def test_apply_mutations_normal_numeric_value_still_works(tmp_path: Path) -> None:
    """Control: an ordinary numeric value is substituted exactly once."""
    workspace = _workspace(tmp_path)

    applied = runner.apply_mutations(workspace, _learning_rate_config(), {"learning_rate": "0.001"})

    written = (workspace / "config.json").read_text(encoding="utf-8")
    assert written == '{"learning_rate": 0.001}'
    assert applied == [{"name": "learning_rate", "value": "0.001", "file": "config.json"}]
