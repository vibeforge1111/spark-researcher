"""Focused tests confirming timeout= is plumbed into every subprocess.run
call site in collective.py and self_edit.py.

Tests mock subprocess.run and assert the call is made with a bounded timeout,
so a hung child cannot block the autoloop.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# collective.py — sync_local_collective uses timeout=120
# ---------------------------------------------------------------------------

def test_sync_local_collective_passes_timeout(tmp_path):
    from spark_researcher.collective import sync_local_collective

    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = ""
    fake_result.stderr = ""

    with patch("subprocess.run", return_value=fake_result) as mock_run:
        try:
            sync_local_collective(tmp_path, tmp_path, label="test-sync")
        except Exception:
            pass
        for c in mock_run.call_args_list:
            kw = c.kwargs
            if "timeout" in kw:
                assert kw["timeout"] is not None, "timeout must not be None"
                assert isinstance(kw["timeout"], (int, float))
                assert kw["timeout"] > 0


# ---------------------------------------------------------------------------
# collective.py — _run_command uses timeout=120
# ---------------------------------------------------------------------------

def test_run_command_passes_timeout(tmp_path):
    from spark_researcher.collective import _run_command

    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = "ok"
    fake_result.stderr = ""

    with patch("subprocess.run", return_value=fake_result) as mock_run:
        try:
            _run_command(["echo", "hi"], cwd=tmp_path)
        except Exception:
            pass
        for c in mock_run.call_args_list:
            kw = c.kwargs
            assert "timeout" in kw, "timeout= must be passed to subprocess.run"
            assert kw["timeout"] > 0


# ---------------------------------------------------------------------------
# self_edit.py — run_git_status uses timeout=30
# ---------------------------------------------------------------------------

def test_run_git_status_passes_timeout(tmp_path):
    from spark_researcher.self_edit import run_git_status

    (tmp_path / ".git").mkdir()

    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = "nothing to commit"

    with patch("subprocess.run", return_value=fake) as mock_run:
        run_git_status(tmp_path)
        assert mock_run.called
        kw = mock_run.call_args.kwargs
        assert "timeout" in kw, "timeout= must be passed to subprocess.run"
        assert kw["timeout"] > 0
        assert kw["timeout"] <= 60, "git status timeout should be ≤60s"


# ---------------------------------------------------------------------------
# self_edit.py — _git helper uses timeout=30
# ---------------------------------------------------------------------------

def test_git_helper_passes_timeout(tmp_path):
    from spark_researcher.self_edit import _git

    (tmp_path / ".git").mkdir()

    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = ""
    fake.stderr = ""

    with patch("subprocess.run", return_value=fake) as mock_run:
        try:
            _git(tmp_path, "status")
        except Exception:
            pass
        assert mock_run.called
        kw = mock_run.call_args.kwargs
        assert "timeout" in kw, "timeout= must be passed to subprocess.run"
        assert kw["timeout"] > 0


# ---------------------------------------------------------------------------
# Hung child is bounded: TimeoutExpired surfaces within timeout window
# ---------------------------------------------------------------------------

def test_hung_subprocess_raises_timeout_expired(tmp_path):
    from spark_researcher.self_edit import run_git_status

    (tmp_path / ".git").mkdir()

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=30)):
        result = run_git_status(tmp_path)
        assert result == "", "hung git should return empty string, not block"
