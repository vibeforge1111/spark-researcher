from __future__ import annotations

import json
from pathlib import Path

from spark_researcher.memory import (
    load_episode_memory,
    load_working_memory,
    record_episode,
    write_working_memory,
)


def test_write_working_memory_persists_normalized_payload(tmp_path: Path) -> None:
    payload = write_working_memory(
        tmp_path,
        kind="advisory",
        focus="  reduce retry noise  ",
        status="  grounded  ",
        trace_id="trace-1",
        notes=["  use bounded retries  ", "", "log structured events"],
        questions=["", "what SLA applies?"],
    )
    assert payload["focus"] == "reduce retry noise"
    assert payload["status"] == "grounded"
    assert payload["notes"] == ["use bounded retries", "log structured events"]
    assert payload["questions"] == ["what SLA applies?"]
    stored = load_working_memory(tmp_path)
    assert stored["focus"] == "reduce retry noise"
    assert stored["trace_id"] == "trace-1"


def test_load_working_memory_returns_empty_when_missing(tmp_path: Path) -> None:
    assert load_working_memory(tmp_path) == {}


def test_record_episode_appends_to_jsonl_and_load_returns_recent_first(tmp_path: Path) -> None:
    record_episode(tmp_path, kind="advisory", title="first", summary="step 1", status="ok")
    record_episode(tmp_path, kind="advisory", title="second", summary="step 2", status="ok")
    record_episode(tmp_path, kind="advisory", title="third", summary="step 3", status="ok")
    rows = load_episode_memory(tmp_path)
    assert [row["title"] for row in rows] == ["third", "second", "first"]


def test_record_episode_writes_trimmed_fields(tmp_path: Path) -> None:
    payload = record_episode(
        tmp_path,
        kind="advisory",
        title="  trimmed title  ",
        summary="  summary text  ",
        status="  ok  ",
        trace_id="trace-x",
    )
    assert payload["title"] == "trimmed title"
    assert payload["summary"] == "summary text"
    assert payload["status"] == "ok"
    assert payload["trace_id"] == "trace-x"


def test_load_episode_memory_respects_limit(tmp_path: Path) -> None:
    for index in range(5):
        record_episode(tmp_path, kind="advisory", title=f"row-{index}", summary="x", status="ok")
    rows = load_episode_memory(tmp_path, limit=2)
    assert [row["title"] for row in rows] == ["row-4", "row-3"]


def test_load_episode_memory_returns_empty_when_missing(tmp_path: Path) -> None:
    assert load_episode_memory(tmp_path) == []
