"""Autonomous scheduler for the Vibe Incubator.

Runs the ops loop on a configurable timer, emits events, and
manages daily/weekly maintenance ticks.

Usage:
    python -m domain_chip_vibe_incubator.scheduler
    python -m domain_chip_vibe_incubator.scheduler --interval 60 --runtime-root /path
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .event_types import (
    AGENT_EVALUATION_COMPLETE,
    ALERT_CRITICAL,
    ALERT_WARNING,
    APPLICATION_PENDING,
    GOVERNANCE_QUORUM,
    KPI_MISSING,
    REVIEW_NEEDED,
    SCHEDULER_STARTED,
    SCHEDULER_STOPPED,
    TICK_COMPLETED,
    VENTURE_STALE,
    EventBus,
    IncubatorEvent,
)
from .ops_loop import (
    append_log,
    default_runtime_root,
    load_state,
    ops_write_lock,
    read_log,
    refresh_ops_artifacts,
    save_state,
)

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Event log persistence
# ---------------------------------------------------------------------------

def emit_event_log(runtime_root: str, event: IncubatorEvent) -> None:
    """Append an event to the events.jsonl log."""
    append_log(runtime_root, "events", event.to_dict())


# ---------------------------------------------------------------------------
# IncubatorScheduler
# ---------------------------------------------------------------------------

class IncubatorScheduler:
    """Autonomous tick scheduler for the incubator ops loop.

    Wraps ``refresh_ops_artifacts()`` in a timed loop and emits events
    when state changes are detected (alerts, stale ventures, etc.).
    """

    def __init__(
        self,
        runtime_root: str | None = None,
        tick_interval_seconds: int = 300,
        age_interval_hours: int = 24,
        weekly_review_day: int = 0,  # Monday
        daily_digest_hour: int = 9,
    ) -> None:
        self.runtime_root = runtime_root or default_runtime_root()
        self.tick_interval = tick_interval_seconds
        self.age_interval = age_interval_hours * 3600
        self.weekly_review_day = weekly_review_day
        self.daily_digest_hour = daily_digest_hour

        self.bus = EventBus()
        self._running = False
        self._tick_count = 0
        self._last_tick_at: str | None = None
        self._last_age_at: float = 0.0
        self._last_weekly_at: str | None = None
        self._llm_tick_cadence = int(os.environ.get("VIBE_LLM_TICK_CADENCE", "6"))
        self._last_llm_results: dict[str, Any] = {}

        # Wire up persistent event logging
        self.bus.subscribe_all(lambda e: emit_event_log(self.runtime_root, e))

    # -- public API --

    @property
    def status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "tick_count": self._tick_count,
            "last_tick_at": self._last_tick_at,
            "tick_interval_seconds": self.tick_interval,
            "runtime_root": self.runtime_root,
            "llm_tick_cadence": self._llm_tick_cadence,
            "llm_last_results": self._last_llm_results,
        }

    async def run(self) -> None:
        """Main event loop.  Runs until cancelled or ``stop()`` is called."""
        self._running = True
        log.info(
            "Scheduler started  runtime_root=%s  interval=%ds",
            self.runtime_root, self.tick_interval,
        )
        self.bus.publish(IncubatorEvent(SCHEDULER_STARTED, {"runtime_root": self.runtime_root}))

        try:
            while self._running:
                await self._tick()
                await self._maybe_age_tick()
                await self._maybe_weekly_tick()
                await self._maybe_llm_tick()
                await asyncio.sleep(self.tick_interval)
        except asyncio.CancelledError:
            log.info("Scheduler cancelled")
        finally:
            self._running = False
            self.bus.publish(IncubatorEvent(SCHEDULER_STOPPED))
            log.info("Scheduler stopped  ticks=%d", self._tick_count)

    def stop(self) -> None:
        """Signal the loop to stop after the current tick."""
        self._running = False

    # -- tick logic --

    async def _tick(self) -> dict[str, Any]:
        """Single ops tick: refresh artifacts, check alerts, emit events."""
        log.debug("Tick #%d starting", self._tick_count + 1)
        try:
            with ops_write_lock(self.runtime_root):
                refreshed = refresh_ops_artifacts(self.runtime_root)
                # Stamp last_tick_at onto state
                state = load_state(self.runtime_root)
                state["last_tick_at"] = _now_iso()
                save_state(self.runtime_root, state)
        except Exception:
            log.exception("Tick failed")
            return {}

        self._tick_count += 1
        self._last_tick_at = _now_iso()

        self._emit_tick_events(refreshed)
        return refreshed

    async def _maybe_age_tick(self) -> None:
        """Increment freshness counters once per age_interval."""
        import time
        now = time.monotonic()
        if now - self._last_age_at < self.age_interval:
            return
        self._last_age_at = now

        log.info("Running daily age tick")
        try:
            with ops_write_lock(self.runtime_root):
                state = load_state(self.runtime_root)
                for venture in state.get("ventures", []):
                    if not isinstance(venture, dict):
                        continue
                    if str(venture.get("status") or "") in {"archived", "stopped"}:
                        continue
                    venture["weekly_update_freshness_days"] = int(venture.get("weekly_update_freshness_days", 0) or 0) + 1
                    venture["last_review_days"] = int(venture.get("last_review_days", 0) or 0) + 1
                    venture["founder_update_latency_hours"] = int(venture.get("founder_update_latency_hours", 0) or 0) + 6
                save_state(self.runtime_root, state)
                append_log(self.runtime_root, "time_passage", {
                    "days": 1, "venture_id": "", "touched_ventures": "all_active", "note": "scheduler_auto_age",
                })
        except Exception:
            log.exception("Age tick failed")

    async def _maybe_weekly_tick(self) -> None:
        """Run weekly maintenance on the configured day."""
        now = datetime.now(UTC)
        if now.weekday() != self.weekly_review_day:
            return
        today_key = now.strftime("%Y-%m-%d")
        if self._last_weekly_at == today_key:
            return
        self._last_weekly_at = today_key

        log.info("Running weekly review tick")
        try:
            # Auto-tally any governance proposals that have enough votes
            proposals = read_log(self.runtime_root, "governance_proposals")
            votes = read_log(self.runtime_root, "governance_votes")
            open_proposals = [p for p in proposals if isinstance(p, dict) and p.get("status") == "open"]
            if open_proposals:
                self.bus.publish(IncubatorEvent(GOVERNANCE_QUORUM, {
                    "open_proposal_count": len(open_proposals),
                }))
        except Exception:
            log.exception("Weekly tick failed")

    async def _maybe_llm_tick(self) -> None:
        """Run LLM evaluation on active ventures every N ticks."""
        if self._llm_tick_cadence <= 0 or self._tick_count % self._llm_tick_cadence != 0:
            return

        try:
            from .agents import VentureAnalystAgent
            agent = VentureAnalystAgent()
            if not agent.available:
                return
        except Exception:
            return  # anthropic not installed or other import error

        log.info("Running LLM evaluation tick")
        try:
            state = load_state(self.runtime_root)
            active = [v for v in state.get("ventures", []) if isinstance(v, dict) and v.get("status") == "active"]
            for venture in active:
                result = await agent.evaluate(venture)
                if result is None:
                    continue
                vid = str(venture.get("venture_id", ""))
                self._last_llm_results[vid] = {
                    "scores": result.scores,
                    "reasoning": result.reasoning,
                    "recommendation": result.recommendation,
                    "confidence": result.confidence,
                    "evaluated_at": _now_iso(),
                }
                # Persist to venture state
                venture["llm_assessment"] = self._last_llm_results[vid]
                self.bus.publish(IncubatorEvent(AGENT_EVALUATION_COMPLETE, {
                    "venture_id": vid,
                    "recommendation": result.recommendation,
                    "confidence": result.confidence,
                }))

            with ops_write_lock(self.runtime_root):
                save_state(self.runtime_root, state)
        except Exception:
            log.exception("LLM evaluation tick failed")

    # -- event emission --

    def _emit_tick_events(self, refreshed: dict[str, Any]) -> None:
        """Inspect refreshed tick data and emit typed events."""
        tick = refreshed.get("tick", {})
        state = refreshed.get("state", {})
        metrics = tick.get("metrics", {})

        # Always emit tick completed
        self.bus.publish(IncubatorEvent(TICK_COMPLETED, {
            "tick_number": self._tick_count,
            "compound_score": metrics.get("incubator_compound_score"),
            "active_count": metrics.get("active_portfolio_count"),
            "alert_count": tick.get("critical_alert_count", 0) + tick.get("warning_alert_count", 0),
        }))

        # Health alerts
        for alert in tick.get("health_alerts", []):
            event_type = ALERT_CRITICAL if alert.get("severity") == "critical" else ALERT_WARNING
            self.bus.publish(IncubatorEvent(event_type, alert))

        # Stale ventures (no update in >7 days)
        for venture in state.get("ventures", []):
            if not isinstance(venture, dict):
                continue
            if str(venture.get("status") or "") != "active":
                continue
            freshness = int(venture.get("weekly_update_freshness_days", 0) or 0)
            if freshness > 7:
                self.bus.publish(IncubatorEvent(VENTURE_STALE, {
                    "venture_id": venture.get("venture_id"),
                    "label": venture.get("label"),
                    "freshness_days": freshness,
                }))

            # Review needed (>14 days since last review)
            review_days = int(venture.get("last_review_days", 0) or 0)
            if review_days > 14:
                self.bus.publish(IncubatorEvent(REVIEW_NEEDED, {
                    "venture_id": venture.get("venture_id"),
                    "label": venture.get("label"),
                    "last_review_days": review_days,
                }))

        # Pending applications
        pending = tick.get("pending_application_count", 0)
        if pending > 0:
            self.bus.publish(IncubatorEvent(APPLICATION_PENDING, {
                "pending_count": pending,
            }))

        # Stale KPIs
        stale_kpi = tick.get("stale_kpi_count", 0)
        if stale_kpi > 0:
            self.bus.publish(IncubatorEvent(KPI_MISSING, {
                "stale_count": stale_kpi,
            }))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main_cli() -> None:
    """Entry point for ``vibe-incubator-daemon`` script."""
    parser = argparse.ArgumentParser(description="Vibe Incubator autonomous scheduler")
    parser.add_argument("--runtime-root", default=None, help="Path to runtime data directory")
    parser.add_argument("--interval", type=int, default=300, help="Tick interval in seconds (default: 300)")
    parser.add_argument("--age-interval", type=int, default=24, help="Age tick interval in hours (default: 24)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    scheduler = IncubatorScheduler(
        runtime_root=args.runtime_root,
        tick_interval_seconds=args.interval,
        age_interval_hours=args.age_interval,
    )

    loop = asyncio.new_event_loop()

    # Graceful shutdown on SIGINT / SIGTERM
    def _shutdown(sig: int, frame: Any) -> None:
        log.info("Received signal %d, shutting down...", sig)
        scheduler.stop()

    signal.signal(signal.SIGINT, _shutdown)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(scheduler.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main_cli()
