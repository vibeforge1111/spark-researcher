"""Tests for LLM agents, client, and blended scoring."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from domain_chip_vibe_incubator.llm_client import (
    ClaudeClient,
    LLMResponse,
    _parse_json_response,
)
from domain_chip_vibe_incubator.agents import (
    AdmissionsAgent,
    AgentOutput,
    BottleneckDiagnosticAgent,
    ReviewAgent,
    VentureAnalystAgent,
    blend_scores,
)


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------


class TestParseJsonResponse:
    def test_plain_json(self):
        result = _parse_json_response('{"score": 0.8}')
        assert result == {"score": 0.8}

    def test_fenced_json(self):
        text = '```json\n{"score": 0.8}\n```'
        result = _parse_json_response(text)
        assert result == {"score": 0.8}

    def test_fenced_no_lang(self):
        text = '```\n{"key": "val"}\n```'
        result = _parse_json_response(text)
        assert result == {"key": "val"}

    def test_malformed_json_returns_none(self):
        assert _parse_json_response("not json at all") is None

    def test_list_json_returns_none(self):
        assert _parse_json_response("[1, 2, 3]") is None

    def test_empty_string(self):
        assert _parse_json_response("") is None


# ---------------------------------------------------------------------------
# Graceful degradation (no API key)
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    def test_client_unavailable_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing key
            os.environ.pop("ANTHROPIC_API_KEY", None)
            client = ClaudeClient()
            assert client.available is False

    def test_client_available_with_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"}):
            client = ClaudeClient()
            assert client.available is True

    def test_evaluate_returns_none_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            client = ClaudeClient()
            result = asyncio.get_event_loop().run_until_complete(
                client.evaluate("system", "user")
            )
            assert result is None

    def test_structured_evaluate_returns_none_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            client = ClaudeClient()
            result = asyncio.get_event_loop().run_until_complete(
                client.structured_evaluate("system", "user")
            )
            assert result is None

    def test_agent_returns_none_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            client = ClaudeClient()
            agent = VentureAnalystAgent(client=client)
            assert agent.available is False
            result = asyncio.get_event_loop().run_until_complete(
                agent.evaluate({"venture_id": "v-test"})
            )
            assert result is None


# ---------------------------------------------------------------------------
# Blended scoring
# ---------------------------------------------------------------------------


class TestBlendScores:
    def test_default_blend_60_40(self):
        llm = {"focus": 0.8, "trust": 0.6}
        heuristic = {"focus": 0.4, "trust": 0.5}
        result = blend_scores(llm, heuristic, ratio=0.6)
        assert result["focus"] == round(0.6 * 0.8 + 0.4 * 0.4, 4)  # 0.64
        assert result["trust"] == round(0.6 * 0.6 + 0.4 * 0.5, 4)  # 0.56

    def test_full_llm_weight(self):
        llm = {"score": 0.9}
        heuristic = {"score": 0.1}
        result = blend_scores(llm, heuristic, ratio=1.0)
        assert result["score"] == 0.9

    def test_full_heuristic_weight(self):
        llm = {"score": 0.9}
        heuristic = {"score": 0.1}
        result = blend_scores(llm, heuristic, ratio=0.0)
        assert result["score"] == 0.1

    def test_missing_keys_handled(self):
        llm = {"a": 0.5}
        heuristic = {"b": 0.3}
        result = blend_scores(llm, heuristic, ratio=0.6)
        assert result["a"] == 0.5  # only in llm
        assert result["b"] == 0.3  # only in heuristic

    def test_env_override(self):
        with patch.dict(os.environ, {"VIBE_LLM_BLEND_RATIO": "0.8"}):
            from domain_chip_vibe_incubator.agents import _blend_ratio
            assert _blend_ratio() == 0.8


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------


class TestPromptLoading:
    def test_venture_analyst_prompt_loads(self):
        agent = VentureAnalystAgent(client=ClaudeClient())
        prompt = agent.system_prompt
        assert "Venture Analyst" in prompt
        assert "compound_score" in prompt

    def test_review_agent_prompt_loads(self):
        agent = ReviewAgent(client=ClaudeClient())
        assert "Review Agent" in agent.system_prompt

    def test_admissions_agent_prompt_loads(self):
        agent = AdmissionsAgent(client=ClaudeClient())
        assert "Admissions Agent" in agent.system_prompt

    def test_bottleneck_diagnostic_prompt_loads(self):
        agent = BottleneckDiagnosticAgent(client=ClaudeClient())
        assert "Bottleneck Diagnostic" in agent.system_prompt


# ---------------------------------------------------------------------------
# Agent evaluation with mocked LLM
# ---------------------------------------------------------------------------


def _mock_client(response_dict: dict) -> ClaudeClient:
    """Create a ClaudeClient with a mocked evaluate method."""
    client = ClaudeClient()
    client._api_key = "mock-key"  # make it think it's available

    async def mock_evaluate(system_prompt, user_message, *, max_tokens=2048):
        return LLMResponse(
            text=json.dumps(response_dict),
            model="mock",
            input_tokens=100,
            output_tokens=50,
        )

    client.evaluate = mock_evaluate  # type: ignore[assignment]
    return client


class TestVentureAnalystAgent:
    def test_evaluate_returns_structured_output(self):
        mock_response = {
            "scores": {
                "portfolio_focus": 0.7,
                "automation_coverage": 0.5,
                "review_hygiene": 0.8,
                "validation_velocity": 0.6,
                "trust_hygiene": 0.9,
                "knowledge_capture": 0.4,
                "revenue_trajectory": 0.55,
                "customer_impact": 0.65,
            },
            "compound_score": 0.65,
            "reasoning": "Strong trust and review hygiene, weak knowledge capture.",
            "bottleneck": "knowledge_capture",
            "recommendation": "on_track",
            "confidence": 0.75,
        }
        client = _mock_client(mock_response)
        agent = VentureAnalystAgent(client=client)
        result = asyncio.get_event_loop().run_until_complete(
            agent.evaluate({"venture_id": "v-test", "status": "active"})
        )
        assert result is not None
        assert isinstance(result, AgentOutput)
        assert result.scores["portfolio_focus"] == 0.7
        assert result.recommendation == "on_track"
        assert result.confidence == 0.75


class TestReviewAgent:
    def test_evaluate_returns_decision(self):
        mock_response = {
            "decision": "continue",
            "confidence": 0.8,
            "reasoning": "Revenue growing, conversations active.",
            "key_signals": ["revenue +15%", "3 conversations"],
            "next_actions": ["schedule founder call"],
            "risk_if_ignored": "Miss growth window",
        }
        client = _mock_client(mock_response)
        agent = ReviewAgent(client=client)
        result = asyncio.get_event_loop().run_until_complete(
            agent.evaluate({"venture_id": "v-test"})
        )
        assert result is not None
        assert result.recommendation == "continue"
        assert result.confidence == 0.8


class TestAdmissionsAgent:
    def test_evaluate_returns_decision(self):
        mock_response = {
            "decision": "invite",
            "scores": {
                "founder_quality": 0.85,
                "market_opportunity": 0.7,
                "portfolio_fit": 0.6,
                "venture_model": 0.75,
            },
            "overall_score": 0.74,
            "confidence": 0.7,
            "reasoning": "Strong founder with relevant domain expertise.",
            "strengths": ["domain expertise", "shipping speed"],
            "concerns": ["crowded market"],
            "conditions": "",
        }
        client = _mock_client(mock_response)
        agent = AdmissionsAgent(client=client)
        result = asyncio.get_event_loop().run_until_complete(
            agent.evaluate({"application_id": "app-1", "label": "Test App"})
        )
        assert result is not None
        assert result.recommendation == "invite"
        assert result.scores["founder_quality"] == 0.85


class TestBottleneckDiagnosticAgent:
    def test_evaluate_returns_diagnostic(self):
        mock_response = {
            "root_causes": [
                {"cause": "Wrong ICP targeting", "evidence": ["0 paid signals"], "severity": "high"}
            ],
            "symptom_cluster": "market_problem",
            "interventions": [
                {"action": "Run 3 calls with mid-market CTOs", "expected_impact": "Validate ICP", "timeline": "this_week"}
            ],
            "prognosis": "recoverable",
            "confidence": 0.65,
            "reasoning": "Low validation despite active conversations suggests ICP mismatch.",
        }
        client = _mock_client(mock_response)
        agent = BottleneckDiagnosticAgent(client=client)
        result = asyncio.get_event_loop().run_until_complete(
            agent.evaluate({"venture_id": "v-test", "validation_velocity": 0.1})
        )
        assert result is not None
        assert result.recommendation == "recoverable"
        assert len(result.raw["root_causes"]) == 1


# ---------------------------------------------------------------------------
# LLM Response model
# ---------------------------------------------------------------------------


class TestLLMResponse:
    def test_frozen_dataclass(self):
        r = LLMResponse(text="hello", model="test", input_tokens=10, output_tokens=5)
        assert r.text == "hello"
        with pytest.raises(AttributeError):
            r.text = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Model env var
# ---------------------------------------------------------------------------


class TestModelConfig:
    def test_default_model(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("VIBE_LLM_MODEL", None)
            from domain_chip_vibe_incubator.llm_client import _get_model, DEFAULT_MODEL
            assert _get_model() == DEFAULT_MODEL

    def test_custom_model(self):
        with patch.dict(os.environ, {"VIBE_LLM_MODEL": "claude-opus-4-6"}):
            from domain_chip_vibe_incubator.llm_client import _get_model
            assert _get_model() == "claude-opus-4-6"
