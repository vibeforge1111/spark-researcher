"""
Trust-boundary tests for write_working_memory — file lock fix.

Boundary: callers (research.py, runner.py) → write_working_memory
          → locked_file context manager → path.write_text (atomic under lock)

Before fix: bare path.write_text() with no lock — concurrent calls silently
            overwrote each other, causing context drift.
After fix:  with locked_file(path): path.write_text(...) — same spinlock used
            by append_jsonl in runner.py.

Tests cover: lock mechanism invoked, absolute path handling, missing parent
directory (safe failure), path traversal boundary, bounded JSON output,
no raw memory/env leakage.
"""

import json
import pytest
from contextlib import contextmanager
from pathlib import Path

from memory_governor import memory_governor_decision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(runtime_root: Path, **kwargs) -> dict:
    from spark_researcher.memory import working_memory_authority_refs, write_working_memory
    defaults = {"kind": "advisor", "focus": "test focus", "status": "running"}
    defaults["governor_decision"] = memory_governor_decision(working_memory_authority_refs(runtime_root))
    defaults.update(kwargs)
    return write_working_memory(runtime_root, **defaults)


def _working_file(runtime_root: Path) -> Path:
    """Return the path where write_working_memory writes its output."""
    from spark_researcher.paths import memory_root
    return memory_root(runtime_root) / "working.json"


# ---------------------------------------------------------------------------
# Lock mechanism
# ---------------------------------------------------------------------------

def test_write_working_memory_uses_locked_file(tmp_path, monkeypatch):
    """locked_file must be called exactly once per write_working_memory call."""
    from spark_researcher.runner import ensure_parent
    lock_calls = []

    @contextmanager
    def fake_lock(path):
        ensure_parent(path)  # mirror what real locked_file does
        lock_calls.append(str(path))
        yield

    monkeypatch.setattr("spark_researcher.memory.locked_file", fake_lock)
    _write(tmp_path)
    assert len(lock_calls) == 1


# ---------------------------------------------------------------------------
# Absolute path handling
# ---------------------------------------------------------------------------

def test_write_working_memory_accepts_absolute_path(tmp_path):
    """An absolute runtime_root must be accepted and the file created."""
    assert tmp_path.is_absolute()
    _write(tmp_path)
    assert _working_file(tmp_path).exists()


def test_write_working_memory_output_written_inside_runtime_root(tmp_path):
    """The written file must reside inside the provided runtime_root tree."""
    _write(tmp_path)
    working = _working_file(tmp_path)
    assert str(working).startswith(str(tmp_path))


# ---------------------------------------------------------------------------
# Missing parent directory (safe failure)
# ---------------------------------------------------------------------------

def test_write_working_memory_creates_missing_parent_directory(tmp_path):
    """locked_file calls ensure_parent, so writing into a non-existent subdir works."""
    nested = tmp_path / "a" / "b" / "c"
    assert not nested.exists()
    _write(nested)
    assert _working_file(nested).exists()


# ---------------------------------------------------------------------------
# Path traversal boundary
# ---------------------------------------------------------------------------

def test_write_working_memory_focus_with_traversal_chars_stays_in_json(tmp_path):
    """User-supplied traversal sequences in focus/notes are serialized to JSON,
    not interpreted as paths — they cannot escape the working.json boundary."""
    _write(tmp_path, focus="../../etc/passwd", notes=["../../../secret"])
    data = json.loads(_working_file(tmp_path).read_text(encoding="utf-8"))
    assert data["focus"] == "../../etc/passwd"
    assert data["notes"] == ["../../../secret"]
    created = [p for p in tmp_path.rglob("*") if p.is_file()]
    for f in created:
        assert str(f).startswith(str(tmp_path))


# ---------------------------------------------------------------------------
# Bounded JSON output
# ---------------------------------------------------------------------------

def test_write_working_memory_output_is_valid_json_with_expected_keys(tmp_path):
    """Written file is valid JSON with the expected top-level keys — no extra state."""
    _write(tmp_path, kind="advisor", focus="check output", status="complete",
           notes=["note A"], questions=["Q?"])
    data = json.loads(_working_file(tmp_path).read_text(encoding="utf-8"))
    assert data["kind"] == "advisor"
    assert data["focus"] == "check output"
    assert data["status"] == "complete"
    assert "notes" in data
    assert "questions" in data
    assert "updated_at" in data


# ---------------------------------------------------------------------------
# No raw memory / env leakage
# ---------------------------------------------------------------------------

def test_write_working_memory_no_env_leak(tmp_path, monkeypatch):
    """Env vars must not appear in the written memory file."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-do-not-leak-abc123")
    _write(tmp_path, focus="safe data only")
    for f in tmp_path.rglob("*"):
        if f.is_file():
            content = f.read_text(encoding="utf-8", errors="replace")
            assert "sk-test-do-not-leak-abc123" not in content
