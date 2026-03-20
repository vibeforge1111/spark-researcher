"""Tests for the notification system (Tier 3)."""

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
    VENTURE_STALE,
    REVIEW_NEEDED,
    APPLICATION_PENDING,
    KPI_MISSING,
    GOVERNANCE_QUORUM,
    AGENT_EVALUATION_COMPLETE,
    EventBus,
    IncubatorEvent,
)
from domain_chip_vibe_incubator.notifications import (
    ConsoleNotifier,
    EmailNotifier,
    NotificationRecord,
    WebhookNotifier,
)
from domain_chip_vibe_incubator.notification_router import (
    NotificationRouter,
    NotificationRule,
    _format_notification,
    _severity_level,
)
from domain_chip_vibe_incubator.ops_loop import load_state, read_log, save_state


@pytest.fixture()
def runtime_root(tmp_path: Path):
    artifacts = tmp_path / "artifacts" / "incubator_os"
    artifacts.mkdir(parents=True)
    (artifacts / "logs").mkdir()
    state = {"ventures": [], "applications": [], "founders": [], "batches": []}
    (artifacts / "state.json").write_text(json.dumps(state))
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Channel tests
# ---------------------------------------------------------------------------


class TestConsoleNotifier:
    def test_always_succeeds(self):
        n = ConsoleNotifier()
        result = asyncio.get_event_loop().run_until_complete(
            n.send("Test subject", "Test body", {"severity": "info"})
        )
        assert result is True

    def test_name(self):
        assert ConsoleNotifier().name == "console"


class TestWebhookNotifier:
    def test_unavailable_without_url(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("VIBE_WEBHOOK_URL", None)
            w = WebhookNotifier(url="")
            assert w.available is False

    def test_available_with_url(self):
        w = WebhookNotifier(url="https://example.com/hook")
        assert w.available is True

    def test_send_returns_false_when_unavailable(self):
        w = WebhookNotifier(url="")
        result = asyncio.get_event_loop().run_until_complete(
            w.send("test", "body")
        )
        assert result is False


class TestEmailNotifier:
    def test_unavailable_without_config(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=True):
            for key in ("VIBE_EMAIL_FROM", "VIBE_EMAIL_TO"):
                os.environ.pop(key, None)
            e = EmailNotifier()
            assert e.available is False


class TestNotificationRecord:
    def test_to_dict(self):
        r = NotificationRecord(
            channel="console", subject="test", body="body", success=True
        )
        d = r.to_dict()
        assert d["channel"] == "console"
        assert d["success"] is True
        assert "timestamp" in d


# ---------------------------------------------------------------------------
# Severity levels
# ---------------------------------------------------------------------------


class TestSeverityLevel:
    def test_levels(self):
        assert _severity_level("info") == 0
        assert _severity_level("warning") == 1
        assert _severity_level("critical") == 2

    def test_unknown_is_zero(self):
        assert _severity_level("unknown") == 0


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------


class TestFormatNotification:
    def test_critical_alert(self):
        event = IncubatorEvent(ALERT_CRITICAL, {
            "venture_id": "v-1", "alert": "revenue_collapse", "detail": "Revenue dropped 50%"
        })
        subject, body = _format_notification(event)
        assert "CRITICAL" in subject
        assert "v-1" in body
        assert "50%" in body

    def test_warning_alert(self):
        event = IncubatorEvent(ALERT_WARNING, {
            "venture_id": "v-2", "alert": "revenue_declining", "detail": "Revenue dropped 20%"
        })
        subject, body = _format_notification(event)
        assert "Warning" in subject

    def test_stale_venture(self):
        event = IncubatorEvent(VENTURE_STALE, {
            "venture_id": "v-3", "label": "My Venture", "freshness_days": 12
        })
        subject, body = _format_notification(event)
        assert "Stale" in subject
        assert "12 days" in body

    def test_review_needed(self):
        event = IncubatorEvent(REVIEW_NEEDED, {
            "venture_id": "v-4", "label": "Review Me", "last_review_days": 20
        })
        subject, body = _format_notification(event)
        assert "overdue" in subject.lower()

    def test_application_pending(self):
        event = IncubatorEvent(APPLICATION_PENDING, {"pending_count": 3})
        subject, body = _format_notification(event)
        assert "3" in subject

    def test_kpi_missing(self):
        event = IncubatorEvent(KPI_MISSING, {"stale_count": 2})
        subject, body = _format_notification(event)
        assert "2" in subject

    def test_governance_quorum(self):
        event = IncubatorEvent(GOVERNANCE_QUORUM, {"open_proposal_count": 1})
        subject, body = _format_notification(event)
        assert "Governance" in subject

    def test_agent_evaluation(self):
        event = IncubatorEvent(AGENT_EVALUATION_COMPLETE, {
            "venture_id": "v-5", "recommendation": "on_track", "confidence": 0.75
        })
        subject, body = _format_notification(event)
        assert "v-5" in subject
        assert "on_track" in subject

    def test_unknown_event_fallback(self):
        event = IncubatorEvent("some.unknown.event", {"foo": "bar"})
        subject, body = _format_notification(event)
        assert "some.unknown.event" in subject


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------


class TestNotificationRule:
    def test_matches_event_type(self):
        rule = NotificationRule(ALERT_CRITICAL, ["console"])
        event = IncubatorEvent(ALERT_CRITICAL, {"severity": "critical"})
        assert rule.matches(event) is True

    def test_does_not_match_wrong_type(self):
        rule = NotificationRule(ALERT_CRITICAL, ["console"])
        event = IncubatorEvent(ALERT_WARNING, {})
        assert rule.matches(event) is False

    def test_severity_filter(self):
        rule = NotificationRule(ALERT_WARNING, ["console"], min_severity="warning")
        event_info = IncubatorEvent(ALERT_WARNING, {"severity": "info"})
        event_warn = IncubatorEvent(ALERT_WARNING, {"severity": "warning"})
        assert rule.matches(event_info) is False
        assert rule.matches(event_warn) is True


class TestNotificationRouter:
    def test_router_has_console_channel(self, runtime_root):
        router = NotificationRouter(runtime_root)
        assert "console" in router.available_channels

    def test_router_history_starts_empty(self, runtime_root):
        router = NotificationRouter(runtime_root)
        assert router.history == []

    def test_send_test(self, runtime_root):
        router = NotificationRouter(runtime_root)
        record = asyncio.get_event_loop().run_until_complete(
            router.send_test("console")
        )
        assert record.success is True
        assert record.channel == "console"
        assert "Test notification" in record.subject

    def test_send_test_unavailable_channel(self, runtime_root):
        router = NotificationRouter(runtime_root)
        record = asyncio.get_event_loop().run_until_complete(
            router.send_test("nonexistent")
        )
        assert record.success is False

    def test_wire_receives_events(self, runtime_root):
        router = NotificationRouter(runtime_root)
        bus = EventBus()
        router.wire(bus)

        # Publish a critical alert
        bus.publish(IncubatorEvent(ALERT_CRITICAL, {
            "venture_id": "v-1", "alert": "test", "detail": "test detail"
        }))

        # Console notification should have fired — check notification log
        notifications = read_log(runtime_root, "notifications")
        assert len(notifications) >= 1
        assert any("CRITICAL" in n.get("subject", "") for n in notifications)
