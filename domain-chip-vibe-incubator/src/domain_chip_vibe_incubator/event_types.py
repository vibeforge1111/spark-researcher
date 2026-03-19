"""Typed event system for the Vibe Incubator autonomous loop.

Events flow from the ops loop through the EventBus to subscribers
(notification router, dashboard SSE, agent orchestrator, etc.).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

TICK_COMPLETED = "tick.completed"
ALERT_CRITICAL = "alert.critical"
ALERT_WARNING = "alert.warning"
REVIEW_NEEDED = "review.needed"
VENTURE_STALE = "venture.stale"
APPLICATION_PENDING = "application.pending"
BATCH_ADVANCED = "batch.week_advanced"
GOVERNANCE_QUORUM = "governance.quorum_reached"
KPI_MISSING = "kpi.missing"
EXPERIMENT_STALE = "experiment.stale"
SCHEDULER_STARTED = "scheduler.started"
SCHEDULER_STOPPED = "scheduler.stopped"


# ---------------------------------------------------------------------------
# Event data class
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IncubatorEvent:
    """Immutable event emitted by the incubator ops loop."""

    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# EventBus — lightweight pub/sub
# ---------------------------------------------------------------------------

EventHandler = Callable[[IncubatorEvent], None]


class EventBus:
    """Simple synchronous publish/subscribe bus for incubator events.

    Subscribers are called in registration order.  A failing subscriber
    is logged but does not block other subscribers.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._global_handlers: list[EventHandler] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe *handler* to a specific *event_type*."""
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe *handler* to **all** event types."""
        self._global_handlers.append(handler)

    def publish(self, event: IncubatorEvent) -> None:
        """Dispatch *event* to all matching subscribers."""
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception:
                log.exception("Global event handler failed for %s", event.event_type)

        for handler in self._handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception:
                log.exception("Event handler failed for %s", event.event_type)

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._handlers.clear()
        self._global_handlers.clear()
