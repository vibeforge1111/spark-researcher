"""Path safety and lazy-sync regression tests for search_memory.

Covers:
- Path traversal stems must not escape docs_root
- Absolute-path stems must not escape docs_root
- Missing manifest triggers sync and returns safely (no data loss)
- Lazy sync skips sync when manifest present — existing docs preserved
- force_sync=True triggers sync even when manifest present
- Error messages must not expose private memory document body content
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from spark_researcher.memory import (
    _manifest_path,
    _unique_document_path,
    search_memory,
)
from spark_researcher.paths import memory_root

_PATCH_SYNC = "spark_researcher.memory.sync_memory"


def _empty_manifest(runtime_root: Path) -> dict:
    return {
        "backend": "local",
        "document_count": 0,
        "documents_root": str(memory_root(runtime_root) / "documents"),
        "source_runs": 0,
        "kinds": {},
        "memory_tiers": {},
        "outcomes": [],
        "self_edit_documents": [],
        "chip_documents": [],
        "working_memory": None,
        "episode_count": 0,
    }


# ---------------------------------------------------------------------------
# Path traversal / absolute-path containment
# ---------------------------------------------------------------------------


def test_traversal_stem_stays_in_docs_root(tmp_path: Path) -> None:
    """_unique_document_path must contain path-traversal stems inside docs_root."""
    docs_root = tmp_path / "documents"
    docs_root.mkdir()
    used: set[str] = set()

    result = _unique_document_path(docs_root, "../../etc/passwd", used)

    assert result.is_relative_to(docs_root), (
        f"traversal stem escaped docs_root: {result}"
    )
    assert ".." not in result.parts, (
        f"parent traversal component in result path parts: {result.parts}"
    )


def test_absolute_posix_stem_stays_in_docs_root(tmp_path: Path) -> None:
    """_unique_document_path must contain POSIX absolute-path stems inside docs_root."""
    docs_root = tmp_path / "documents"
    docs_root.mkdir()
    used: set[str] = set()

    result = _unique_document_path(docs_root, "/etc/passwd", used)

    assert result.is_relative_to(docs_root), (
        f"absolute POSIX stem escaped docs_root: {result}"
    )


def test_absolute_windows_stem_stays_in_docs_root(tmp_path: Path) -> None:
    """_unique_document_path must contain Windows absolute-path stems inside docs_root."""
    docs_root = tmp_path / "documents"
    docs_root.mkdir()
    used: set[str] = set()

    result = _unique_document_path(docs_root, r"C:\Windows\System32\cmd.exe", used)

    assert result.is_relative_to(docs_root), (
        f"Windows absolute stem escaped docs_root: {result}"
    )


# ---------------------------------------------------------------------------
# Missing memory path — safe failure without data loss
# ---------------------------------------------------------------------------


def test_missing_manifest_triggers_sync_returns_list(tmp_path: Path) -> None:
    """When manifest is absent search_memory must call sync and return a list safely."""
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    runtime_root.mkdir()

    assert not _manifest_path(runtime_root).exists(), "precondition: manifest absent"

    with patch(_PATCH_SYNC, return_value=_empty_manifest(runtime_root)) as mock_sync:
        results = search_memory(repo_root, runtime_root, "some query")

    assert mock_sync.called, "sync must be called when manifest is absent"
    assert isinstance(results, list), f"expected list, got {type(results)}"


def test_missing_runtime_root_no_private_content_in_error(tmp_path: Path) -> None:
    """Errors from missing runtime_root must not expose private memory content."""
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "nonexistent_runtime"
    repo_root.mkdir()

    private_token = "PRIVATE_MEMORY_BODY_XYZZY_99887766"
    returned_manifest = _empty_manifest(runtime_root)

    with patch(_PATCH_SYNC, return_value=returned_manifest):
        try:
            results = search_memory(repo_root, runtime_root, "some query")
            assert private_token not in str(results)
        except Exception as exc:
            assert private_token not in str(exc), (
                f"error message must not expose private token: {exc}"
            )


# ---------------------------------------------------------------------------
# Lazy sync: manifest present → sync skipped, existing docs preserved
# ---------------------------------------------------------------------------


def test_lazy_sync_skips_when_manifest_present(tmp_path: Path) -> None:
    """search_memory must skip sync when manifest exists — existing docs survive."""
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()

    mem_root = memory_root(runtime_root)
    docs_root = mem_root / "documents"
    docs_root.mkdir(parents=True)

    sentinel = docs_root / "existing-doc.md"
    sentinel.write_text("# Existing Document\nsafe content only\n", encoding="utf-8")

    manifest_path = _manifest_path(runtime_root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(_empty_manifest(runtime_root)), encoding="utf-8")

    with patch(_PATCH_SYNC) as mock_sync:
        search_memory(repo_root, runtime_root, "existing safe")

    mock_sync.assert_not_called()
    assert sentinel.exists(), "existing document must not be overwritten when manifest present"
    assert "safe content only" in sentinel.read_text(encoding="utf-8")


def test_lazy_sync_calls_sync_when_manifest_absent(tmp_path: Path) -> None:
    """search_memory must call sync when manifest is absent (first run in session)."""
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    runtime_root.mkdir()

    assert not _manifest_path(runtime_root).exists()

    with patch(_PATCH_SYNC, return_value=_empty_manifest(runtime_root)) as mock_sync:
        search_memory(repo_root, runtime_root, "first run query")

    assert mock_sync.called, "sync must be called when manifest is absent (first run in session)"


def test_force_sync_overrides_manifest_present(tmp_path: Path) -> None:
    """force_sync=True must trigger sync even when manifest is present."""
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()

    manifest_path = _manifest_path(runtime_root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(_empty_manifest(runtime_root)), encoding="utf-8")

    with patch(_PATCH_SYNC, return_value=_empty_manifest(runtime_root)) as mock_sync:
        search_memory(repo_root, runtime_root, "query", force_sync=True)

    mock_sync.assert_called_once()


# ---------------------------------------------------------------------------
# No raw memory body in error messages
# ---------------------------------------------------------------------------


def test_empty_query_error_does_not_expose_memory_body(tmp_path: Path) -> None:
    """RuntimeError for empty query must not contain private memory document content."""
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()

    private_content = "SECRET_MEMORY_BODY_DO_NOT_EXPOSE_4455667788"

    manifest_path = _manifest_path(runtime_root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(_empty_manifest(runtime_root)), encoding="utf-8")

    docs_root = memory_root(runtime_root) / "documents"
    docs_root.mkdir(parents=True, exist_ok=True)
    (docs_root / "private.md").write_text(
        f"# Private Document\n{private_content}\n", encoding="utf-8"
    )

    with pytest.raises(RuntimeError) as exc_info:
        search_memory(repo_root, runtime_root, "")

    assert private_content not in str(exc_info.value), (
        f"error message must not expose memory document body: {exc_info.value}"
    )
