from __future__ import annotations

from spark_researcher.memory import (
    build_episode_memory_doc,
    build_outcome_doc,
    build_run_doc,
    build_self_edit_doc,
    build_working_memory_doc,
)


def test_build_run_doc_includes_mutations_and_paths() -> None:
    record = {
        "run_id": "run-001",
        "candidate_id": "cand-1",
        "command_name": "tune",
        "verdict": "improved",
        "metric_name": "rmse",
        "metric_value": 0.5,
        "trace_id": "trace-001",
        "hypothesis": "increase capacity",
        "applied_mutations": [{"name": "lr", "value": "0.01"}],
    }
    doc = build_run_doc(record)
    assert "# Run Memory cand-1" in doc
    assert "- run_id: `run-001`" in doc
    assert "- `lr` -> `0.01`" in doc
    assert "increase capacity" in doc


def test_build_run_doc_handles_missing_mutations() -> None:
    doc = build_run_doc({"run_id": "r", "candidate_id": "c"})
    assert "- none" in doc
    assert "n/a" in doc


def test_build_outcome_doc_renders_run_ids() -> None:
    outcome = {
        "title": "tune / cand-1",
        "outcome_id": "outcome-abc",
        "command_name": "tune",
        "candidate_id": "cand-1",
        "run_count": 2,
        "improved_runs": 1,
        "latest_verdict": "improved",
        "best_metric": 0.4,
        "latest_metric": 0.5,
        "run_ids": ["run-001", "run-002"],
    }
    doc = build_outcome_doc(outcome)
    assert "# Outcome tune / cand-1" in doc
    assert "- `run-001`" in doc and "- `run-002`" in doc


def test_build_self_edit_doc_omits_review_section_when_absent() -> None:
    doc = build_self_edit_doc({"proposal_id": "prop-1", "status": "open"}, None)
    assert "# Self Edit prop-1" in doc
    assert "## Review" not in doc


def test_build_self_edit_doc_includes_review_when_present() -> None:
    review = {
        "decision": "accept",
        "root_lesson": "use bounded retries",
        "trace_id": "trace-x",
        "lineage_failures": ["fail-1"],
    }
    doc = build_self_edit_doc({"proposal_id": "prop-1"}, review)
    assert "## Review" in doc
    assert "- decision: `accept`" in doc
    assert "- fail-1" in doc


def test_build_working_memory_doc_filters_blank_entries() -> None:
    payload = {
        "updated_at": "2026-06-06T00:00:00+00:00",
        "kind": "advisory",
        "status": "grounded",
        "focus": "stabilize retry budget",
        "notes": ["actionable note", "  ", "another"],
        "questions": ["", "what is the right SLA?"],
    }
    doc = build_working_memory_doc(payload)
    assert "stabilize retry budget" in doc
    assert "- actionable note" in doc and "- another" in doc
    assert "what is the right SLA?" in doc


def test_build_episode_memory_doc_handles_empty_and_filled_rows() -> None:
    assert "No episodes yet." in build_episode_memory_doc([])
    rows = [
        {"title": "First step", "kind": "advisory", "status": "ok", "summary": "started"},
        {"kind": "outcome", "status": "fail", "summary": "rolled back"},
    ]
    doc = build_episode_memory_doc(rows)
    assert "## First step" in doc and "## outcome" in doc
    assert "rolled back" in doc
