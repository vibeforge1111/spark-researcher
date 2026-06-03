from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spark_researcher.memory import _local_search_results


def _make_runtime_root(tmp_path: Path) -> Path:
    r = tmp_path / "runtime"
    r.mkdir()
    return r


def _make_docs_root(tmp_path: Path, files: dict[str, str]) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    for name, content in files.items():
        (docs / name).write_text(content, encoding="utf-8")
    return docs


def _search(runtime_root, docs_root, query):
    with patch("spark_researcher.memory.build_beliefs"):
        with patch("spark_researcher.memory._manifest_docs_by_path", return_value={}):
            return _local_search_results(
                runtime_root,
                docs_root,
                query,
                limit=10,
                repo_root=runtime_root,
                goal="minimize",
                config_path=None,
            )


def test_permission_error_on_locked_file_is_caught_and_skipped(tmp_path):
    docs = _make_docs_root(tmp_path, {
        "readable.md": "hello world",
        "locked.md": "hello world locked",
    })
    runtime_root = _make_runtime_root(tmp_path)

    original_read = Path.read_text

    def patched_read_text(self, *args, **kwargs):
        if self.name == "locked.md":
            raise PermissionError("file is locked by another process")
        return original_read(self, *args, **kwargs)

    with patch.object(Path, "read_text", patched_read_text):
        results = _search(runtime_root, docs, "hello")

    # Search completes without exception and returns readable file
    assert any(r["path"].endswith("readable.md") for r in results)


def test_search_continues_with_remaining_files_after_permission_error(tmp_path):
    docs = _make_docs_root(tmp_path, {
        "alpha.md": "unique_alpha_term",
        "locked.md": "unique_alpha_term locked",
        "beta.md": "unique_alpha_term",
    })
    runtime_root = _make_runtime_root(tmp_path)

    original_read = Path.read_text

    def patched_read_text(self, *args, **kwargs):
        if self.name == "locked.md":
            raise PermissionError("locked")
        return original_read(self, *args, **kwargs)

    with patch.object(Path, "read_text", patched_read_text):
        results = _search(runtime_root, docs, "unique_alpha_term")

    paths = [r["path"] for r in results]
    assert any(p.endswith("alpha.md") for p in paths)
    assert any(p.endswith("beta.md") for p in paths)
    assert not any(p.endswith("locked.md") for p in paths)


def test_file_not_found_still_caught(tmp_path):
    docs = _make_docs_root(tmp_path, {"present.md": "search_term_xyz"})
    runtime_root = _make_runtime_root(tmp_path)

    original_read = Path.read_text

    def patched_read_text(self, *args, **kwargs):
        if self.name == "missing.md":
            raise FileNotFoundError("gone")
        return original_read(self, *args, **kwargs)

    with patch.object(Path, "read_text", patched_read_text):
        results = _search(runtime_root, docs, "search_term_xyz")

    assert any(r["path"].endswith("present.md") for r in results)


def test_locked_file_content_not_in_results(tmp_path):
    docs = _make_docs_root(tmp_path, {
        "readable.md": "common_term",
        "locked.md": "common_term secret_only_in_locked",
    })
    runtime_root = _make_runtime_root(tmp_path)

    original_read = Path.read_text

    def patched_read_text(self, *args, **kwargs):
        if self.name == "locked.md":
            raise PermissionError("locked")
        return original_read(self, *args, **kwargs)

    with patch.object(Path, "read_text", patched_read_text):
        results = _search(runtime_root, docs, "secret_only_in_locked")

    assert len(results) == 0


def test_normal_readable_files_still_returned(tmp_path):
    docs = _make_docs_root(tmp_path, {
        "doc1.md": "query_word content here",
        "doc2.md": "query_word more content",
    })
    runtime_root = _make_runtime_root(tmp_path)

    results = _search(runtime_root, docs, "query_word")
    assert len(results) == 2
