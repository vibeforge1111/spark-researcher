from __future__ import annotations

import json
import threading
from pathlib import Path

from spark_researcher.failures import failures_path, load_failures, record_failure


def test_load_failures_skips_malformed_jsonl_rows(tmp_path: Path) -> None:
    path = failures_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                json.dumps({"failure_type": "first", "summary": "kept"}),
                "{bad json",
                json.dumps(["not", "a", "dict"]),
                "",
                json.dumps({"failure_type": "second", "summary": "also kept"}),
            ]
        ),
        encoding="utf-8",
    )

    assert [row["failure_type"] for row in load_failures(tmp_path)] == ["first", "second"]


def test_record_failure_is_concurrency_safe(tmp_path: Path) -> None:
    """Concurrent record_failure writers must not interleave or drop rows.

    _append_jsonl serializes writers through runner.locked_file; under
    contention every payload should land as exactly one well-formed JSONL
    line and the transient lock file must be cleaned up afterwards.
    """
    worker_count = 16

    def writer(index: int) -> None:
        record_failure(
            tmp_path,
            failure_type=f"type-{index}",
            summary=f"summary {index}",
            surface="concurrency-test",
        )

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(worker_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    rows = load_failures(tmp_path)
    assert len(rows) == worker_count
    assert {row["failure_type"] for row in rows} == {f"type-{i}" for i in range(worker_count)}

    path = failures_path(tmp_path)
    # Every physical line must be valid JSON (no torn/interleaved writes).
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == worker_count
    for line in lines:
        json.loads(line)
    # The lock file is transient and removed once writers finish.
    assert not path.with_name(path.name + ".lock").exists()
