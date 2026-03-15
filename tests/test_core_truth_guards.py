from __future__ import annotations

import json
from pathlib import Path

from spark_researcher import candidates, runner
from spark_researcher.paths import ledger_path


def _write_ledger(runtime_root: Path, rows: list[dict]) -> None:
    path = ledger_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_best_metric_ignores_failed_rows(tmp_path: Path) -> None:
    runtime_root = tmp_path
    _write_ledger(
        runtime_root,
        [
            {"command_name": "research", "status": "ok", "metric_value": 1.0, "applied_mutations": []},
            {"command_name": "research", "status": "failed", "metric_value": 9.0, "applied_mutations": [{"name": "x", "value": "9"}]},
            {"command_name": "research", "status": "ok", "metric_value": 5.0, "applied_mutations": [{"name": "x", "value": "5"}]},
        ],
    )

    assert runner.best_metric(runtime_root, "research", "maximize") == 5.0


def test_baseline_metric_only_uses_ok_baseline_rows(tmp_path: Path) -> None:
    runtime_root = tmp_path
    _write_ledger(
        runtime_root,
        [
            {"command_name": "research", "status": "ok", "metric_value": 0.6, "applied_mutations": []},
            {"command_name": "research", "status": "ok", "metric_value": 0.95, "applied_mutations": [{"name": "mode", "value": "candidate"}]},
            {"command_name": "research", "status": "failed", "metric_value": 0.99, "applied_mutations": []},
        ],
    )

    assert runner.baseline_metric(runtime_root, "research", "maximize") == 0.6


def test_candidate_primitive_selection_ignores_failed_rows() -> None:
    rows = [
        {"command_name": "research", "status": "ok", "metric_value": 1.0, "applied_mutations": []},
        {
            "command_name": "research",
            "status": "failed",
            "metric_value": 9.0,
            "verdict": "improved",
            "candidate_id": "bad",
            "applied_mutations": [{"name": "lane", "value": "bad"}],
        },
        {
            "command_name": "research",
            "status": "ok",
            "metric_value": 2.0,
            "verdict": "improved",
            "candidate_id": "good",
            "applied_mutations": [{"name": "lane", "value": "good"}],
        },
    ]

    best = candidates._best_single_primitives(rows, "research", "maximize", baseline_metric=1.0)

    assert best == {
        "lane": {
            "name": "lane",
            "value": "good",
            "metric_value": 2.0,
            "candidate_id": "good",
            "reason": "beats baseline",
        }
    }


def test_failed_and_unknown_rows_count_as_discards() -> None:
    assert runner.row_counts_as_discard({"status": "failed", "verdict": "baseline"}) is True
    assert runner.row_counts_as_discard({"status": "ok", "verdict": "unknown"}) is True
    assert runner.row_counts_as_discard({"status": "ok", "verdict": "regressed"}) is True
    assert runner.row_counts_as_discard({"status": "ok", "verdict": "improved"}) is False

    assert candidates._row_counts_as_discard({"status": "failed", "verdict": "baseline"}) is True
    assert candidates._row_counts_as_discard({"status": "ok", "verdict": "unknown"}) is True
    assert candidates._row_counts_as_discard({"status": "ok", "verdict": "regressed"}) is True
    assert candidates._row_counts_as_discard({"status": "ok", "verdict": "improved"}) is False
