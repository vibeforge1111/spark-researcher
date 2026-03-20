"""Web search data source for venture enrichment.

Uses aiohttp to fetch search results.  Configurable via:
- ``VIBE_SEARCH_API_KEY`` — API key for search provider
- ``VIBE_SEARCH_ENGINE`` — search endpoint URL

If no API key is set, this source is disabled (graceful degradation).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from .base import DataSource, EnrichmentResult

log = logging.getLogger(__name__)


class WebSearchSource:
    """Fetches market signals, competitor info, and trends via web search."""

    name = "web_search"

    def __init__(self) -> None:
        self.api_key = os.environ.get("VIBE_SEARCH_API_KEY", "")
        self.endpoint = os.environ.get(
            "VIBE_SEARCH_ENGINE",
            "https://api.search.brave.com/res/v1/web/search",
        )

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _build_queries(self, venture: dict[str, Any]) -> list[str]:
        """Generate search queries from venture data."""
        label = str(venture.get("label", ""))
        model = str(venture.get("venture_model", ""))
        surface = str(venture.get("customer_surface", ""))
        queries = []
        if label:
            queries.append(f"{label} startup competitors 2026")
            queries.append(f"{label} market size trends")
        if model and surface:
            queries.append(f"{model} {surface} market opportunity")
        return queries[:3]  # max 3 queries per venture

    async def fetch(self, venture: dict[str, Any]) -> list[EnrichmentResult]:
        if not self.available:
            return []

        queries = self._build_queries(venture)
        if not queries:
            return []

        results: list[EnrichmentResult] = []
        try:
            import aiohttp
        except ImportError:
            log.warning("aiohttp not installed — web search disabled")
            return []

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }

        async with aiohttp.ClientSession() as session:
            for query in queries:
                try:
                    async with session.get(
                        self.endpoint,
                        params={"q": query, "count": 5},
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status != 200:
                            log.warning("Search API returned %d for query: %s", resp.status, query)
                            continue
                        data = await resp.json()
                        for item in (data.get("web", {}).get("results", []) or [])[:3]:
                            results.append(EnrichmentResult(
                                source=self.name,
                                category=_classify_result(query),
                                title=str(item.get("title", "")),
                                summary=str(item.get("description", "")),
                                url=str(item.get("url", "")),
                                relevance=0.5,
                            ))
                except Exception:
                    log.exception("Search query failed: %s", query)

        return results


def _classify_result(query: str) -> str:
    """Simple category classification based on query keywords."""
    q = query.lower()
    if "competitor" in q:
        return "competitor"
    if "market size" in q or "trend" in q:
        return "market_signal"
    return "general"
