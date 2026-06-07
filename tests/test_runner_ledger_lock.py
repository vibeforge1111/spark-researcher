from __future__ import annotations

from pathlib import Path

from spark_researcher.runner import append_jsonl, locked_file, read_jsonl


def test_append_jsonl_uses_transient_lock_file(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "runs.jsonl"

    append_jsonl(path, {"run_id": "one", "metric_value": 1})
    append_jsonl(path, {"run_id": "two", "metric_value": 2})

    assert [row["run_id"] for row in read_jsonl(path)] == ["one", "two"]
    assert not path.with_name(path.name + ".lock").exists()


def test_locked_file_recovers_from_stale_lock(tmp_path: Path) -> None:
    """Stale locks (invalid PID) are automatically recovered."""
    path = tmp_path / "ledger" / "runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_name(path.name + ".lock").write_text("held-by-test", encoding="utf-8")

    # Should recover from stale lock and succeed
    with locked_file(path, timeout_seconds=5):
        path.write_text('{"run_id": "one"}\n', encoding="utf-8")

    assert path.exists()
    assert not path.with_name(path.name + ".lock").exists()


def test_locked_file_times_out_when_lock_holder_is_alive(tmp_path: Path) -> None:
    """Timeout still occurs when lock holder process is still running."""
    import os
    path = tmp_path / "ledger" / "runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write current PID as lock holder (process is alive)
    path.with_name(path.name + ".lock").write_text(str(os.getpid()), encoding="utf-8")

    try:
        with locked_file(path, timeout_seconds=0):
            raise AssertionError("lock should not be acquired")
    except TimeoutError as exc:
        assert "runs.jsonl.lock" in str(exc)


def test_read_jsonl_skips_malformed_rows(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"run_id":"one"}\nnot-json\n{"run_id":"two"}\n', encoding="utf-8")

    assert [row["run_id"] for row in read_jsonl(path)] == ["one", "two"]
