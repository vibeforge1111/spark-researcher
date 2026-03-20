"""Tests for the feedback loop and outcome tracking system (Tier 5)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from domain_chip_vibe_incubator.ops_loop import load_state, read_log, save_state
from domain_chip_vibe_incubator.outcome_tracker import (
    AccuracyReport,
    Outcome,
    Prediction,
    _outcome_from_venture,
    _pair_predictions_outcomes,
    compute_accuracy,
    load_outcomes,
    load_predictions,
    record_outcome,
    record_prediction,
)
from domain_chip_vibe_incubator.feedback_loop import (
    AdaptationResult,
    CalibrationResult,
    PolicyAdapter,
    PolicyRecommendation,
    ScoringCalibrator,
    run_feedback_cycle,
)


@pytest.fixture()
def runtime_root(tmp_path: Path):
    artifacts = tmp_path / "artifacts" / "incubator_os"
    artifacts.mkdir(parents=True)
    (artifacts / "logs").mkdir()
    state = {
        "ventures": [
            {
                "venture_id": "v-alpha",
                "label": "Alpha Venture",
                "stage": "validation",
                "status": "active",
                "venture_model": "agentic_saas",
                "customer_surface": "founder_backoffice",
                "automation_coverage": 0.5,
                "weekly_revenue": 200,
                "revenue_trend": 0.1,
                "retention_signal": 0.6,
                "customer_conversations_this_week": 2,
                "paid_signals_this_week": 1,
                "weekly_update_freshness_days": 3,
                "last_review_days": 5,
                "trust_review_status": "green",
            },
        ],
        "applications": [],
        "founders": [],
        "batches": [],
    }
    (artifacts / "state.json").write_text(json.dumps(state))
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Prediction data class
# ---------------------------------------------------------------------------


class TestPrediction:
    def test_to_dict(self):
        p = Prediction(
            venture_id="v-1",
            tick_number=5,
            source="heuristic",
            scores={"focus": 0.7, "trust": 0.8},
            recommendation="continue",
            confidence=0.75,
        )
        d = p.to_dict()
        assert d["venture_id"] == "v-1"
        assert d["source"] == "heuristic"
        assert d["scores"]["focus"] == 0.7
        assert "created_at" in d

    def test_frozen(self):
        p = Prediction(venture_id="v-1", tick_number=1, source="llm")
        with pytest.raises(AttributeError):
            p.venture_id = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Outcome data class
# ---------------------------------------------------------------------------


class TestOutcome:
    def test_to_dict(self):
        o = Outcome(
            venture_id="v-1",
            outcome_type="kpi_snapshot",
            observed_scores={"revenue_trend": 0.15},
            actual_status="active",
        )
        d = o.to_dict()
        assert d["venture_id"] == "v-1"
        assert d["outcome_type"] == "kpi_snapshot"
        assert d["observed_scores"]["revenue_trend"] == 0.15

    def test_from_venture(self):
        venture = {
            "venture_id": "v-test",
            "status": "active",
            "stage": "validation",
            "automation_coverage": 0.65,
            "revenue_trend": 0.2,
            "retention_signal": 0.8,
            "weekly_update_freshness_days": 2,
        }
        o = _outcome_from_venture(venture)
        assert o.venture_id == "v-test"
        assert o.actual_status == "active"
        assert o.observed_scores["automation_coverage"] == 0.65
        assert o.observed_scores["revenue_trend"] == 0.2
        assert o.observed_scores["update_freshness"] > 0  # 1 - 2/7


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_record_and_load_predictions(self, runtime_root):
        p = Prediction(venture_id="v-alpha", tick_number=1, source="heuristic",
                       scores={"focus": 0.7})
        record_prediction(runtime_root, p)
        loaded = load_predictions(runtime_root)
        assert len(loaded) == 1
        assert loaded[0]["venture_id"] == "v-alpha"

    def test_record_and_load_outcomes(self, runtime_root):
        o = Outcome(venture_id="v-alpha", outcome_type="kpi_snapshot",
                    observed_scores={"focus": 0.8})
        record_outcome(runtime_root, o)
        loaded = load_outcomes(runtime_root)
        assert len(loaded) == 1
        assert loaded[0]["venture_id"] == "v-alpha"


# ---------------------------------------------------------------------------
# Pairing logic
# ---------------------------------------------------------------------------


class TestPairing:
    def test_pairs_prediction_with_later_outcome(self):
        preds = [
            {"venture_id": "v-1", "created_at": "2026-01-01T00:00:00+00:00", "scores": {"x": 0.5}},
        ]
        outcomes = [
            {"venture_id": "v-1", "observed_at": "2026-01-02T00:00:00+00:00", "observed_scores": {"x": 0.7}},
        ]
        pairs = _pair_predictions_outcomes(preds, outcomes)
        assert len(pairs) == 1
        assert pairs[0][0]["venture_id"] == "v-1"
        assert pairs[0][1]["observed_scores"]["x"] == 0.7

    def test_no_pair_when_outcome_before_prediction(self):
        preds = [
            {"venture_id": "v-1", "created_at": "2026-01-05T00:00:00+00:00", "scores": {}},
        ]
        outcomes = [
            {"venture_id": "v-1", "observed_at": "2026-01-01T00:00:00+00:00", "observed_scores": {}},
        ]
        pairs = _pair_predictions_outcomes(preds, outcomes)
        assert len(pairs) == 0

    def test_different_ventures_not_paired(self):
        preds = [
            {"venture_id": "v-1", "created_at": "2026-01-01T00:00:00+00:00", "scores": {}},
        ]
        outcomes = [
            {"venture_id": "v-2", "observed_at": "2026-01-02T00:00:00+00:00", "observed_scores": {}},
        ]
        pairs = _pair_predictions_outcomes(preds, outcomes)
        assert len(pairs) == 0

    def test_multiple_predictions_paired_in_order(self):
        preds = [
            {"venture_id": "v-1", "created_at": "2026-01-01T00:00:00+00:00", "scores": {"x": 0.3}},
            {"venture_id": "v-1", "created_at": "2026-01-03T00:00:00+00:00", "scores": {"x": 0.5}},
        ]
        outcomes = [
            {"venture_id": "v-1", "observed_at": "2026-01-02T00:00:00+00:00", "observed_scores": {"x": 0.4}},
            {"venture_id": "v-1", "observed_at": "2026-01-04T00:00:00+00:00", "observed_scores": {"x": 0.6}},
        ]
        pairs = _pair_predictions_outcomes(preds, outcomes)
        assert len(pairs) == 2


# ---------------------------------------------------------------------------
# Accuracy computation
# ---------------------------------------------------------------------------


class TestAccuracy:
    def test_empty_returns_zero(self, runtime_root):
        report = compute_accuracy(runtime_root)
        assert report.pair_count == 0
        assert report.overall_mae == 0.0

    def test_computes_mae(self, runtime_root):
        # Record a prediction
        p = Prediction(
            venture_id="v-alpha", tick_number=1, source="heuristic",
            scores={"focus": 0.7, "trust": 0.8},
            recommendation="continue",
            created_at="2026-01-01T00:00:00+00:00",
        )
        record_prediction(runtime_root, p)

        # Record an outcome
        o = Outcome(
            venture_id="v-alpha", outcome_type="kpi_snapshot",
            observed_scores={"focus": 0.6, "trust": 0.9},
            actual_status="active",
            observed_at="2026-01-02T00:00:00+00:00",
        )
        record_outcome(runtime_root, o)

        report = compute_accuracy(runtime_root)
        assert report.pair_count == 1
        # focus error = 0.1, trust error = 0.1, MAE = 0.1
        assert abs(report.overall_mae - 0.1) < 0.01
        assert "focus" in report.dimension_mae
        assert "trust" in report.dimension_mae


class TestAccuracyReport:
    def test_to_dict(self):
        r = AccuracyReport(pair_count=5, overall_mae=0.15)
        d = r.to_dict()
        assert d["pair_count"] == 5
        assert d["overall_mae"] == 0.15


# ---------------------------------------------------------------------------
# ScoringCalibrator
# ---------------------------------------------------------------------------


class TestScoringCalibrator:
    def test_insufficient_data_returns_base_weights(self):
        cal = ScoringCalibrator()
        accuracy = AccuracyReport(pair_count=1)
        result = cal.calibrate(accuracy)
        assert result.adjusted_weights == result.original_weights
        assert result.dimensions_adjusted == []

    def test_calibrates_with_enough_data(self):
        cal = ScoringCalibrator(
            base_weights={"focus": 0.3, "trust": 0.3, "review": 0.4}
        )
        accuracy = AccuracyReport(
            pair_count=10,
            overall_mae=0.2,
            dimension_mae={"focus": 0.4, "trust": 0.05, "review": 0.15},
        )
        result = cal.calibrate(accuracy)
        # focus has high error → weight should decrease
        assert result.adjusted_weights["focus"] < result.original_weights["focus"]
        # trust has low error → weight should increase
        assert result.adjusted_weights["trust"] > result.original_weights["trust"]
        assert len(result.dimensions_adjusted) >= 1

    def test_weights_sum_to_one(self):
        cal = ScoringCalibrator()
        accuracy = AccuracyReport(
            pair_count=10,
            overall_mae=0.2,
            dimension_mae={
                "focus": 0.4, "automation": 0.3, "review": 0.1,
                "validation": 0.2, "knowledge": 0.15, "trust": 0.05,
            },
        )
        result = cal.calibrate(accuracy)
        total = sum(result.adjusted_weights.values())
        assert abs(total - 1.0) < 0.01


class TestCalibrationResult:
    def test_to_dict(self):
        r = CalibrationResult(
            original_weights={"focus": 0.5},
            adjusted_weights={"focus": 0.48},
            accuracy_before=0.15,
        )
        d = r.to_dict()
        assert d["accuracy_before"] == 0.15


# ---------------------------------------------------------------------------
# PolicyAdapter
# ---------------------------------------------------------------------------


class TestPolicyAdapter:
    def test_empty_portfolio(self):
        adapter = PolicyAdapter()
        result = adapter.adapt(
            {"ventures": []},
            AccuracyReport(),
            {"review_cadence": "weekly"},
        )
        assert result.portfolio_health == "empty"
        assert result.recommendations == []

    def test_stale_updates_recommend_tighter_sla(self):
        adapter = PolicyAdapter()
        state = {
            "ventures": [
                {"status": "active", "weekly_update_freshness_days": 8,
                 "last_review_days": 5, "revenue_trend": 0.05, "retention_signal": 0.5},
            ],
        }
        result = adapter.adapt(state, AccuracyReport(), {"founder_update_sla": "48h"})
        sla_recs = [r for r in result.recommendations if r.parameter == "founder_update_sla"]
        assert len(sla_recs) == 1
        assert sla_recs[0].recommended_value == "24h"

    def test_declining_revenue_recommend_validation_pressure(self):
        adapter = PolicyAdapter()
        state = {
            "ventures": [
                {"status": "active", "weekly_update_freshness_days": 2,
                 "last_review_days": 5, "revenue_trend": -0.2, "retention_signal": 0.5},
            ],
        }
        result = adapter.adapt(
            state, AccuracyReport(),
            {"validation_pressure": "design_partner_first"},
        )
        val_recs = [r for r in result.recommendations if r.parameter == "validation_pressure"]
        assert len(val_recs) == 1
        assert val_recs[0].recommended_value == "paid_every_week"

    def test_healthy_portfolio_no_changes(self):
        adapter = PolicyAdapter()
        state = {
            "ventures": [
                {"status": "active", "weekly_update_freshness_days": 2,
                 "last_review_days": 3, "revenue_trend": 0.15, "retention_signal": 0.7},
            ],
        }
        result = adapter.adapt(
            state, AccuracyReport(overall_mae=0.1),
            {"founder_update_sla": "48h", "review_cadence": "weekly",
             "validation_pressure": "paid_every_week", "knowledge_capture": "every_review"},
        )
        assert result.portfolio_health == "healthy"
        assert result.recommendations == []

    def test_critical_health(self):
        adapter = PolicyAdapter()
        state = {
            "ventures": [
                {"status": "active", "weekly_update_freshness_days": 2,
                 "last_review_days": 3, "revenue_trend": -0.3, "retention_signal": 0.1},
            ],
        }
        result = adapter.adapt(state, AccuracyReport(), {})
        assert result.portfolio_health == "critical"


class TestPolicyRecommendation:
    def test_to_dict(self):
        r = PolicyRecommendation(
            parameter="review_cadence",
            current_value="weekly",
            recommended_value="daily",
            reason="Reviews overdue",
            confidence=0.8,
        )
        d = r.to_dict()
        assert d["parameter"] == "review_cadence"


class TestAdaptationResult:
    def test_to_dict(self):
        r = AdaptationResult(portfolio_health="healthy")
        d = r.to_dict()
        assert d["portfolio_health"] == "healthy"


# ---------------------------------------------------------------------------
# Full feedback cycle
# ---------------------------------------------------------------------------


class TestFeedbackCycle:
    def test_run_feedback_cycle(self, runtime_root):
        # Seed some prediction data
        p = Prediction(
            venture_id="v-alpha", tick_number=1, source="heuristic",
            scores={"automation_coverage": 0.5},
            created_at="2026-01-01T00:00:00+00:00",
        )
        record_prediction(runtime_root, p)

        result = asyncio.run(run_feedback_cycle(runtime_root))
        assert "outcomes_recorded" in result
        assert result["outcomes_recorded"] == 1
        assert "accuracy" in result
        assert "calibration" in result
        assert "adaptation" in result

        # Check state was updated
        state = load_state(runtime_root)
        assert "scoring_weights" in state
        assert "last_feedback_cycle" in state

    def test_feedback_cycle_persists_to_log(self, runtime_root):
        asyncio.run(run_feedback_cycle(runtime_root))
        logs = read_log(runtime_root, "feedback_cycles")
        assert len(logs) == 1
        assert "cycle_at" in logs[0]
