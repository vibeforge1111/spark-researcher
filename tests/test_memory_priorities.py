from __future__ import annotations

from pathlib import Path

from spark_researcher.memory import (
    _build_outcomes,
    _build_snippet,
    _default_memory_tier,
    _infer_document_kind,
    _is_better,
    _kind_priority,
    _tier_priority,
)


def test_kind_priority_orders_startup_above_lower_tiers() -> None:
    assert _kind_priority("startup_research") > _kind_priority("belief")
    assert _kind_priority("belief") > _kind_priority("episode")
    assert _kind_priority("episode") > _kind_priority("working")
    assert _kind_priority("unknown_kind") == 0


def test_tier_priority_ranks_doctrine_first() -> None:
    assert _tier_priority("grounded_doctrine") > _tier_priority("research_grounded")
    assert _tier_priority("benchmark_evidence") > _tier_priority("state_snapshot")
    assert _tier_priority("raw_run") < _tier_priority("raw_outcome")
    assert _tier_priority("unknown_tier") == 0


def test_default_memory_tier_maps_known_kinds() -> None:
    assert _default_memory_tier("startup_doctrine") == "grounded_doctrine"
    assert _default_memory_tier("belief") == "belief"
    assert _default_memory_tier("outcome") == "raw_outcome"
    assert _default_memory_tier("anything_else") == "raw_run"


def test_infer_document_kind_recognizes_well_known_stems() -> None:
    assert _infer_document_kind(Path("working-memory.md")) == "working"
    assert _infer_document_kind(Path("episode-memory.md")) == "episode"
    assert _infer_document_kind(Path("run-001.md")) == "run"
    assert _infer_document_kind(Path("outcome-abc.md")) == "outcome"
    assert _infer_document_kind(Path("belief-x.md")) == "belief"
    assert _infer_document_kind(Path("self-edit-1.md")) == "self_edit"
    assert _infer_document_kind(Path("startup_doctrine-x.md")) == "startup_doctrine"
    assert _infer_document_kind(Path("random.md")) == "unknown"


def test_is_better_treats_none_as_worst() -> None:
    assert _is_better(0.1, None, "minimize") is True
    assert _is_better(0.1, None, "maximize") is True


def test_is_better_respects_goal_direction() -> None:
    assert _is_better(0.5, 0.7, "minimize") is True
    assert _is_better(0.5, 0.3, "minimize") is False
    assert _is_better(0.7, 0.5, "maximize") is True
    assert _is_better(0.3, 0.5, "maximize") is False


def test_build_outcomes_groups_by_command_and_candidate() -> None:
    rows = [
        {"command_name": "tune", "candidate_id": "cand-1", "verdict": "improved", "metric_value": 0.5, "run_id": "r1"},
        {"command_name": "tune", "candidate_id": "cand-1", "verdict": "regressed", "metric_value": 0.6, "run_id": "r2"},
        {"command_name": "tune", "candidate_id": "cand-2", "verdict": "improved", "metric_value": 0.4, "run_id": "r3"},
    ]
    outcomes = _build_outcomes(rows, goal="minimize")
    assert len(outcomes) == 2
    first, second = outcomes
    assert first["candidate_id"] == "cand-1"
    assert first["run_count"] == 2
    assert first["improved_runs"] == 1
    assert first["best_metric"] == 0.5  # minimize keeps the lower value
    assert second["candidate_id"] == "cand-2"
    assert second["best_metric"] == 0.4


def test_build_snippet_returns_window_around_match() -> None:
    text = "the brown fox jumps over the LAZY dog"
    snippet = _build_snippet(text, "lazy", width=30)
    assert "LAZY" in snippet


def test_build_snippet_returns_head_when_no_match() -> None:
    text = "alpha\nbeta\ngamma" * 100
    snippet = _build_snippet(text, "missing-term", width=20)
    assert "\n" not in snippet
    assert len(snippet) <= 20
