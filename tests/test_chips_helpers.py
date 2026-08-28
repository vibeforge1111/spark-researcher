from __future__ import annotations

from pathlib import Path

import pytest

from spark_researcher.chips import (
    _command_parts,
    _looks_like_local_command_path,
    _normalize_relative_paths,
    _validate_hook_response,
)


def test_command_parts_coerces_numeric_segments() -> None:
    assert _command_parts(["python", "script.py", 42]) == ["python", "script.py", "42"]


def test_command_parts_rejects_non_list_input() -> None:
    with pytest.raises(RuntimeError, match="arrays of command parts"):
        _command_parts("python script.py")


def test_looks_like_local_command_path_recognizes_slashes() -> None:
    assert _looks_like_local_command_path("scripts/run.sh") is True
    assert _looks_like_local_command_path("./local") is True


def test_looks_like_local_command_path_ignores_flags_and_bare_tokens() -> None:
    assert _looks_like_local_command_path("--name") is False
    assert _looks_like_local_command_path("") is False
    assert _looks_like_local_command_path("python") is False


def test_looks_like_local_command_path_detects_file_suffix() -> None:
    assert _looks_like_local_command_path("entry.py") is True
    assert _looks_like_local_command_path("entry.sh") is True


def test_normalize_relative_paths_handles_separators_and_blanks() -> None:
    result = _normalize_relative_paths([
        "Docs\\Notes",
        "/foo/",
        ".",
        "   ",
        "src/Lib",
    ])
    assert result == {"docs/notes", "foo", "src/lib"}


def test_validate_hook_response_evaluate_accepts_well_formed_payload() -> None:
    _validate_hook_response(
        "evaluate",
        {"returncode": 0, "stdout": "ok", "stderr": "", "metrics": {"score": 0.5}, "result": {"summary": "fine"}},
    )


def test_validate_hook_response_evaluate_rejects_non_int_returncode() -> None:
    with pytest.raises(RuntimeError, match="returncode"):
        _validate_hook_response("evaluate", {"returncode": "0"})


def test_validate_hook_response_suggest_requires_candidate_id() -> None:
    with pytest.raises(RuntimeError, match="candidate_id"):
        _validate_hook_response("suggest", {"suggestions": [{"mutations": {}}]})


def test_validate_hook_response_suggest_rejects_non_dict_suggestion() -> None:
    with pytest.raises(RuntimeError, match="must be an object"):
        _validate_hook_response("suggest", {"suggestions": ["not-an-object"]})


def test_validate_hook_response_packets_requires_non_empty_strings() -> None:
    with pytest.raises(RuntimeError, match="must be a non-empty string"):
        _validate_hook_response(
            "packets",
            {"documents": [{"kind": "belief", "title": "", "content": "ok"}]},
        )


def test_validate_hook_response_watchtower_requires_pages_array() -> None:
    with pytest.raises(RuntimeError, match="array `pages`"):
        _validate_hook_response("watchtower", {"pages": "nope"})
