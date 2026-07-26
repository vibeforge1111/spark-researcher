from __future__ import annotations

import json
from pathlib import Path

from spark_researcher.optimizer import export_advisory_dataset, optimizer_status


def _write_outcome(runtime_root: Path, payload: dict[str, object]) -> None:
    outcomes_path = runtime_root / "artifacts" / "advisory" / "outcomes.jsonl"
    outcomes_path.parent.mkdir(parents=True, exist_ok=True)
    with outcomes_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def test_optimizer_status_reports_optional_provider_and_notes() -> None:
    status = optimizer_status()
    assert status["mode"] == "optional"
    assert isinstance(status["notes"], list)
    assert any("Spark Researcher does not require DSPy" in note for note in status["notes"])
    # Provider must be "dspy" iff available; otherwise None.
    if status["available"]:
        assert status["provider"] == "dspy"
    else:
        assert status["provider"] is None


def test_export_advisory_dataset_skips_rows_without_packet_ids(tmp_path: Path) -> None:
    _write_outcome(tmp_path, {"task": "a", "packet_ids": ["p1"], "status": "ok", "score": 0.9})
    _write_outcome(tmp_path, {"task": "no-packets", "status": "ok"})  # excluded -- no packet_ids
    _write_outcome(tmp_path, {"task": "empty-packets", "packet_ids": [], "status": "ok"})  # excluded -- empty list

    payload = export_advisory_dataset(tmp_path)

    assert payload["example_count"] == 1
    dataset_path = Path(payload["path"])
    assert dataset_path.exists()
    lines = dataset_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["packet_ids"] == ["p1"]
    assert parsed["task"] == "a"


def test_export_advisory_dataset_marks_ready_for_dspy_only_at_five_or_more(tmp_path: Path) -> None:
    # Four ok-with-score rows: below the >=5 threshold.
    for idx in range(4):
        _write_outcome(
            tmp_path,
            {"task": f"t{idx}", "packet_ids": [f"p{idx}"], "status": "ok", "score": 0.5},
        )

    payload = export_advisory_dataset(tmp_path)
    assert payload["example_count"] == 4
    assert payload["ready_for_dspy"] is False

    # Add the fifth row -- now ready_for_dspy must flip.
    _write_outcome(
        tmp_path,
        {"task": "t4", "packet_ids": ["p4"], "status": "ok", "score": 0.5},
    )
    payload2 = export_advisory_dataset(tmp_path)
    assert payload2["example_count"] == 5
    assert payload2["ready_for_dspy"] is True


def test_export_advisory_dataset_ignores_rows_that_lack_numeric_score_or_ok_status(tmp_path: Path) -> None:
    # Status-ok with no numeric score must not count toward the ready threshold.
    _write_outcome(tmp_path, {"task": "no-score", "packet_ids": ["p1"], "status": "ok"})
    # Non-ok status with score must not count.
    _write_outcome(
        tmp_path,
        {"task": "fail", "packet_ids": ["p2"], "status": "fail", "score": 0.7},
    )
    # Score-as-string must not count toward the readiness threshold.
    _write_outcome(
        tmp_path,
        {"task": "score-str", "packet_ids": ["p3"], "status": "ok", "score": "0.9"},
    )

    payload = export_advisory_dataset(tmp_path)
    # All three rows are dataset-eligible (they have packet_ids) but none satisfy the readiness rule.
    assert payload["example_count"] == 3
    assert payload["ready_for_dspy"] is False


def test_export_advisory_dataset_writes_empty_file_when_no_outcomes_exist(tmp_path: Path) -> None:
    payload = export_advisory_dataset(tmp_path)
    assert payload["example_count"] == 0
    assert payload["ready_for_dspy"] is False
    dataset_path = Path(payload["path"])
    assert dataset_path.exists()
    assert dataset_path.read_text(encoding="utf-8") == ""


def test_export_advisory_dataset_overwrites_previous_dataset(tmp_path: Path) -> None:
    _write_outcome(tmp_path, {"task": "first", "packet_ids": ["p1"], "status": "ok", "score": 0.1})
    first = export_advisory_dataset(tmp_path)
    assert first["example_count"] == 1

    # Now drop the underlying outcome and re-export; the dataset file must reflect the new shape.
    (tmp_path / "artifacts" / "advisory" / "outcomes.jsonl").unlink()
    second = export_advisory_dataset(tmp_path)
    assert second["example_count"] == 0
    dataset_path = Path(second["path"])
    assert dataset_path.read_text(encoding="utf-8") == ""
