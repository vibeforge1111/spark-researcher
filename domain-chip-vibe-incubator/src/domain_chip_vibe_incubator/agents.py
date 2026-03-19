"""LLM-powered decision agents for the Vibe Incubator.

Each agent wraps a system prompt, accepts venture/application context,
and returns a structured ``AgentOutput``.  When the LLM is unavailable
the agent returns ``None`` and callers fall back to heuristic scoring.

Blended scoring: ``final = blend * llm + (1 - blend) * heuristic``
Default blend ratio is 0.6 (configurable via ``VIBE_LLM_BLEND_RATIO``).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .llm_client import ClaudeClient, get_client

log = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parent / "agent_prompts"
DEFAULT_BLEND_RATIO = 0.6


def _blend_ratio() -> float:
    raw = os.environ.get("VIBE_LLM_BLEND_RATIO", "")
    if raw:
        try:
            v = float(raw)
            return max(0.0, min(1.0, v))
        except ValueError:
            pass
    return DEFAULT_BLEND_RATIO


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Agent output
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentOutput:
    """Structured output from an LLM agent evaluation."""
    scores: dict[str, float] = field(default_factory=dict)
    reasoning: str = ""
    recommendation: str = ""
    confidence: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


def blend_scores(
    llm_scores: dict[str, float],
    heuristic_scores: dict[str, float],
    ratio: float | None = None,
) -> dict[str, float]:
    """Blend LLM scores with heuristic scores.

    ``ratio`` controls how much weight the LLM gets (default from env).
    """
    r = ratio if ratio is not None else _blend_ratio()
    blended: dict[str, float] = {}
    all_keys = set(llm_scores) | set(heuristic_scores)
    for key in all_keys:
        llm_val = llm_scores.get(key)
        heur_val = heuristic_scores.get(key)
        if llm_val is not None and heur_val is not None:
            blended[key] = round(r * llm_val + (1 - r) * heur_val, 4)
        elif llm_val is not None:
            blended[key] = llm_val
        elif heur_val is not None:
            blended[key] = heur_val
    return blended


# ---------------------------------------------------------------------------
# Base agent
# ---------------------------------------------------------------------------

class _BaseAgent:
    """Common agent infrastructure."""

    prompt_name: str = ""

    def __init__(self, client: ClaudeClient | None = None) -> None:
        self.client = client or get_client()
        self._system_prompt: str | None = None

    @property
    def system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = _load_prompt(self.prompt_name)
        return self._system_prompt

    @property
    def available(self) -> bool:
        return self.client.available

    def _build_user_message(self, context: dict[str, Any]) -> str:
        return json.dumps(context, indent=2, default=str)

    async def _call_llm(self, context: dict[str, Any]) -> dict[str, Any] | None:
        if not self.available:
            return None
        return await self.client.structured_evaluate(
            self.system_prompt,
            self._build_user_message(context),
        )


# ---------------------------------------------------------------------------
# VentureAnalystAgent
# ---------------------------------------------------------------------------

class VentureAnalystAgent(_BaseAgent):
    """Evaluates a venture across 8 dimensions with LLM reasoning."""

    prompt_name = "venture_analyst"

    async def evaluate(self, venture: dict[str, Any], portfolio_context: dict[str, Any] | None = None) -> AgentOutput | None:
        """Evaluate a single venture.  Returns None if LLM unavailable."""
        context = {"venture": venture}
        if portfolio_context:
            context["portfolio"] = portfolio_context

        result = await self._call_llm(context)
        if result is None:
            return None

        scores = result.get("scores", {})
        return AgentOutput(
            scores={k: float(v) for k, v in scores.items() if isinstance(v, (int, float))},
            reasoning=str(result.get("reasoning", "")),
            recommendation=str(result.get("recommendation", "")),
            confidence=float(result.get("confidence", 0.0)),
            raw=result,
        )


# ---------------------------------------------------------------------------
# ReviewAgent
# ---------------------------------------------------------------------------

class ReviewAgent(_BaseAgent):
    """Recommends continue/narrow/pivot/stop for a venture."""

    prompt_name = "review_agent"

    async def evaluate(self, venture: dict[str, Any], history: list[dict[str, Any]] | None = None) -> AgentOutput | None:
        context = {"venture": venture}
        if history:
            context["review_history"] = history[-10:]  # last 10 reviews

        result = await self._call_llm(context)
        if result is None:
            return None

        return AgentOutput(
            scores={},
            reasoning=str(result.get("reasoning", "")),
            recommendation=str(result.get("decision", "")),
            confidence=float(result.get("confidence", 0.0)),
            raw=result,
        )


# ---------------------------------------------------------------------------
# AdmissionsAgent
# ---------------------------------------------------------------------------

class AdmissionsAgent(_BaseAgent):
    """Evaluates applications for portfolio admission."""

    prompt_name = "admissions_agent"

    async def evaluate(self, application: dict[str, Any], portfolio_state: dict[str, Any] | None = None) -> AgentOutput | None:
        context = {"application": application}
        if portfolio_state:
            context["portfolio"] = {
                "active_count": len([v for v in portfolio_state.get("ventures", []) if isinstance(v, dict) and v.get("status") == "active"]),
                "portfolio_cap": portfolio_state.get("portfolio_cap", 3),
                "active_sectors": list({str(v.get("venture_model", "")) for v in portfolio_state.get("ventures", []) if isinstance(v, dict) and v.get("status") == "active"}),
            }

        result = await self._call_llm(context)
        if result is None:
            return None

        scores = result.get("scores", {})
        return AgentOutput(
            scores={k: float(v) for k, v in scores.items() if isinstance(v, (int, float))},
            reasoning=str(result.get("reasoning", "")),
            recommendation=str(result.get("decision", "")),
            confidence=float(result.get("confidence", 0.0)),
            raw=result,
        )


# ---------------------------------------------------------------------------
# BottleneckDiagnosticAgent
# ---------------------------------------------------------------------------

class BottleneckDiagnosticAgent(_BaseAgent):
    """Deep diagnostic when a venture's compound score drops below threshold."""

    prompt_name = "bottleneck_diagnostic"

    SCORE_THRESHOLD = 0.45

    async def evaluate(self, venture: dict[str, Any], metrics: dict[str, Any] | None = None) -> AgentOutput | None:
        context = {"venture": venture}
        if metrics:
            context["current_metrics"] = metrics

        result = await self._call_llm(context)
        if result is None:
            return None

        return AgentOutput(
            scores={},
            reasoning=str(result.get("reasoning", "")),
            recommendation=str(result.get("prognosis", "")),
            confidence=float(result.get("confidence", 0.0)),
            raw=result,
        )
