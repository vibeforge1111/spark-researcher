"""Outcome tracking for the Vibe Incubator feedback loop (Tier 5).

Records predictions from LLM agents and heuristic scoring, then compares
them against observed outcomes to compute accuracy metrics.  This data
feeds into ``ScoringCalibrator`` to adjust scoring weights over time.

Design:
    - Predictions are appended to ``predictions.jsonl``
    - Outcomes are appended to ``outcomes.jsonl``
    - ``compute_accuracy()`` pairs predictions with outcomes and returns
      per-dimension accuracy plus overall MAE (mean absolute error).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from .ops_loop import append_log, read_log

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Prediction:
    """A scored prediction for a venture at a point in time."""

    venture_id: str
    tick_number: int
    source: str  # "heuristic", "llm", "blended"
    scores: dict[str, float] = field(default_factory=dict)
    recommendation: str = ""
    confidence: float = 0.0
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Outcome:
    """An observed outcome for a venture (recorded when KPIs arrive)."""

    venture_id: str
    outcome_type: str  # "kpi_snapshot", "exit", "stage_change", "review"
    observed_scores: dict[str, float] = field(default_factory=dict)
    actual_status: str = ""  # "active", "archived", "stopped"
    actual_stage: str = ""
    observed_at: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AccuracyReport:
    """Accuracy metrics from comparing predictions to outcomes."""

    pair_count: int = 0
    overall_mae: float = 0.0  # mean absolute error across all dimensions
    dimension_mae: dict[str, float] = field(default_factory=dict)
    recommendation_accuracy: float = 0.0  # fraction of correct recommendations
    sample_window_days: int = 0
    computed_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def record_prediction(runtime_root: str, prediction: Prediction) -> None:
    """Append a prediction to the predictions log."""
    append_log(runtime_root, "predictions", prediction.to_dict())


def record_outcome(runtime_root: str, outcome: Outcome) -> None:
    """Append an outcome to the outcomes log."""
    append_log(runtime_root, "outcomes", outcome.to_dict())


def load_predictions(runtime_root: str) -> list[dict[str, Any]]:
    return read_log(runtime_root, "predictions")


def load_outcomes(runtime_root: str) -> list[dict[str, Any]]:
    return read_log(runtime_root, "outcomes")


# ---------------------------------------------------------------------------
# Accuracy computation
# ---------------------------------------------------------------------------

def _pair_predictions_outcomes(
    predictions: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Pair each prediction with the closest subsequent outcome for the same venture.

    Strategy: for each prediction, find the earliest outcome for the same
    venture_id that was recorded *after* the prediction.
    """
    # Sort by time
    preds_sorted = sorted(predictions, key=lambda p: p.get("created_at", ""))
    outcomes_by_venture: dict[str, list[dict[str, Any]]] = {}
    for o in outcomes:
        vid = str(o.get("venture_id", ""))
        outcomes_by_venture.setdefault(vid, []).append(o)
    for vid in outcomes_by_venture:
        outcomes_by_venture[vid].sort(key=lambda o: o.get("observed_at", ""))

    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    used_outcomes: set[int] = set()

    for pred in preds_sorted:
        vid = str(pred.get("venture_id", ""))
        pred_time = pred.get("created_at", "")
        candidates = outcomes_by_venture.get(vid, [])
        for i, outcome in enumerate(candidates):
            if id(outcome) in used_outcomes:
                continue
            if outcome.get("observed_at", "") >= pred_time:
                pairs.append((pred, outcome))
                used_outcomes.add(id(outcome))
                break

    return pairs


def compute_accuracy(runtime_root: str) -> AccuracyReport:
    """Compare recorded predictions against observed outcomes."""
    predictions = load_predictions(runtime_root)
    outcomes = load_outcomes(runtime_root)

    if not predictions or not outcomes:
        return AccuracyReport()

    pairs = _pair_predictions_outcomes(predictions, outcomes)
    if not pairs:
        return AccuracyReport()

    dimension_errors: dict[str, list[float]] = {}
    correct_recommendations = 0
    total_with_recommendation = 0

    for pred, outcome in pairs:
        pred_scores = pred.get("scores", {})
        obs_scores = outcome.get("observed_scores", {})

        shared_keys = set(pred_scores) & set(obs_scores)
        for key in shared_keys:
            try:
                error = abs(float(pred_scores[key]) - float(obs_scores[key]))
                dimension_errors.setdefault(key, []).append(error)
            except (TypeError, ValueError):
                continue

        # Check recommendation accuracy
        pred_rec = pred.get("recommendation", "")
        actual_status = outcome.get("actual_status", "")
        if pred_rec and actual_status:
            total_with_recommendation += 1
            # "continue" is correct if venture is still active
            # "stop"/"pivot" is correct if venture is archived/stopped
            if pred_rec in ("continue", "on_track") and actual_status == "active":
                correct_recommendations += 1
            elif pred_rec in ("stop", "exit") and actual_status in ("archived", "stopped"):
                correct_recommendations += 1
            elif pred_rec in ("narrow", "pivot") and actual_status in ("active", "archived"):
                correct_recommendations += 1  # pivot is ambiguously correct

    # Compute per-dimension MAE
    dim_mae: dict[str, float] = {}
    all_errors: list[float] = []
    for key, errors in dimension_errors.items():
        mae = sum(errors) / len(errors) if errors else 0.0
        dim_mae[key] = round(mae, 4)
        all_errors.extend(errors)

    overall_mae = sum(all_errors) / len(all_errors) if all_errors else 0.0
    rec_accuracy = correct_recommendations / total_with_recommendation if total_with_recommendation > 0 else 0.0

    return AccuracyReport(
        pair_count=len(pairs),
        overall_mae=round(overall_mae, 4),
        dimension_mae=dim_mae,
        recommendation_accuracy=round(rec_accuracy, 4),
    )


def _outcome_from_venture(venture: dict[str, Any], outcome_type: str = "kpi_snapshot") -> Outcome:
    """Build an Outcome from current venture state (convenience helper)."""
    # Extract observable scores from venture state
    observed: dict[str, float] = {}
    for key in (
        "automation_coverage", "revenue_trend", "retention_signal",
    ):
        val = venture.get(key)
        if val is not None:
            try:
                observed[key] = float(val)
            except (TypeError, ValueError):
                pass

    # Map update freshness to a 0-1 score (fresher = higher)
    freshness = venture.get("weekly_update_freshness_days")
    if freshness is not None:
        try:
            observed["update_freshness"] = max(0.0, 1.0 - float(freshness) / 7.0)
        except (TypeError, ValueError):
            pass

    return Outcome(
        venture_id=str(venture.get("venture_id", "")),
        outcome_type=outcome_type,
        observed_scores=observed,
        actual_status=str(venture.get("status", "")),
        actual_stage=str(venture.get("stage", "")),
    )
