"""Regression test for the redacted git error in self_edit._git_output.

Unlike a tautological re-implementation, this exercises the real
``_git_output`` helper against a directory that is not a git repository so
``git`` exits non-zero and writes diagnostic stderr that historically leaked
into the raised ``RuntimeError``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from spark_researcher.self_edit import _git, _git_output


def test_git_output_error_is_generic_and_omits_stderr(tmp_path: Path) -> None:
    # Not a git repo, so `git status` exits non-zero with stderr that mentions
    # the path and "not a git repository".
    probe = _git(tmp_path, "status")
    assert probe.returncode != 0
    assert probe.stderr.strip()  # git really did emit diagnostic stderr

    with pytest.raises(RuntimeError) as excinfo:
        _git_output(tmp_path, "status")

    message = str(excinfo.value)
    assert message == "git status failed"
    # The raw stderr (and the absolute repo path it embeds) must not leak.
    assert probe.stderr.strip() not in message
    assert str(tmp_path) not in message


def test_git_output_returns_stdout_on_success(tmp_path: Path) -> None:
    init = _git(tmp_path, "init")
    if init.returncode != 0:  # pragma: no cover - git unavailable in env
        pytest.skip("git not available")
    # A succeeding command returns its trimmed stdout.
    out = _git_output(tmp_path, "rev-parse", "--is-inside-work-tree")
    assert out == "true"
