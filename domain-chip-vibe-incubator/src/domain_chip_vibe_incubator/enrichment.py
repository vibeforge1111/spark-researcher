"""Venture enrichment orchestrator.

Coordinates data sources, manages cooldowns, and stores enrichment
records on venture state.

Enrichment runs on a configurable cadence (default: every 6 hours).
Per-venture cooldown prevents re-enriching too frequently (default: 7 days).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from .data_sources.base import EnrichmentResult
from .data_sources.web_search import WebSearchSource
from .data_sources.twitter_signals import TwitterSignalsSource
from .ops_loop import append_log, load_state, ops_write_lock, save_state

log = logging.getLogger(__name__)

DEFAULT_COOLDOWN_DAYS = 7
DEFAULT_ENRICHMENT_INTERVAL_HOURS = 6


@dataclass
class EnrichmentRecord:
    """Aggregated enrichment data for a single venture."""
    venture_id: str
    results: list[dict[str, Any]] = field(default_factory=list)
    source_count: int = 0
    total_results: int = 0
    enriched_at: str = field(default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat())
    competitor_count: int = 0
    market_signal_count: int = 0
    overall_sentiment: str = "neutral"

    def to_dict(self) -> dict[str, Any]:
        return {
            "venture_id": self.venture_id,
            "results": self.results,
            "source_count": self.source_count,
            "total_results": self.total_results,
            "enriched_at": self.enriched_at,
            "competitor_count": self.competitor_count,
            "market_signal_count": self.market_signal_count,
            "overall_sentiment": self.overall_sentiment,
        }


def _needs_enrichment(venture: dict[str, Any], cooldown_days: int) -> bool:
    """Check if a venture is due for enrichment."""
    if str(venture.get("status", "")) != "active":
        return False
    enrichment = venture.get("enrichment_data")
    if not isinstance(enrichment, dict):
        return True  # never enriched
    last = enrichment.get("enriched_at", "")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        return datetime.now(UTC) - last_dt > timedelta(days=cooldown_days)
    except (ValueError, TypeError):
        return True


def _compute_sentiment(results: list[EnrichmentResult]) -> str:
    """Aggregate sentiment across all results."""
    pos = sum(1 for r in results if r.sentiment == "positive")
    neg = sum(1 for r in results if r.sentiment == "negative")
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


class VentureEnricher:
    """Orchestrates data fetching from all configured sources.

    Manages per-venture cooldowns and aggregates results.
    """

    def __init__(self) -> None:
        self._sources: list[Any] = []

        web = WebSearchSource()
        if web.available:
            self._sources.append(web)

        twitter = TwitterSignalsSource()
        if twitter.available:
            self._sources.append(twitter)

        self.cooldown_days = int(os.environ.get("VIBE_ENRICHMENT_COOLDOWN_DAYS", str(DEFAULT_COOLDOWN_DAYS)))

    @property
    def available(self) -> bool:
        return len(self._sources) > 0

    @property
    def source_names(self) -> list[str]:
        return [s.name for s in self._sources]

    async def enrich_venture(self, venture: dict[str, Any]) -> EnrichmentRecord | None:
        """Enrich a single venture from all sources.  Returns None if no sources available."""
        if not self.available:
            return None

        vid = str(venture.get("venture_id", "unknown"))
        all_results: list[EnrichmentResult] = []

        for source in self._sources:
            try:
                results = await source.fetch(venture)
                all_results.extend(results)
                log.debug("Source %s returned %d results for %s", source.name, len(results), vid)
            except Exception:
                log.exception("Source %s failed for %s", source.name, vid)

        if not all_results:
            return None

        competitor_count = sum(1 for r in all_results if r.category == "competitor")
        market_signal_count = sum(1 for r in all_results if r.category == "market_signal")

        return EnrichmentRecord(
            venture_id=vid,
            results=[r.to_dict() for r in all_results],
            source_count=len(self._sources),
            total_results=len(all_results),
            competitor_count=competitor_count,
            market_signal_count=market_signal_count,
            overall_sentiment=_compute_sentiment(all_results),
        )

    async def enrich_portfolio(self, runtime_root: str) -> list[EnrichmentRecord]:
        """Enrich all active ventures that are past their cooldown.

        Modifies state in-place and persists.
        """
        if not self.available:
            log.debug("No enrichment sources configured — skipping")
            return []

        state = load_state(runtime_root)
        ventures = [v for v in state.get("ventures", []) if isinstance(v, dict)]
        due = [v for v in ventures if _needs_enrichment(v, self.cooldown_days)]

        if not due:
            log.debug("No ventures due for enrichment")
            return []

        log.info("Enriching %d/%d ventures", len(due), len(ventures))
        records: list[EnrichmentRecord] = []

        for venture in due:
            record = await self.enrich_venture(venture)
            if record is None:
                continue
            records.append(record)
            # Store on venture state
            venture["enrichment_data"] = record.to_dict()
            # Log it
            append_log(runtime_root, "enrichment", record.to_dict())

        if records:
            with ops_write_lock(runtime_root):
                save_state(runtime_root, state)

        return records
