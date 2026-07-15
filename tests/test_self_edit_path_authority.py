from __future__ import annotations

import shutil
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from spark_researcher import self_edit
from spark_researcher.self_edit import _workspace_dir, expand_command, is_allowed_path


@pytest.mark.parametrize(
    "path_text",
    [
        "../src/allowed.py",
        "../../src/allowed.py",
        "src/../src/allowed.py",
        "/src/allowed.py",
        "C:/src/allowed.py",
        "//server/share/src/allowed.py",
    ],
)
def test_allowed_path_rejects_noncanonical_or_absolute_paths(path_text: str) -> None:
    assert is_allowed_path(path_text, ["src"]) is False


def test_allowed_path_accepts_canonical_relative_descendants() -> None:
    assert is_allowed_path("src", ["src"]) is True
    assert is_allowed_path("src/package/module.py", ["src"]) is True
    assert is_allowed_path("src\\package\\module.py", ["src"]) is True
    assert is_allowed_path("tests/test_module.py", ["src"]) is False


def test_workspace_dir_is_private_and_unique_for_the_same_proposal() -> None:
    first = _workspace_dir("proposal-safe")
    second = _workspace_dir("proposal-safe")
    try:
        assert first != second
        assert first.name == second.name == "workspace"
        assert first.parent.exists()
        assert second.parent.exists()
        assert first.exists() is False
        assert second.exists() is False
        assert stat.S_IMODE(first.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(second.parent.stat().st_mode) == 0o700
    finally:
        shutil.rmtree(first.parent, ignore_errors=True)
        shutil.rmtree(second.parent, ignore_errors=True)


def test_commit_paths_terminates_git_options_before_owned_paths(monkeypatch, tmp_path: Path) -> None:
    output_calls: list[tuple[str, ...]] = []

    def fake_git_output(repo_root: Path, *args: str) -> str:
        assert repo_root == tmp_path
        output_calls.append(args)
        return "abc123"

    monkeypatch.setattr(self_edit, "_git_output", fake_git_output)
    monkeypatch.setattr(
        self_edit,
        "_git",
        lambda repo_root, *args: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    assert self_edit._commit_paths(tmp_path, ["--intent.py"], "Apply reviewed proposal") == "abc123"
    assert output_calls[0] == ("add", "--", "--intent.py")


def test_expand_command_keeps_metacharacter_paths_inside_their_original_argv_tokens(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace ; $(touch nope)"
    request = tmp_path / "request & notes.md"
    last_message = tmp_path / "last | message.txt"

    command = expand_command(
        ["runner", "--workspace={workspace}", "Read {request}", "{last_message}"],
        workspace_root=workspace,
        request_path=request,
        last_message_path=last_message,
    )

    assert command == [
        "runner",
        f"--workspace={workspace}",
        f"Read {request}",
        str(last_message),
    ]
