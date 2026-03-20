"""Base protocol for data sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class EnrichmentResult:
    """A single enrichment finding from any data source."""
    source: str  # e.g. "web_search", "twitter"
    category: str  # e.g. "competitor", "market_signal", "trend", "news"
    title: str
    summary: str
    url: str = ""
    relevance: float = 0.5  # 0-1
    sentiment: str = "neutral"  # positive, negative, neutral
    raw: dict[str, Any] = field(default_factory=dict)
    fetched_at: str = field(default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "category": self.category,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "relevance": self.relevance,
            "sentiment": self.sentiment,
            "fetched_at": self.fetched_at,
        }


class DataSource(Protocol):
    """Any object that can fetch enrichment data for a venture."""

    name: str

    async def fetch(self, venture: dict[str, Any]) -> list[EnrichmentResult]:
        """Fetch enrichment results for a venture.  Return empty list on failure."""
        ...

    @property
    def available(self) -> bool:
        """Whether this source is configured and ready."""
        ...
