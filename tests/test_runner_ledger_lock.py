from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from spark_researcher.runner import append_jsonl, locked_file, read_jsonl


def test_append_jsonl_uses_transient_lock_file(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "runs.jsonl"

    append_jsonl(path, {"run_id": "one", "metric_value": 1})
    append_jsonl(path, {"run_id": "two", "metric_value": 2})

    assert [row["run_id"] for row in read_jsonl(path)] == ["one", "two"]
    assert not path.with_name(path.name + ".lock").exists()


def test_locked_file_times_out_when_lock_is_held(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_name(path.name + ".lock").write_text("held-by-test", encoding="utf-8")

    try:
        with locked_file(path, timeout_seconds=0):
            raise AssertionError("lock should not be acquired")
    except TimeoutError as exc:
        assert "runs.jsonl.lock" in str(exc)
        assert "owner=held-by-test" in str(exc)


def test_locked_file_recovers_when_recorded_owner_is_dead(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "runs.jsonl"
    lock_path = path.with_name(path.name + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)

    for stale_ownership in ("424242", "424242:stale-token"):
        lock_path.write_text(stale_ownership, encoding="ascii")
        with patch("spark_researcher.runner.os.kill", side_effect=ProcessLookupError):
            with locked_file(path, timeout_seconds=0):
                ownership = lock_path.read_text(encoding="ascii")
                assert ownership.startswith(f"{os.getpid()}:")
                assert ownership != stale_ownership

        assert not lock_path.exists()
        assert not lock_path.with_name(lock_path.name + ".reclaim").exists()


def test_locked_file_preserves_live_owner(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "runs.jsonl"
    lock_path = path.with_name(path.name + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    live_ownership = f"{os.getpid()}:live-token"
    lock_path.write_text(live_ownership, encoding="ascii")

    try:
        with locked_file(path, timeout_seconds=0):
            raise AssertionError("live lock should not be acquired")
    except TimeoutError:
        pass

    assert lock_path.read_text(encoding="ascii") == live_ownership


def test_locked_file_revalidates_replaced_owner_before_recovery(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "runs.jsonl"
    lock_path = path.with_name(path.name + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("424242:stale-token", encoding="ascii")
    replacement = f"{os.getpid()}:replacement-token"

    def replace_owner_then_report_dead(_pid: int, _signal: int) -> None:
        lock_path.write_text(replacement, encoding="ascii")
        raise ProcessLookupError

    with patch("spark_researcher.runner.os.kill", side_effect=replace_owner_then_report_dead):
        try:
            with locked_file(path, timeout_seconds=0):
                raise AssertionError("replacement lock should not be acquired")
        except TimeoutError:
            pass

    assert lock_path.read_text(encoding="ascii") == replacement
    assert not lock_path.with_name(lock_path.name + ".reclaim").exists()


def test_locked_file_release_does_not_remove_same_pid_replacement(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "runs.jsonl"
    lock_path = path.with_name(path.name + ".lock")

    with locked_file(path):
        lock_path.unlink()
        lock_path.write_text(str(os.getpid()), encoding="ascii")

    assert lock_path.read_text(encoding="ascii") == str(os.getpid())


def test_read_jsonl_skips_malformed_rows(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"run_id":"one"}\nnot-json\n{"run_id":"two"}\n', encoding="utf-8")

    assert [row["run_id"] for row in read_jsonl(path)] == ["one", "two"]
