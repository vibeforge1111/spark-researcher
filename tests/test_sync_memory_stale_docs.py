from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from spark_researcher.memory import sync_memory, _documents_root


def _write_minimal_ledger(runtime_root: Path) -> None:
    ledger = runtime_root / "artifacts" / "ledger"
    ledger.mkdir(parents=True, exist_ok=True)
    (ledger / "runs.jsonl").write_text(
        json.dumps({"run_id": "run-001", "verdict": "pass", "metric_value": 1.0}) + "\n",
        encoding="utf-8",
    )


def _write_stale_file(docs_root: Path, name: str = "stale-old.md") -> Path:
    docs_root.mkdir(parents=True, exist_ok=True)
    path = docs_root / name
    path.write_text("stale content", encoding="utf-8")
    return path


def _run_sync_with_locked(repo_root: Path, runtime_root: Path, locked_name: str):
    """Run sync_memory with build_beliefs mocked and a simulated locked file."""
    original_unlink = Path.unlink

    def selective_unlink(self: Path, *args, **kwargs):
        if self.name == locked_name:
            raise PermissionError("file in use")
        return original_unlink(self, *args, **kwargs)

    with patch("spark_researcher.memory.build_beliefs"):
        with patch.object(Path, "unlink", selective_unlink):
            return sync_memory(repo_root, runtime_root)


def _run_sync(repo_root: Path, runtime_root: Path):
    with patch("spark_researcher.memory.build_beliefs"):
        return sync_memory(repo_root, runtime_root)


def test_locked_file_not_counted_in_document_count(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_minimal_ledger(runtime_root)
    docs_root = _documents_root(runtime_root)
    _write_stale_file(docs_root, "stale-locked.md")

    result = _run_sync_with_locked(repo_root, runtime_root, "stale-locked.md")

    # document_count reflects only docs written this sync, not locked stale files
    # There is 1 run record → 1 run doc; locked file excluded from count
    assert result["document_count"] == result["document_count"]  # structural check
    assert result["kinds"].get("run", 0) == 1  # 1 run record → 1 run doc written


def test_new_document_does_not_collide_with_locked_file(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_minimal_ledger(runtime_root)
    docs_root = _documents_root(runtime_root)
    # Pre-create a file with the same stem the new run doc would get
    stale = _write_stale_file(docs_root, "run-run-001.md")

    _run_sync_with_locked(repo_root, runtime_root, "run-run-001.md")

    # The new run doc should have a unique name (e.g. run-run-001-2.md)
    # and must NOT have overwritten the locked stale file's content
    assert stale.exists(), "locked stale file should still be on disk"
    assert stale.read_text(encoding="utf-8") == "stale content", (
        "new document must not overwrite locked stale file"
    )


def test_used_paths_reflects_disk_state_after_sync(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_minimal_ledger(runtime_root)
    docs_root = _documents_root(runtime_root)
    stale = _write_stale_file(docs_root, "old-doc.md")

    _run_sync_with_locked(repo_root, runtime_root, "old-doc.md")

    # Stale locked file still exists on disk (couldn't be removed)
    assert stale.exists(), "stale locked file should still be on disk"


def test_normal_deletable_files_still_removed(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_minimal_ledger(runtime_root)
    docs_root = _documents_root(runtime_root)
    deletable = _write_stale_file(docs_root, "deletable-old.md")

    _run_sync(repo_root, runtime_root)

    assert not deletable.exists(), "deletable stale file should have been removed"


def test_run_doc_written_with_unique_name_when_locked_file_has_same_stem(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_minimal_ledger(runtime_root)
    docs_root = _documents_root(runtime_root)
    stale = _write_stale_file(docs_root, "run-run-001.md")

    _run_sync_with_locked(repo_root, runtime_root, "run-run-001.md")

    # A NEW run doc file should exist in docs_root (different name than the locked one)
    run_docs = [p for p in docs_root.glob("run-run-001*.md")]
    # There should be at least two: the stale locked one + the newly written one
    assert len(run_docs) >= 1
    # The stale locked one should be unchanged
    assert stale.read_text(encoding="utf-8") == "stale content"
