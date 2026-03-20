"""Feedback loop and scoring calibration for the Vibe Incubator (Tier 5).

Closes the predict → observe → compare → adapt cycle.

Components:
    ``ScoringCalibrator``
        Reads accuracy reports and adjusts scoring dimension weights to
        reduce future prediction error.  Adjustments are small (max 5% per
        cycle) to avoid instability.

    ``PolicyAdapter``
        Examines portfolio outcomes and recommends policy parameter changes
        (e.g. review cadence, validation pressure).

    ``run_feedback_cycle()``
        Top-level function called by the scheduler weekly tick.  Records
        outcomes for all active ventures, computes accuracy, runs calibration
        and policy adaptation, persists results.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from .ops_loop import (
    DEFAULT_POLICY,
    append_log,
    load_state,
    ops_write_lock,
    read_log,
    save_state,
)
from .outcome_tracker import (
    AccuracyReport,
    Outcome,
    Prediction,
    _outcome_from_venture,
    compute_accuracy,
    record_outcome,
    record_prediction,
)

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Scoring dimension weights (baseline)
# ---------------------------------------------------------------------------

# These match the weights used in ops_loop._score_state() activity_score line.
# The calibrator adjusts these based on prediction accuracy.
DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "focus": 0.18,
    "automation": 0.16,
    "review": 0.16,
    "validation": 0.20,
    "knowledge": 0.15,
    "trust": 0.15,
}

# Outcome weights from _score_state()
DEFAULT_OUTCOME_WEIGHTS: dict[str, float] = {
    "revenue": 0.35,
    "retention": 0.25,
    "impact": 0.25,
    "review_quality": 0.15,
}

MAX_WEIGHT_DELTA = 0.05  # max adjustment per cycle


# ---------------------------------------------------------------------------
# ScoringCalibrator
# ---------------------------------------------------------------------------

@dataclass
class CalibrationResult:
    """Output of a calibration cycle."""

    original_weights: dict[str, float] = field(default_factory=dict)
    adjusted_weights: dict[str, float] = field(default_factory=dict)
    accuracy_before: float = 0.0
    dimensions_adjusted: list[str] = field(default_factory=list)
    calibrated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ScoringCalibrator:
    """Adjusts scoring dimension weights based on prediction accuracy.

    Strategy:
        - Dimensions with high MAE get slightly reduced weight (the model
          is less reliable there, so lean more on heuristic).
        - Dimensions with low MAE get slightly increased weight (the model
          is more reliable there).
        - Total weights are always re-normalized to sum to 1.0.
    """

    def __init__(
        self,
        base_weights: dict[str, float] | None = None,
        max_delta: float = MAX_WEIGHT_DELTA,
    ) -> None:
        self.base_weights = dict(base_weights or DEFAULT_DIMENSION_WEIGHTS)
        self.max_delta = max_delta

    def calibrate(self, accuracy: AccuracyReport) -> CalibrationResult:
        """Produce adjusted weights from an accuracy report."""
        if accuracy.pair_count < 3:
            # Not enough data to calibrate
            return CalibrationResult(
                original_weights=dict(self.base_weights),
                adjusted_weights=dict(self.base_weights),
                accuracy_before=accuracy.overall_mae,
            )

        dim_mae = accuracy.dimension_mae
        if not dim_mae:
            return CalibrationResult(
                original_weights=dict(self.base_weights),
                adjusted_weights=dict(self.base_weights),
                accuracy_before=accuracy.overall_mae,
            )

        # Compute mean MAE across measured dimensions
        measured_dims = [k for k in dim_mae if k in self.base_weights]
        if not measured_dims:
            return CalibrationResult(
                original_weights=dict(self.base_weights),
                adjusted_weights=dict(self.base_weights),
                accuracy_before=accuracy.overall_mae,
            )

        avg_mae = sum(dim_mae[k] for k in measured_dims) / len(measured_dims)

        adjusted = dict(self.base_weights)
        dims_changed: list[str] = []

        for dim in measured_dims:
            error = dim_mae[dim]
            if error > avg_mae * 1.2:
                # Above average error → reduce weight
                delta = min(self.max_delta, (error - avg_mae) * 0.5)
                adjusted[dim] = max(0.05, adjusted[dim] - delta)
                dims_changed.append(dim)
            elif error < avg_mae * 0.8:
                # Below average error → increase weight
                delta = min(self.max_delta, (avg_mae - error) * 0.5)
                adjusted[dim] = adjusted[dim] + delta
                dims_changed.append(dim)

        # Re-normalize to sum to 1.0
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: round(v / total, 4) for k, v in adjusted.items()}

        return CalibrationResult(
            original_weights=dict(self.base_weights),
            adjusted_weights=adjusted,
            accuracy_before=accuracy.overall_mae,
            dimensions_adjusted=dims_changed,
        )


# ---------------------------------------------------------------------------
# PolicyAdapter
# ---------------------------------------------------------------------------

@dataclass
class PolicyRecommendation:
    """A recommended change to an incubator policy parameter."""

    parameter: str
    current_value: str
    recommended_value: str
    reason: str
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdaptationResult:
    """Output of a policy adaptation cycle."""

    recommendations: list[PolicyRecommendation] = field(default_factory=list)
    portfolio_health: str = ""  # "healthy", "struggling", "critical"
    adapted_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendations": [r.to_dict() for r in self.recommendations],
            "portfolio_health": self.portfolio_health,
            "adapted_at": self.adapted_at,
        }


class PolicyAdapter:
    """Examines portfolio metrics and recommends policy changes.

    Rules are heuristic-based (no LLM needed).  Each rule checks a specific
    metric condition and suggests a policy change if warranted.
    """

    def adapt(
        self,
        state: dict[str, Any],
        accuracy: AccuracyReport,
        current_policy: dict[str, str],
    ) -> AdaptationResult:
        ventures = [
            v for v in state.get("ventures", [])
            if isinstance(v, dict) and v.get("status") == "active"
        ]
        recs: list[PolicyRecommendation] = []

        if not ventures:
            return AdaptationResult(portfolio_health="empty")

        # Compute aggregate metrics
        avg_freshness = _mean([float(v.get("weekly_update_freshness_days", 0) or 0) for v in ventures])
        avg_review_days = _mean([float(v.get("last_review_days", 0) or 0) for v in ventures])
        avg_revenue_trend = _mean([float(v.get("revenue_trend", 0) or 0) for v in ventures])
        avg_retention = _mean([float(v.get("retention_signal", 0) or 0) for v in ventures])

        # Determine health
        if avg_revenue_trend < -0.2 or avg_retention < 0.2:
            health = "critical"
        elif avg_revenue_trend < 0 or avg_freshness > 7:
            health = "struggling"
        else:
            health = "healthy"

        # Rule 1: If updates are chronically stale, suggest tighter cadence
        if avg_freshness > 5 and current_policy.get("founder_update_sla") != "24h":
            recs.append(PolicyRecommendation(
                parameter="founder_update_sla",
                current_value=current_policy.get("founder_update_sla", "48h"),
                recommended_value="24h",
                reason=f"Average update freshness is {avg_freshness:.0f} days — tighten SLA",
                confidence=min(0.9, avg_freshness / 10),
            ))

        # Rule 2: If reviews are overdue across portfolio, increase cadence
        if avg_review_days > 10 and current_policy.get("review_cadence") != "daily":
            recs.append(PolicyRecommendation(
                parameter="review_cadence",
                current_value=current_policy.get("review_cadence", "weekly"),
                recommended_value="twice_weekly",
                reason=f"Average review gap is {avg_review_days:.0f} days — increase cadence",
                confidence=min(0.85, avg_review_days / 14),
            ))

        # Rule 3: If revenue is declining, increase validation pressure
        if avg_revenue_trend < -0.1 and current_policy.get("validation_pressure") != "paid_every_week":
            recs.append(PolicyRecommendation(
                parameter="validation_pressure",
                current_value=current_policy.get("validation_pressure", "design_partner_first"),
                recommended_value="paid_every_week",
                reason=f"Average revenue trend is {avg_revenue_trend:.0%} — tighten validation",
                confidence=0.7,
            ))

        # Rule 4: If portfolio is overloaded, suggest cap reduction
        cap = int(current_policy.get("portfolio_cap", "3") or 3)
        if len(ventures) > cap and health in ("struggling", "critical"):
            recs.append(PolicyRecommendation(
                parameter="portfolio_cap",
                current_value=str(cap),
                recommended_value=str(max(2, cap - 1)),
                reason=f"Portfolio over cap ({len(ventures)}/{cap}) while health={health}",
                confidence=0.6,
            ))

        # Rule 5: If prediction accuracy is low, increase knowledge capture
        if accuracy.overall_mae > 0.3 and current_policy.get("knowledge_capture") != "every_review":
            recs.append(PolicyRecommendation(
                parameter="knowledge_capture",
                current_value=current_policy.get("knowledge_capture", "weekly_summary"),
                recommended_value="every_review",
                reason=f"Prediction MAE is {accuracy.overall_mae:.2f} — capture more data to improve",
                confidence=0.65,
            ))

        return AdaptationResult(
            recommendations=recs,
            portfolio_health=health,
        )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# ---------------------------------------------------------------------------
# Top-level feedback cycle
# ---------------------------------------------------------------------------

async def run_feedback_cycle(runtime_root: str) -> dict[str, Any]:
    """Run the full feedback cycle: record outcomes → compute accuracy → calibrate → adapt.

    Returns a summary dict suitable for logging.
    """
    # 1. Record current outcomes for all active ventures
    state = load_state(runtime_root)
    ventures = [
        v for v in state.get("ventures", [])
        if isinstance(v, dict) and v.get("status") == "active"
    ]

    outcome_count = 0
    for venture in ventures:
        outcome = _outcome_from_venture(venture)
        record_outcome(runtime_root, outcome)
        outcome_count += 1

    # 2. Compute accuracy
    accuracy = compute_accuracy(runtime_root)

    # 3. Calibrate scoring weights
    calibrator = ScoringCalibrator()
    calibration = calibrator.calibrate(accuracy)

    # 4. Adapt policy
    current_policy = dict(state.get("effective_policy", DEFAULT_POLICY))
    adapter = PolicyAdapter()
    adaptation = adapter.adapt(state, accuracy, current_policy)

    # 5. Persist results
    result = {
        "outcomes_recorded": outcome_count,
        "accuracy": accuracy.to_dict(),
        "calibration": calibration.to_dict(),
        "adaptation": adaptation.to_dict(),
        "cycle_at": _now_iso(),
    }
    append_log(runtime_root, "feedback_cycles", result)

    # 6. Store adjusted weights on state for next tick to pick up
    with ops_write_lock(runtime_root):
        state = load_state(runtime_root)
        state["scoring_weights"] = calibration.adjusted_weights
        state["last_feedback_cycle"] = result
        save_state(runtime_root, state)

    log.info(
        "Feedback cycle complete  pairs=%d  MAE=%.3f  adjustments=%d  recs=%d",
        accuracy.pair_count, accuracy.overall_mae,
        len(calibration.dimensions_adjusted),
        len(adaptation.recommendations),
    )
    return result
