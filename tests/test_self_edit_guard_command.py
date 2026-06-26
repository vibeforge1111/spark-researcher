"""guard_command must block a fragment even when it is split across argv tokens.

The earlier guard only substring-matched the space-joined command, so blocking
"rm -rf" could be trivially evaded by passing the flag as separate argv tokens
(["rm", "-rf"] or ["rm", "-", "r", "f"]). guard_command now also compares the
whitespace-stripped command against the whitespace-stripped fragment.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from spark_researcher.self_edit import guard_command

BLOCKED = ["rm -rf", "sudo"]


def _is_blocked(parts: list[str]) -> bool:
    try:
        guard_command(parts, BLOCKED)
    except RuntimeError:
        return True
    return False


def test_blocks_literal_fragment() -> None:
    assert _is_blocked(["rm -rf", "/"])
    assert _is_blocked(["bash", "-c", "rm -rf /tmp/x"])


def test_blocks_fragment_split_into_two_tokens() -> None:
    assert _is_blocked(["rm", "-rf", "/"])


def test_blocks_fragment_split_into_character_tokens() -> None:
    assert _is_blocked(["rm", "-", "r", "f"])


def test_blocks_single_token_fragment() -> None:
    assert _is_blocked(["sudo", "make", "install"])


def test_allows_unrelated_command() -> None:
    assert not _is_blocked(["python", "-m", "pytest"])
    # "format" contains no blocked fragment; ensure no false positive.
    assert not _is_blocked(["git", "status"])


def test_empty_fragment_does_not_match_everything() -> None:
    # A stray empty fragment must not block every command.
    try:
        guard_command(["echo", "hi"], [""])
    except RuntimeError:  # pragma: no cover
        pytest.fail("empty fragment should not block an arbitrary command")
