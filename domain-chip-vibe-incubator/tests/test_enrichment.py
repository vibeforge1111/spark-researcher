"""Tests for the external data enrichment system (Tier 4)."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from domain_chip_vibe_incubator.data_sources.base import EnrichmentResult
from domain_chip_vibe_incubator.data_sources.web_search import WebSearchSource, _classify_result
from domain_chip_vibe_incubator.data_sources.twitter_signals import TwitterSignalsSource, _simple_sentiment
from domain_chip_vibe_incubator.enrichment import (
    EnrichmentRecord,
    VentureEnricher,
    _compute_sentiment,
    _needs_enrichment,
)
from domain_chip_vibe_incubator.ops_loop import load_state, read_log, save_state


@pytest.fixture()
def runtime_root(tmp_path: Path):
    artifacts = tmp_path / "artifacts" / "incubator_os"
    artifacts.mkdir(parents=True)
    (artifacts / "logs").mkdir()
    state = {
        "ventures": [
            {
                "venture_id": "v-alpha",
                "label": "Alpha Venture",
                "status": "active",
                "venture_model": "agentic_saas",
                "customer_surface": "founder_backoffice",
            },
        ],
        "applications": [],
        "founders": [],
        "batches": [],
    }
    (artifacts / "state.json").write_text(json.dumps(state))
    return str(tmp_path)


# ---------------------------------------------------------------------------
# EnrichmentResult
# ---------------------------------------------------------------------------


class TestEnrichmentResult:
    def test_to_dict(self):
        r = EnrichmentResult(
            source="web_search",
            category="competitor",
            title="Competitor Found",
            summary="A competitor was found",
            url="https://example.com",
            relevance=0.7,
            sentiment="neutral",
        )
        d = r.to_dict()
        assert d["source"] == "web_search"
        assert d["category"] == "competitor"
        assert d["relevance"] == 0.7

    def test_frozen(self):
        r = EnrichmentResult(source="test", category="test", title="t", summary="s")
        with pytest.raises(AttributeError):
            r.source = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


class TestClassifyResult:
    def test_competitor_query(self):
        assert _classify_result("Alpha startup competitors 2026") == "competitor"

    def test_market_query(self):
        assert _classify_result("SaaS market size trends") == "market_signal"

    def test_general_query(self):
        assert _classify_result("something else entirely") == "general"


class TestSimpleSentiment:
    def test_positive(self):
        assert _simple_sentiment("This product is amazing, love it, great growth!") == "positive"

    def test_negative(self):
        assert _simple_sentiment("The startup failed and shut down due to scam concerns") == "negative"

    def test_neutral(self):
        assert _simple_sentiment("The company announced a new feature today") == "neutral"


class TestComputeSentiment:
    def test_majority_positive(self):
        results = [
            EnrichmentResult(source="t", category="c", title="t", summary="s", sentiment="positive"),
            EnrichmentResult(source="t", category="c", title="t", summary="s", sentiment="positive"),
            EnrichmentResult(source="t", category="c", title="t", summary="s", sentiment="negative"),
        ]
        assert _compute_sentiment(results) == "positive"

    def test_tie_is_neutral(self):
        results = [
            EnrichmentResult(source="t", category="c", title="t", summary="s", sentiment="positive"),
            EnrichmentResult(source="t", category="c", title="t", summary="s", sentiment="negative"),
        ]
        assert _compute_sentiment(results) == "neutral"


# ---------------------------------------------------------------------------
# Needs enrichment check
# ---------------------------------------------------------------------------


class TestNeedsEnrichment:
    def test_active_without_enrichment_data(self):
        v = {"status": "active"}
        assert _needs_enrichment(v, 7) is True

    def test_archived_never_needs_enrichment(self):
        v = {"status": "archived"}
        assert _needs_enrichment(v, 7) is False

    def test_recently_enriched_skipped(self):
        from datetime import UTC, datetime
        v = {
            "status": "active",
            "enrichment_data": {
                "enriched_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            },
        }
        assert _needs_enrichment(v, 7) is False

    def test_stale_enrichment_needs_refresh(self):
        v = {
            "status": "active",
            "enrichment_data": {
                "enriched_at": "2020-01-01T00:00:00+00:00",
            },
        }
        assert _needs_enrichment(v, 7) is True


# ---------------------------------------------------------------------------
# Source availability (graceful degradation)
# ---------------------------------------------------------------------------


class TestSourceAvailability:
    def test_web_search_unavailable_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("VIBE_SEARCH_API_KEY", None)
            source = WebSearchSource()
            assert source.available is False

    def test_web_search_available_with_key(self):
        with patch.dict(os.environ, {"VIBE_SEARCH_API_KEY": "test-key"}):
            source = WebSearchSource()
            assert source.available is True

    def test_twitter_unavailable_without_token(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("VIBE_TWITTER_BEARER_TOKEN", None)
            source = TwitterSignalsSource()
            assert source.available is False

    def test_twitter_available_with_token(self):
        with patch.dict(os.environ, {"VIBE_TWITTER_BEARER_TOKEN": "test-token"}):
            source = TwitterSignalsSource()
            assert source.available is True


class TestVentureEnricher:
    def test_unavailable_without_any_source(self):
        with patch.dict(os.environ, {}, clear=True):
            for key in ("VIBE_SEARCH_API_KEY", "VIBE_TWITTER_BEARER_TOKEN"):
                os.environ.pop(key, None)
            enricher = VentureEnricher()
            assert enricher.available is False
            assert enricher.source_names == []

    def test_enrich_returns_none_when_unavailable(self):
        with patch.dict(os.environ, {}, clear=True):
            for key in ("VIBE_SEARCH_API_KEY", "VIBE_TWITTER_BEARER_TOKEN"):
                os.environ.pop(key, None)
            enricher = VentureEnricher()
            result = asyncio.get_event_loop().run_until_complete(
                enricher.enrich_venture({"venture_id": "v-test", "status": "active"})
            )
            assert result is None

    def test_enrich_portfolio_empty_when_unavailable(self, runtime_root):
        with patch.dict(os.environ, {}, clear=True):
            for key in ("VIBE_SEARCH_API_KEY", "VIBE_TWITTER_BEARER_TOKEN"):
                os.environ.pop(key, None)
            enricher = VentureEnricher()
            records = asyncio.get_event_loop().run_until_complete(
                enricher.enrich_portfolio(runtime_root)
            )
            assert records == []


# ---------------------------------------------------------------------------
# EnrichmentRecord
# ---------------------------------------------------------------------------


class TestEnrichmentRecord:
    def test_to_dict(self):
        r = EnrichmentRecord(
            venture_id="v-1",
            results=[{"source": "web_search", "title": "test"}],
            source_count=1,
            total_results=1,
            competitor_count=0,
            market_signal_count=1,
            overall_sentiment="positive",
        )
        d = r.to_dict()
        assert d["venture_id"] == "v-1"
        assert d["total_results"] == 1
        assert d["overall_sentiment"] == "positive"


# ---------------------------------------------------------------------------
# Query generation
# ---------------------------------------------------------------------------


class TestQueryGeneration:
    def test_web_search_builds_queries(self):
        source = WebSearchSource()
        queries = source._build_queries({
            "label": "FooBar",
            "venture_model": "agentic_saas",
            "customer_surface": "founder_backoffice",
        })
        assert len(queries) == 3
        assert any("FooBar" in q for q in queries)
        assert any("competitor" in q.lower() for q in queries)

    def test_web_search_empty_venture(self):
        source = WebSearchSource()
        queries = source._build_queries({})
        assert queries == []

    def test_twitter_builds_queries(self):
        source = TwitterSignalsSource()
        queries = source._build_queries({
            "label": "FooBar",
            "venture_model": "agentic_saas",
        })
        assert len(queries) == 2
        assert any("FooBar" in q for q in queries)
