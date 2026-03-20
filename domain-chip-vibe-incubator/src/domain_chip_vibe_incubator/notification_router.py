"""Event-to-notification routing for the Vibe Incubator.

The ``NotificationRouter`` subscribes to the EventBus and dispatches
formatted notifications to the appropriate channels based on rules.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .event_types import (
    AGENT_EVALUATION_COMPLETE,
    ALERT_CRITICAL,
    ALERT_WARNING,
    APPLICATION_PENDING,
    GOVERNANCE_QUORUM,
    KPI_MISSING,
    REVIEW_NEEDED,
    TICK_COMPLETED,
    VENTURE_STALE,
    EventBus,
    IncubatorEvent,
)
from .notifications import (
    ConsoleNotifier,
    EmailNotifier,
    NotificationChannel,
    NotificationRecord,
    WebhookNotifier,
)
from .ops_loop import append_log

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Notification rule
# ---------------------------------------------------------------------------

@dataclass
class NotificationRule:
    """Maps an event type to channels + severity filter."""
    event_type: str
    channels: list[str]  # channel names: "console", "webhook", "email"
    min_severity: str = "info"  # "info", "warning", "critical"

    def matches(self, event: IncubatorEvent) -> bool:
        if event.event_type != self.event_type:
            return False
        severity = event.payload.get("severity", "info")
        return _severity_level(severity) >= _severity_level(self.min_severity)


def _severity_level(s: str) -> int:
    return {"info": 0, "warning": 1, "critical": 2}.get(s, 0)


# ---------------------------------------------------------------------------
# Default rules
# ---------------------------------------------------------------------------

DEFAULT_RULES: list[NotificationRule] = [
    # Critical alerts → all channels
    NotificationRule(ALERT_CRITICAL, ["console", "webhook", "email"]),
    # Warning alerts → console + webhook
    NotificationRule(ALERT_WARNING, ["console", "webhook"]),
    # Stale ventures → console + webhook
    NotificationRule(VENTURE_STALE, ["console", "webhook"]),
    # Review needed → console + webhook
    NotificationRule(REVIEW_NEEDED, ["console", "webhook"]),
    # Applications pending → console
    NotificationRule(APPLICATION_PENDING, ["console"]),
    # KPI missing → console + webhook
    NotificationRule(KPI_MISSING, ["console", "webhook"]),
    # Governance quorum → console + email
    NotificationRule(GOVERNANCE_QUORUM, ["console", "email"]),
    # Agent evaluation → console only (high volume)
    NotificationRule(AGENT_EVALUATION_COMPLETE, ["console"]),
]


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------

def _format_notification(event: IncubatorEvent) -> tuple[str, str]:
    """Return (subject, body) for an event."""
    payload = event.payload
    etype = event.event_type

    if etype == ALERT_CRITICAL:
        vid = payload.get("venture_id", "unknown")
        detail = payload.get("detail", "No details")
        return (
            f"CRITICAL: {payload.get('alert', 'alert')} — {vid}",
            f"Venture: {vid}\nAlert: {payload.get('alert', '')}\nDetail: {detail}\nTime: {event.timestamp}",
        )

    if etype == ALERT_WARNING:
        vid = payload.get("venture_id", "unknown")
        detail = payload.get("detail", "No details")
        return (
            f"Warning: {payload.get('alert', 'alert')} — {vid}",
            f"Venture: {vid}\nAlert: {payload.get('alert', '')}\nDetail: {detail}\nTime: {event.timestamp}",
        )

    if etype == VENTURE_STALE:
        vid = payload.get("venture_id", "unknown")
        days = payload.get("freshness_days", "?")
        return (
            f"Stale venture: {payload.get('label', vid)}",
            f"Venture {vid} has not been updated in {days} days.\nLast update was over a week ago — check in with founder.",
        )

    if etype == REVIEW_NEEDED:
        vid = payload.get("venture_id", "unknown")
        days = payload.get("last_review_days", "?")
        return (
            f"Review overdue: {payload.get('label', vid)}",
            f"Venture {vid} has not been reviewed in {days} days.\nSchedule a review session.",
        )

    if etype == APPLICATION_PENDING:
        count = payload.get("pending_count", 0)
        return (
            f"{count} pending application(s)",
            f"There are {count} applications waiting for review.\nRun admissions review to process them.",
        )

    if etype == KPI_MISSING:
        count = payload.get("stale_count", 0)
        return (
            f"{count} venture(s) with stale KPIs",
            f"{count} active ventures have not reported KPIs recently.\nRequest updates from founders.",
        )

    if etype == GOVERNANCE_QUORUM:
        count = payload.get("open_proposal_count", 0)
        return (
            f"Governance: {count} open proposal(s) ready for tally",
            f"{count} governance proposals have enough votes for resolution.\nRun governance tally to resolve.",
        )

    if etype == AGENT_EVALUATION_COMPLETE:
        vid = payload.get("venture_id", "unknown")
        rec = payload.get("recommendation", "")
        conf = payload.get("confidence", 0)
        return (
            f"Agent evaluated {vid}: {rec}",
            f"Venture: {vid}\nRecommendation: {rec}\nConfidence: {conf:.0%}",
        )

    # Fallback
    return (
        f"Event: {etype}",
        f"Payload: {payload}\nTime: {event.timestamp}",
    )


# ---------------------------------------------------------------------------
# NotificationRouter
# ---------------------------------------------------------------------------

class NotificationRouter:
    """Routes incubator events to notification channels.

    Instantiate with a runtime_root (for logging) and optional custom rules.
    Call ``wire(bus)`` to subscribe to an EventBus.
    """

    def __init__(
        self,
        runtime_root: str,
        rules: list[NotificationRule] | None = None,
    ) -> None:
        self.runtime_root = runtime_root
        self.rules = rules or list(DEFAULT_RULES)
        self._history: list[NotificationRecord] = []

        # Build available channels
        self._channels: dict[str, NotificationChannel] = {}
        self._channels["console"] = ConsoleNotifier()

        webhook = WebhookNotifier()
        if webhook.available:
            self._channels["webhook"] = webhook

        email = EmailNotifier()
        if email.available:
            self._channels["email"] = email

    @property
    def available_channels(self) -> list[str]:
        return list(self._channels.keys())

    @property
    def history(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-100:]]  # last 100

    def wire(self, bus: EventBus) -> None:
        """Subscribe to all events on the bus."""
        bus.subscribe_all(self._handle_event)

    def _handle_event(self, event: IncubatorEvent) -> None:
        """Synchronous handler called by EventBus.publish()."""
        for rule in self.rules:
            if not rule.matches(event):
                continue
            subject, body = _format_notification(event)
            metadata = {
                "event_type": event.event_type,
                "severity": event.payload.get("severity", "info"),
            }
            for channel_name in rule.channels:
                channel = self._channels.get(channel_name)
                if channel is None:
                    continue
                try:
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        # We're inside an async context — schedule as task
                        loop.create_task(self._send_and_record(channel, subject, body, metadata))
                    except RuntimeError:
                        # No running loop — run in a fresh loop
                        loop = asyncio.new_event_loop()
                        try:
                            loop.run_until_complete(self._send_and_record(channel, subject, body, metadata))
                        finally:
                            loop.close()
                except Exception:
                    log.exception("Failed to dispatch notification to %s", channel_name)

    async def _send_and_record(
        self,
        channel: NotificationChannel,
        subject: str,
        body: str,
        metadata: dict[str, Any],
    ) -> None:
        """Send via channel and record the result."""
        success = await channel.send(subject, body, metadata)
        record = NotificationRecord(
            channel=channel.name,
            subject=subject,
            body=body,
            success=success,
            metadata=metadata,
        )
        self._history.append(record)

        # Persist to log
        try:
            append_log(self.runtime_root, "notifications", record.to_dict())
        except Exception:
            log.exception("Failed to persist notification record")

    async def send_test(self, channel_name: str = "console") -> NotificationRecord:
        """Send a test notification to verify channel connectivity."""
        channel = self._channels.get(channel_name)
        if channel is None:
            return NotificationRecord(
                channel=channel_name, subject="test", body="", success=False,
                metadata={"error": f"Channel '{channel_name}' not available"},
            )
        subject = "Test notification from Vibe Incubator"
        body = f"This is a test notification sent at {datetime.now(UTC).replace(microsecond=0).isoformat()}.\nIf you see this, the {channel_name} channel is working."
        success = await channel.send(subject, body, {"severity": "info", "test": True})
        record = NotificationRecord(
            channel=channel_name, subject=subject, body=body, success=success,
            metadata={"test": True},
        )
        self._history.append(record)
        return record
