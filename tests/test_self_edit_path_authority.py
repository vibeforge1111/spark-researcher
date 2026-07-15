from __future__ import annotations

import shutil
import stat

import pytest

from spark_researcher.self_edit import _workspace_dir, is_allowed_path


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
