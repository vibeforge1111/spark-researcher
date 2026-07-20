from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from memory_governor import memory_governor_decision
from spark_researcher.memory import (
    _episode_memory_state,
    load_episode_memory,
    memory_status,
    sync_memory,
    sync_memory_authority_refs,
)


def _write_episode_lines(runtime_root: Path, *lines: str) -> Path:
    path = runtime_root / "artifacts" / "memory" / "episodes.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_corrupt_episode_lines_preserve_valid_rows_and_report_partial_state(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    _write_episode_lines(
        runtime_root,
        json.dumps({"title": "first", "status": "done"}),
        "{PRIVATE_CORRUPT_EPISODE_BODY",
        json.dumps({"title": "second", "status": "working"}),
        json.dumps(["not", "an", "episode"]),
    )

    assert [row["title"] for row in load_episode_memory(runtime_root)] == ["second", "first"]

    state = _episode_memory_state(runtime_root)
    assert state == {
        "status": "partial",
        "valid_line_count": 2,
        "invalid_line_count": 2,
        "rows": [
            {"title": "second", "status": "working"},
            {"title": "first", "status": "done"},
        ],
    }
    assert "PRIVATE_CORRUPT_EPISODE_BODY" not in json.dumps(state)


def test_episode_state_distinguishes_empty_ready_and_invalid_files(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    assert _episode_memory_state(runtime_root) == {
        "status": "empty",
        "valid_line_count": 0,
        "invalid_line_count": 0,
        "rows": [],
    }

    _write_episode_lines(runtime_root, json.dumps({"title": "ready"}), "", "{}")
    assert _episode_memory_state(runtime_root)["status"] == "ready"

    _write_episode_lines(runtime_root, "{broken", json.dumps(["wrong-shape"]))
    assert _episode_memory_state(runtime_root) == {
        "status": "invalid",
        "valid_line_count": 0,
        "invalid_line_count": 2,
        "rows": [],
    }


def test_memory_surfaces_report_partial_episode_state_without_raw_corrupt_content(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_episode_lines(
        runtime_root,
        json.dumps({"title": "kept", "summary": "safe summary", "status": "done"}),
        "{PRIVATE_CORRUPT_EPISODE_BODY",
    )

    before_sync = memory_status(repo_root, runtime_root)
    assert before_sync["episode_state"] == "partial"
    assert before_sync["episode_invalid_line_count"] == 1

    governor = memory_governor_decision(sync_memory_authority_refs(repo_root, runtime_root))
    with patch("spark_researcher.memory.build_beliefs"):
        manifest = sync_memory(repo_root, runtime_root, governor_decision=governor)

    assert manifest["episode_count"] == 1
    assert manifest["episode_state"] == "partial"
    assert manifest["episode_invalid_line_count"] == 1
    assert "PRIVATE_CORRUPT_EPISODE_BODY" not in json.dumps(manifest)

    after_sync = memory_status(repo_root, runtime_root)
    assert after_sync["episode_state"] == "partial"
    assert after_sync["episode_invalid_line_count"] == 1
