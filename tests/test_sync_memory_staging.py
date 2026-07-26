from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from memory_governor import memory_governor_decision
from spark_researcher.memory import (
    _documents_root,
    _manifest_path,
    search_memory,
    sync_memory,
    sync_memory_authority_refs,
)


def _write_ledger(runtime_root: Path) -> None:
    path = runtime_root / "artifacts" / "ledger" / "runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"run_id": "new-run", "candidate_id": "candidate", "verdict": "pass"}) + "\n",
        encoding="utf-8",
    )


def _governor(repo_root: Path, runtime_root: Path):
    return memory_governor_decision(sync_memory_authority_refs(repo_root, runtime_root))


def test_failed_rebuild_preserves_previous_documents_and_manifest(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    _write_ledger(runtime_root)
    docs_root = _documents_root(runtime_root)
    docs_root.mkdir(parents=True)
    old_doc = docs_root / "old.md"
    old_doc.write_text("old snapshot remains available\n", encoding="utf-8")
    manifest_path = _manifest_path(runtime_root)
    old_manifest = json.dumps(
        {
            "backend": "local",
            "document_count": 1,
            "documents_root": str(docs_root),
            "documents": [
                {
                    "path": str(old_doc),
                    "kind": "run",
                    "title": "old",
                    "memory_tier": "raw_run",
                }
            ],
        },
        sort_keys=True,
    )
    manifest_path.write_text(old_manifest, encoding="utf-8")

    with patch("spark_researcher.memory.build_beliefs"):
        with patch("spark_researcher.memory.build_run_doc", side_effect=RuntimeError("synthetic rebuild failure")):
            with pytest.raises(RuntimeError, match="synthetic rebuild failure"):
                sync_memory(
                    repo_root,
                    runtime_root,
                    governor_decision=_governor(repo_root, runtime_root),
                )

    assert old_doc.read_text(encoding="utf-8") == "old snapshot remains available\n"
    assert manifest_path.read_text(encoding="utf-8") == old_manifest
    assert not list(manifest_path.parent.glob(".documents-stage-*"))


def test_locked_stale_document_is_not_searched_after_successful_sync(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    _write_ledger(runtime_root)
    docs_root = _documents_root(runtime_root)
    docs_root.mkdir(parents=True)
    stale = docs_root / "stale-locked.md"
    stale.write_text("PRIVATE_STALE_MEMORY_TOKEN\n", encoding="utf-8")
    original_unlink = Path.unlink

    def selective_unlink(self: Path, *args, **kwargs):
        if self == stale:
            raise PermissionError("file in use")
        return original_unlink(self, *args, **kwargs)

    with patch("spark_researcher.memory.build_beliefs"):
        with patch.object(Path, "unlink", selective_unlink):
            manifest = sync_memory(
                repo_root,
                runtime_root,
                governor_decision=_governor(repo_root, runtime_root),
            )

    assert stale.exists()
    assert manifest["documents"]
    assert all(Path(item["path"]).is_relative_to(docs_root) for item in manifest["documents"])
    assert str(stale) not in {item["path"] for item in manifest["documents"]}
    assert search_memory(repo_root, runtime_root, "PRIVATE_STALE_MEMORY_TOKEN") == []


def test_manifest_document_paths_cannot_escape_owned_memory_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    docs_root = _documents_root(runtime_root)
    docs_root.mkdir(parents=True)
    outside = docs_root.parent / "outside.md"
    outside.write_text("PRIVATE_OUTSIDE_MEMORY_TOKEN\n", encoding="utf-8")
    _manifest_path(runtime_root).write_text(
        json.dumps(
            {
                "backend": "local",
                "document_count": 1,
                "documents_root": str(docs_root.parent),
                "documents": [
                    {
                        "path": str(docs_root / ".." / outside.name),
                        "kind": "run",
                        "title": "outside",
                        "memory_tier": "raw_run",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert search_memory(repo_root, runtime_root, "PRIVATE_OUTSIDE_MEMORY_TOKEN") == []
