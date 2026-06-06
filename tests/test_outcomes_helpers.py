from __future__ import annotations

import json
from pathlib import Path

import pytest

from spark_researcher.outcomes import (
    load_advisory_outcomes,
    log_advisory_outcome,
    review_advisory_outcomes,
)
from spark_researcher.paths import advisory_root


def test_log_advisory_outcome_appends_jsonl(tmp_path: Path) -> None:
    result = log_advisory_outcome(
        tmp_path,
        task="explore tradeoffs",
        model="generic",
        status="ok",
        packet_ids=["packet-a"],
        score=0.8,
        notes="seed",
        domain="research",
    )
    assert result["recorded"] is True
    log_path = Path(result["path"])
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["task"] == "explore tradeoffs"
    assert row["packet_ids"] == ["packet-a"]
    assert row["domain"] == "research"


def test_load_advisory_outcomes_skips_blank_and_invalid_lines(tmp_path: Path) -> None:
    root = advisory_root(tmp_path)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "outcomes.jsonl"
    path.write_text(
        "\n"
        + json.dumps({"task": "a", "packet_ids": [], "status": "ok"})
        + "\n"
        + "{not valid json\n"
        + "   \n"
        + json.dumps({"task": "b", "packet_ids": [], "status": "fail"})
        + "\n",
        encoding="utf-8",
    )
    rows = load_advisory_outcomes(tmp_path)
    assert [row["task"] for row in rows] == ["a", "b"]


def test_load_advisory_outcomes_returns_empty_when_missing(tmp_path: Path) -> None:
    assert load_advisory_outcomes(tmp_path) == []


def test_review_advisory_outcomes_recommends_keep_for_high_scores(tmp_path: Path) -> None:
    for status, score in (("ok", 0.95), ("ok", 0.9), ("ok", 0.85)):
        log_advisory_outcome(
            tmp_path,
            task="task",
            model="m",
            status=status,
            packet_ids=["p1"],
            score=score,
        )
    review = review_advisory_outcomes(tmp_path)
    assert review["outcome_count"] == 3
    [packet] = review["packet_reviews"]
    assert packet["packet_id"] == "p1"
    assert packet["uses"] == 3
    assert packet["recommendation"] == "keep"
    assert packet["average_score"] == pytest.approx(round((0.95 + 0.9 + 0.85) / 3, 3))


def test_review_advisory_outcomes_recommends_drop_for_low_scores(tmp_path: Path) -> None:
    for score in (0.2, 0.3, 0.4):
        log_advisory_outcome(
            tmp_path,
            task="task",
            model="m",
            status="fail",
            packet_ids=["weak"],
            score=score,
        )
    review = review_advisory_outcomes(tmp_path)
    [packet] = review["packet_reviews"]
    assert packet["recommendation"] == "drop"


def test_review_advisory_outcomes_recommends_rewrite_when_mixed(tmp_path: Path) -> None:
    log_advisory_outcome(tmp_path, task="t", model="m", status="ok", packet_ids=["mix"], score=0.6)
    log_advisory_outcome(tmp_path, task="t", model="m", status="fail", packet_ids=["mix"], score=0.6)
    review = review_advisory_outcomes(tmp_path)
    [packet] = review["packet_reviews"]
    assert packet["recommendation"] == "rewrite"
