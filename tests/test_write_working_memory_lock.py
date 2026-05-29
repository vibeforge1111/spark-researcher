import json
import pytest
from pathlib import Path
from contextlib import contextmanager


def test_write_working_memory_uses_locked_file(tmp_path, monkeypatch):
    lock_calls = []

    @contextmanager
    def fake_lock(path):
        lock_calls.append(str(path))
        yield

    monkeypatch.setattr("spark_researcher.memory.locked_file", fake_lock)
    from spark_researcher.memory import write_working_memory
    write_working_memory(tmp_path, {"key": "value"})
    assert len(lock_calls) == 1


def test_write_working_memory_accepts_absolute_path(tmp_path):
    assert tmp_path.is_absolute()
    from spark_researcher.memory import write_working_memory
    write_working_memory(tmp_path, {"data": "test"})


def test_write_working_memory_creates_file(tmp_path):
    from spark_researcher.memory import write_working_memory
    write_working_memory(tmp_path, {"hello": "world"})
    files = list(tmp_path.rglob("*.jsonl")) + list(tmp_path.rglob("*.json"))
    assert len(files) >= 1


def test_write_working_memory_missing_path_safe(tmp_path):
    from spark_researcher.memory import write_working_memory
    missing = tmp_path / "does_not_exist" / "subdir"
    try:
        write_working_memory(missing, {"k": "v"})
    except (FileNotFoundError, OSError):
        pass
    except Exception as e:
        pytest.fail(f"Unexpected exception type: {type(e).__name__}: {e}")


def test_write_working_memory_no_env_leak(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-do-not-leak")
    from spark_researcher.memory import write_working_memory
    write_working_memory(tmp_path, {"entry": "safe data"})
    for f in tmp_path.rglob("*"):
        if f.is_file():
            content = f.read_text(encoding="utf-8", errors="replace")
            assert "sk-test-do-not-leak" not in content