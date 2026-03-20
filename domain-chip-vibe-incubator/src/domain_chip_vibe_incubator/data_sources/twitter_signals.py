"""Twitter/X data source for market signals.

Uses the X/Twitter search capabilities to find relevant market signals,
competitor activity, and industry trends for ventures.

Requires either:
- Twitter API credentials via ``VIBE_TWITTER_BEARER_TOKEN``
- Or falls back to disabled state (graceful degradation)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from .base import EnrichmentResult

log = logging.getLogger(__name__)


class TwitterSignalsSource:
    """Fetches market signals from X/Twitter."""

    name = "twitter"

    def __init__(self) -> None:
        self.bearer_token = os.environ.get("VIBE_TWITTER_BEARER_TOKEN", "")

    @property
    def available(self) -> bool:
        return bool(self.bearer_token)

    def _build_queries(self, venture: dict[str, Any]) -> list[str]:
        """Generate Twitter search queries from venture data."""
        label = str(venture.get("label", ""))
        model = str(venture.get("venture_model", ""))
        queries = []
        if label:
            queries.append(f"{label} -is:retweet lang:en")
        if model:
            queries.append(f"{model} startup launch -is:retweet lang:en")
        return queries[:2]

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
            log.warning("aiohttp not installed — Twitter signals disabled")
            return []

        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
        }
        endpoint = "https://api.twitter.com/2/tweets/search/recent"

        async with aiohttp.ClientSession() as session:
            for query in queries:
                try:
                    async with session.get(
                        endpoint,
                        params={"query": query, "max_results": 10, "tweet.fields": "created_at,public_metrics"},
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status != 200:
                            log.warning("Twitter API returned %d for query: %s", resp.status, query)
                            continue
                        data = await resp.json()
                        for tweet in (data.get("data") or [])[:5]:
                            metrics = tweet.get("public_metrics", {})
                            engagement = int(metrics.get("like_count", 0)) + int(metrics.get("retweet_count", 0))
                            results.append(EnrichmentResult(
                                source=self.name,
                                category="market_signal",
                                title=f"Tweet ({engagement} engagements)",
                                summary=str(tweet.get("text", ""))[:280],
                                url=f"https://twitter.com/i/web/status/{tweet.get('id', '')}",
                                relevance=min(1.0, engagement / 100) if engagement > 0 else 0.1,
                                sentiment=_simple_sentiment(str(tweet.get("text", ""))),
                            ))
                except Exception:
                    log.exception("Twitter query failed: %s", query)

        return results


def _simple_sentiment(text: str) -> str:
    """Very basic keyword sentiment.  LLM enrichment in Tier 2 does better."""
    t = text.lower()
    positive = sum(1 for w in ("great", "love", "amazing", "growth", "launched", "raised", "hired") if w in t)
    negative = sum(1 for w in ("failed", "shut down", "layoff", "crash", "scam", "concern") if w in t)
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"
