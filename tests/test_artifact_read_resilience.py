from __future__ import annotations

from pathlib import Path

import pytest

from spark_researcher.outcomes import load_advisory_outcomes
from spark_researcher.tracing import trace_status


def test_trace_status_uses_bounded_error_for_unreadable_index(tmp_path: Path, monkeypatch) -> None:
    index_path = tmp_path / "artifacts" / "traces" / "index.jsonl"
    index_path.parent.mkdir(parents=True)
    index_path.write_text("{}\n", encoding="utf-8")
    original_read_text = Path.read_text

    def fail_index_read(path: Path, *args, **kwargs) -> str:
        if path == index_path:
            raise OSError("PRIVATE_TRACE_STORAGE_DETAIL")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_index_read)

    with pytest.raises(RuntimeError) as captured:
        trace_status(tmp_path)

    assert str(captured.value) == "Trace evidence is unavailable."
    assert "PRIVATE_TRACE_STORAGE_DETAIL" not in str(captured.value)
    assert str(tmp_path) not in str(captured.value)


def test_advisory_outcomes_use_bounded_error_for_unreadable_file(tmp_path: Path, monkeypatch) -> None:
    outcomes_path = tmp_path / "artifacts" / "advisory" / "outcomes.jsonl"
    outcomes_path.parent.mkdir(parents=True)
    outcomes_path.write_text("{}\n", encoding="utf-8")
    original_read_text = Path.read_text

    def fail_outcome_read(path: Path, *args, **kwargs) -> str:
        if path == outcomes_path:
            raise OSError("PRIVATE_OUTCOME_STORAGE_DETAIL")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_outcome_read)

    with pytest.raises(RuntimeError) as captured:
        load_advisory_outcomes(tmp_path)

    assert str(captured.value) == "Advisory outcome evidence is unavailable."
    assert "PRIVATE_OUTCOME_STORAGE_DETAIL" not in str(captured.value)
    assert str(tmp_path) not in str(captured.value)
