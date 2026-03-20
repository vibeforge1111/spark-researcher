"""Notification channels for the Vibe Incubator.

Channels deliver formatted messages when incubator events fire.
Each channel implements the ``NotificationChannel`` protocol.

Supported: console, webhook, email (SMTP).  No Slack.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import smtplib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any, Protocol

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Channel protocol
# ---------------------------------------------------------------------------

class NotificationChannel(Protocol):
    """Any object that can send a notification."""

    name: str

    async def send(self, subject: str, body: str, metadata: dict[str, Any] | None = None) -> bool:
        """Send a notification.  Return True on success."""
        ...


# ---------------------------------------------------------------------------
# Notification record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NotificationRecord:
    """Immutable record of a sent notification."""
    channel: str
    subject: str
    body: str
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "subject": self.subject,
            "body": self.body,
            "success": self.success,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Console channel (always available)
# ---------------------------------------------------------------------------

class ConsoleNotifier:
    """Prints notifications to stdout.  Always succeeds."""

    name = "console"

    async def send(self, subject: str, body: str, metadata: dict[str, Any] | None = None) -> bool:
        prefix = "[VIBE-NOTIFY]"
        severity = (metadata or {}).get("severity", "info")
        print(f"{prefix} [{severity.upper()}] {subject}")
        if body:
            for line in body.splitlines():
                print(f"  {line}")
        return True


# ---------------------------------------------------------------------------
# Webhook channel
# ---------------------------------------------------------------------------

class WebhookNotifier:
    """POSTs JSON payloads to a configured URL.

    Env: ``VIBE_WEBHOOK_URL`` — if unset, channel is disabled.
    Optional: ``VIBE_WEBHOOK_SECRET`` — included as X-Webhook-Secret header.
    """

    name = "webhook"

    def __init__(self, url: str | None = None, secret: str | None = None) -> None:
        self.url = url or os.environ.get("VIBE_WEBHOOK_URL", "")
        self.secret = secret or os.environ.get("VIBE_WEBHOOK_SECRET", "")

    @property
    def available(self) -> bool:
        return bool(self.url)

    async def send(self, subject: str, body: str, metadata: dict[str, Any] | None = None) -> bool:
        if not self.available:
            log.debug("Webhook not configured — skipping")
            return False

        payload = {
            "subject": subject,
            "body": body,
            "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat(),
            **(metadata or {}),
        }
        headers = {"Content-Type": "application/json"}
        if self.secret:
            headers["X-Webhook-Secret"] = self.secret

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    ok = 200 <= resp.status < 300
                    if not ok:
                        log.warning("Webhook returned %d: %s", resp.status, await resp.text())
                    return ok
        except ImportError:
            log.warning("aiohttp not installed — webhook disabled")
            return False
        except Exception:
            log.exception("Webhook send failed")
            return False


# ---------------------------------------------------------------------------
# Email channel (SMTP)
# ---------------------------------------------------------------------------

class EmailNotifier:
    """Sends email via SMTP.

    Env vars:
    - ``VIBE_SMTP_HOST`` (default: localhost)
    - ``VIBE_SMTP_PORT`` (default: 587)
    - ``VIBE_SMTP_USER`` / ``VIBE_SMTP_PASS`` (optional, for auth)
    - ``VIBE_EMAIL_FROM`` (required)
    - ``VIBE_EMAIL_TO`` (comma-separated recipients, required)
    """

    name = "email"

    def __init__(self) -> None:
        self.host = os.environ.get("VIBE_SMTP_HOST", "localhost")
        self.port = int(os.environ.get("VIBE_SMTP_PORT", "587"))
        self.user = os.environ.get("VIBE_SMTP_USER", "")
        self.password = os.environ.get("VIBE_SMTP_PASS", "")
        self.from_addr = os.environ.get("VIBE_EMAIL_FROM", "")
        self.to_addrs = [a.strip() for a in os.environ.get("VIBE_EMAIL_TO", "").split(",") if a.strip()]

    @property
    def available(self) -> bool:
        return bool(self.from_addr and self.to_addrs)

    async def send(self, subject: str, body: str, metadata: dict[str, Any] | None = None) -> bool:
        if not self.available:
            log.debug("Email not configured — skipping")
            return False

        msg = EmailMessage()
        msg["Subject"] = f"[Vibe Incubator] {subject}"
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg.set_content(body)

        try:
            # Run SMTP in thread to avoid blocking event loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._send_smtp, msg)
            return True
        except Exception:
            log.exception("Email send failed")
            return False

    def _send_smtp(self, msg: EmailMessage) -> None:
        with smtplib.SMTP(self.host, self.port, timeout=15) as server:
            server.ehlo()
            if self.port != 25:
                server.starttls()
            if self.user and self.password:
                server.login(self.user, self.password)
            server.send_message(msg)
