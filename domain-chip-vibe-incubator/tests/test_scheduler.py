"""Tests for the event system and autonomous scheduler."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from domain_chip_vibe_incubator.event_types import (
    ALERT_CRITICAL,
    ALERT_WARNING,
    APPLICATION_PENDING,
    REVIEW_NEEDED,
    TICK_COMPLETED,
    VENTURE_STALE,
    EventBus,
    IncubatorEvent,
)
from domain_chip_vibe_incubator.ops_loop import (
    append_log,
    load_state,
    read_log,
    refresh_ops_artifacts,
    save_state,
)
from domain_chip_vibe_incubator.scheduler import (
    IncubatorScheduler,
    emit_event_log,
)


@pytest.fixture()
def runtime_root(tmp_path: Path):
    """Minimal runtime root with seed state."""
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
                "distribution_engine": "operator_content",
                "build_stack": "template_factory",
                "automation_coverage": 0.5,
                "weekly_revenue": 200,
                "customer_conversations_this_week": 2,
                "paid_signals_this_week": 1,
                "active_users": 3,
                "weekly_update_freshness_days": 3,
                "last_review_days": 5,
                "trust_review_status": "green",
                "open_pipeline_count": 1,
            },
        ],
        "applications": [
            {"application_id": "app-1", "label": "Pending App", "status": "pending"},
        ],
        "founders": [],
        "batches": [],
    }
    (artifacts / "state.json").write_text(json.dumps(state))
    return str(tmp_path)


# ---------------------------------------------------------------------------
# EventBus tests
# ---------------------------------------------------------------------------


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe(TICK_COMPLETED, lambda e: received.append(e))

        event = IncubatorEvent(TICK_COMPLETED, {"tick": 1})
        bus.publish(event)

        assert len(received) == 1
        assert received[0].event_type == TICK_COMPLETED
        assert received[0].payload["tick"] == 1

    def test_subscribe_all(self):
        bus = EventBus()
        received = []
        bus.subscribe_all(lambda e: received.append(e))

        bus.publish(IncubatorEvent(TICK_COMPLETED, {}))
        bus.publish(IncubatorEvent(ALERT_CRITICAL, {}))

        assert len(received) == 2
        assert received[0].event_type == TICK_COMPLETED
        assert received[1].event_type == ALERT_CRITICAL

    def test_handler_failure_does_not_block_others(self):
        bus = EventBus()
        received = []

        def bad_handler(e):
            raise RuntimeError("boom")

        bus.subscribe(TICK_COMPLETED, bad_handler)
        bus.subscribe(TICK_COMPLETED, lambda e: received.append(e))

        bus.publish(IncubatorEvent(TICK_COMPLETED, {}))
        assert len(received) == 1  # second handler still ran

    def test_clear(self):
        bus = EventBus()
        received = []
        bus.subscribe(TICK_COMPLETED, lambda e: received.append(e))
        bus.clear()
        bus.publish(IncubatorEvent(TICK_COMPLETED, {}))
        assert len(received) == 0

    def test_to_dict(self):
        event = IncubatorEvent(ALERT_WARNING, {"venture_id": "v1"})
        d = event.to_dict()
        assert d["event_type"] == ALERT_WARNING
        assert d["payload"]["venture_id"] == "v1"
        assert "timestamp" in d


# ---------------------------------------------------------------------------
# Event log persistence
# ---------------------------------------------------------------------------


class TestEventLog:
    def test_emit_event_log_persists(self, runtime_root):
        event = IncubatorEvent(TICK_COMPLETED, {"tick": 42})
        emit_event_log(runtime_root, event)

        events = read_log(runtime_root, "events")
        assert len(events) == 1
        assert events[0]["event_type"] == TICK_COMPLETED
        assert events[0]["payload"]["tick"] == 42

    def test_multiple_events_append(self, runtime_root):
        emit_event_log(runtime_root, IncubatorEvent(TICK_COMPLETED, {"n": 1}))
        emit_event_log(runtime_root, IncubatorEvent(ALERT_CRITICAL, {"n": 2}))
        emit_event_log(runtime_root, IncubatorEvent(VENTURE_STALE, {"n": 3}))

        events = read_log(runtime_root, "events")
        assert len(events) == 3
        types = [e["event_type"] for e in events]
        assert TICK_COMPLETED in types
        assert ALERT_CRITICAL in types
        assert VENTURE_STALE in types


# ---------------------------------------------------------------------------
# Scheduler tick tests
# ---------------------------------------------------------------------------


class TestSchedulerTick:
    def test_single_tick_produces_artifacts(self, runtime_root):
        scheduler = IncubatorScheduler(runtime_root=runtime_root, tick_interval_seconds=9999)
        result = asyncio.get_event_loop().run_until_complete(scheduler._tick())

        assert "tick" in result
        assert "metrics" in result
        assert result["tick"]["metrics"]["active_portfolio_count"] == 1
        assert scheduler._tick_count == 1
        assert scheduler._last_tick_at is not None

    def test_tick_stamps_last_tick_at_on_state(self, runtime_root):
        scheduler = IncubatorScheduler(runtime_root=runtime_root)
        asyncio.get_event_loop().run_until_complete(scheduler._tick())

        state = load_state(runtime_root)
        assert "last_tick_at" in state
        assert state["last_tick_at"] is not None

    def test_tick_emits_events(self, runtime_root):
        scheduler = IncubatorScheduler(runtime_root=runtime_root)
        received = []
        scheduler.bus.subscribe_all(lambda e: received.append(e))

        asyncio.get_event_loop().run_until_complete(scheduler._tick())

        types = [e.event_type for e in received]
        assert TICK_COMPLETED in types
        # At minimum tick.completed always fires; other events depend on state
        assert len(received) >= 1

    def test_tick_idempotent(self, runtime_root):
        scheduler = IncubatorScheduler(runtime_root=runtime_root)
        r1 = asyncio.get_event_loop().run_until_complete(scheduler._tick())
        r2 = asyncio.get_event_loop().run_until_complete(scheduler._tick())

        # Same state → same compound score
        score1 = r1["tick"]["metrics"]["incubator_compound_score"]
        score2 = r2["tick"]["metrics"]["incubator_compound_score"]
        assert score1 == score2
        assert scheduler._tick_count == 2

    def test_tick_events_persisted_to_log(self, runtime_root):
        scheduler = IncubatorScheduler(runtime_root=runtime_root)
        asyncio.get_event_loop().run_until_complete(scheduler._tick())

        events = read_log(runtime_root, "events")
        assert len(events) > 0
        assert any(e["event_type"] == TICK_COMPLETED for e in events)


# ---------------------------------------------------------------------------
# Age tick tests
# ---------------------------------------------------------------------------


class TestAgeTick:
    def test_age_tick_increments_freshness(self, runtime_root):
        state = load_state(runtime_root)
        original_freshness = state["ventures"][0]["weekly_update_freshness_days"]

        scheduler = IncubatorScheduler(runtime_root=runtime_root, age_interval_hours=0)
        # Force the age tick by setting last_age_at to 0 (default)
        asyncio.get_event_loop().run_until_complete(scheduler._maybe_age_tick())

        state = load_state(runtime_root)
        assert state["ventures"][0]["weekly_update_freshness_days"] == original_freshness + 1
        assert state["ventures"][0]["last_review_days"] == 6  # was 5

    def test_age_tick_skips_archived(self, runtime_root):
        state = load_state(runtime_root)
        state["ventures"].append({
            "venture_id": "v-archived",
            "label": "Archived",
            "status": "archived",
            "weekly_update_freshness_days": 0,
            "last_review_days": 0,
        })
        save_state(runtime_root, state)

        scheduler = IncubatorScheduler(runtime_root=runtime_root, age_interval_hours=0)
        asyncio.get_event_loop().run_until_complete(scheduler._maybe_age_tick())

        state = load_state(runtime_root)
        archived = [v for v in state["ventures"] if v["venture_id"] == "v-archived"][0]
        assert archived["weekly_update_freshness_days"] == 0  # not incremented


# ---------------------------------------------------------------------------
# Stale venture event emission
# ---------------------------------------------------------------------------


class TestStaleVentureEvents:
    def test_stale_venture_emits_event(self, runtime_root):
        state = load_state(runtime_root)
        state["ventures"][0]["weekly_update_freshness_days"] = 10
        save_state(runtime_root, state)

        scheduler = IncubatorScheduler(runtime_root=runtime_root)
        received = []
        scheduler.bus.subscribe(VENTURE_STALE, lambda e: received.append(e))

        asyncio.get_event_loop().run_until_complete(scheduler._tick())

        assert len(received) == 1
        assert received[0].payload["venture_id"] == "v-alpha"
        assert received[0].payload["freshness_days"] == 10

    def test_review_needed_emits_event(self, runtime_root):
        state = load_state(runtime_root)
        state["ventures"][0]["last_review_days"] = 20
        save_state(runtime_root, state)

        scheduler = IncubatorScheduler(runtime_root=runtime_root)
        received = []
        scheduler.bus.subscribe(REVIEW_NEEDED, lambda e: received.append(e))

        asyncio.get_event_loop().run_until_complete(scheduler._tick())

        assert len(received) == 1
        assert received[0].payload["last_review_days"] == 20


# ---------------------------------------------------------------------------
# Scheduler status
# ---------------------------------------------------------------------------


class TestSchedulerStatus:
    def test_status_before_tick(self, runtime_root):
        scheduler = IncubatorScheduler(runtime_root=runtime_root)
        s = scheduler.status
        assert s["running"] is False
        assert s["tick_count"] == 0
        assert s["last_tick_at"] is None

    def test_status_after_tick(self, runtime_root):
        scheduler = IncubatorScheduler(runtime_root=runtime_root)
        asyncio.get_event_loop().run_until_complete(scheduler._tick())
        s = scheduler.status
        assert s["running"] is False  # not in run loop, just direct _tick()
        assert s["tick_count"] == 1
        assert s["last_tick_at"] is not None
