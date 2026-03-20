"""Multi-agent orchestrator for the Vibe Incubator (Tier 6).

Maps incubator work queues to specialized agents.  Each agent type processes
items from its queue, generates recommendations, and flags items that require
human approval (the "human gate").

Agent types:
    1. FounderCoachAgent       — office_hours queue
    2. CustomerResearchAgent   — validation queue
    3. GTMOperatorAgent        — gtm queue
    4. BuildOrchestratorAgent  — build queue
    5. TrustDiligenceAgent     — trust queue
    6. CapitalOperatorAgent    — capital queue
    7. PortfolioLibrarianAgent — doctrine queue

Human gates (always require operator approval):
    - Admission decisions (invite/reject)
    - Kill/exit decisions
    - Equity or token grants
    - Investor introductions
    - Public commitments
    - Trust escalations (red zone)
    - Treasury disbursements
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from .agents import AgentOutput, _BaseAgent, _load_prompt
from .event_types import EventBus, IncubatorEvent
from .llm_client import ClaudeClient, get_client
from .ops_loop import append_log, load_state, ops_write_lock, read_log, save_state

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Human gate definitions
# ---------------------------------------------------------------------------

HUMAN_GATE_ACTIONS = frozenset({
    "admit",
    "reject",
    "kill",
    "exit",
    "equity_grant",
    "token_grant",
    "investor_intro",
    "public_commitment",
    "trust_escalation",
    "treasury_disbursement",
})


def requires_human_gate(action: str) -> bool:
    """Return True if the action requires human operator approval."""
    return action.lower() in HUMAN_GATE_ACTIONS


# ---------------------------------------------------------------------------
# Agent action output
# ---------------------------------------------------------------------------

@dataclass
class AgentAction:
    """An action recommended by a specialized agent."""

    agent_type: str
    venture_id: str
    action: str  # what the agent recommends
    reasoning: str = ""
    confidence: float = 0.0
    requires_human: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrchestratorResult:
    """Summary of a single orchestration cycle."""

    actions_generated: int = 0
    actions_auto_executed: int = 0
    actions_queued_for_human: int = 0
    agent_results: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    processed_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Specialized agent implementations
# ---------------------------------------------------------------------------

class _QueueAgent:
    """Base class for queue-processing agents."""

    agent_type: str = ""
    queue_name: str = ""

    # System prompt is built inline since these are simpler than Tier 2 agents
    _system_prompt: str = ""

    def __init__(self, client: ClaudeClient | None = None) -> None:
        self.client = client or get_client()

    @property
    def available(self) -> bool:
        return self.client.available

    async def process_item(
        self,
        item: dict[str, Any],
        venture: dict[str, Any],
        state: dict[str, Any],
    ) -> AgentAction | None:
        """Process a single queue item and return a recommended action."""
        if not self.available:
            return self._heuristic_action(item, venture, state)
        return await self._llm_action(item, venture, state)

    def _heuristic_action(
        self,
        item: dict[str, Any],
        venture: dict[str, Any],
        state: dict[str, Any],
    ) -> AgentAction | None:
        """Subclasses override for heuristic fallback."""
        return None

    async def _llm_action(
        self,
        item: dict[str, Any],
        venture: dict[str, Any],
        state: dict[str, Any],
    ) -> AgentAction | None:
        """Use LLM to generate an action."""
        import json
        context = {
            "queue_item": item,
            "venture": venture,
            "portfolio_size": len([
                v for v in state.get("ventures", [])
                if isinstance(v, dict) and v.get("status") == "active"
            ]),
        }
        result = await self.client.structured_evaluate(
            self._system_prompt,
            json.dumps(context, indent=2, default=str),
        )
        if result is None:
            return self._heuristic_action(item, venture, state)

        action_str = str(result.get("action", "review"))
        return AgentAction(
            agent_type=self.agent_type,
            venture_id=str(venture.get("venture_id", "")),
            action=action_str,
            reasoning=str(result.get("reasoning", "")),
            confidence=float(result.get("confidence", 0.5)),
            requires_human=requires_human_gate(action_str),
            metadata=result,
        )


class FounderCoachAgent(_QueueAgent):
    """Prepares coaching agendas and meeting notes for office hours."""

    agent_type = "founder_coach"
    queue_name = "office_hours"
    _system_prompt = (
        "You are a startup founder coach. Given a venture's current state, "
        "prepare a coaching agenda. Identify the top 3 blockers, suggest "
        "questions to ask the founder, and flag any metrics that need attention. "
        "Respond with JSON: {\"action\": \"coach\", \"agenda\": [...], "
        "\"key_questions\": [...], \"metrics_to_discuss\": [...], "
        "\"reasoning\": \"...\", \"confidence\": 0.0-1.0}"
    )

    def _heuristic_action(self, item: dict, venture: dict, state: dict) -> AgentAction | None:
        vid = str(venture.get("venture_id", ""))
        freshness = int(venture.get("weekly_update_freshness_days", 0) or 0)
        convos = int(venture.get("customer_conversations_this_week", 0) or 0)

        issues: list[str] = []
        if freshness > 5:
            issues.append(f"No update in {freshness} days")
        if convos == 0:
            issues.append("Zero customer conversations this week")
        if float(venture.get("revenue_trend", 0) or 0) < -0.1:
            issues.append("Revenue declining")

        return AgentAction(
            agent_type=self.agent_type,
            venture_id=vid,
            action="coach",
            reasoning=f"Coaching agenda: {'; '.join(issues) if issues else 'routine check-in'}",
            confidence=0.6,
        )


class CustomerResearchAgent(_QueueAgent):
    """Generates customer interview guides and ICP analysis."""

    agent_type = "customer_research"
    queue_name = "validation"
    _system_prompt = (
        "You are a customer research specialist for early-stage startups. "
        "Given a venture's state, generate interview questions, identify ideal "
        "customer profile gaps, and suggest validation experiments. "
        "Respond with JSON: {\"action\": \"research\", \"interview_questions\": [...], "
        "\"icp_gaps\": [...], \"experiments\": [...], \"reasoning\": \"...\", \"confidence\": 0.0-1.0}"
    )

    def _heuristic_action(self, item: dict, venture: dict, state: dict) -> AgentAction | None:
        vid = str(venture.get("venture_id", ""))
        convos = int(venture.get("customer_conversations_this_week", 0) or 0)
        paid = int(venture.get("paid_signals_this_week", 0) or 0)

        if convos == 0:
            action_str = "research"
            reasoning = "No customer conversations — need to start interviews"
        elif paid == 0:
            action_str = "research"
            reasoning = "Conversations happening but no paid signals — refine ICP"
        else:
            action_str = "monitor"
            reasoning = "Validation on track"

        return AgentAction(
            agent_type=self.agent_type,
            venture_id=vid,
            action=action_str,
            reasoning=reasoning,
            confidence=0.5,
        )


class GTMOperatorAgent(_QueueAgent):
    """Manages go-to-market execution: distribution, launch calendars."""

    agent_type = "gtm_operator"
    queue_name = "gtm"
    _system_prompt = (
        "You are a go-to-market operator for early-stage ventures. "
        "Given a venture's state, recommend distribution actions, content "
        "strategy, and launch timing. "
        "Respond with JSON: {\"action\": \"execute_gtm\", \"distribution_channels\": [...], "
        "\"content_plan\": [...], \"launch_readiness\": 0.0-1.0, "
        "\"reasoning\": \"...\", \"confidence\": 0.0-1.0}"
    )

    def _heuristic_action(self, item: dict, venture: dict, state: dict) -> AgentAction | None:
        vid = str(venture.get("venture_id", ""))
        dist = str(venture.get("distribution_engine", ""))
        return AgentAction(
            agent_type=self.agent_type,
            venture_id=vid,
            action="execute_gtm",
            reasoning=f"GTM via {dist or 'unset distribution engine'}",
            confidence=0.4,
        )


class BuildOrchestratorAgent(_QueueAgent):
    """Routes build tasks and manages development queues."""

    agent_type = "build_orchestrator"
    queue_name = "build"
    _system_prompt = (
        "You are a build orchestrator for startup ventures. "
        "Prioritize build tasks, suggest task routing (template vs custom), "
        "and estimate complexity. "
        "Respond with JSON: {\"action\": \"route_build\", \"priority\": \"high|medium|low\", "
        "\"approach\": \"template|custom|agent_workflow\", "
        "\"reasoning\": \"...\", \"confidence\": 0.0-1.0}"
    )

    def _heuristic_action(self, item: dict, venture: dict, state: dict) -> AgentAction | None:
        vid = str(venture.get("venture_id", ""))
        backlog = int(venture.get("build_backlog_count", 0) or 0)
        return AgentAction(
            agent_type=self.agent_type,
            venture_id=vid,
            action="route_build",
            reasoning=f"Build backlog: {backlog} items — {'high priority' if backlog > 5 else 'normal'}",
            confidence=0.5,
        )


class TrustDiligenceAgent(_QueueAgent):
    """Runs security and compliance checks on ventures."""

    agent_type = "trust_diligence"
    queue_name = "trust"
    _system_prompt = (
        "You are a trust and diligence officer for an incubator. "
        "Review venture compliance, security posture, and risk signals. "
        "Flag any issues requiring human escalation. "
        "Respond with JSON: {\"action\": \"review_trust|trust_escalation\", "
        "\"risk_level\": \"green|amber|red\", \"findings\": [...], "
        "\"reasoning\": \"...\", \"confidence\": 0.0-1.0}"
    )

    def _heuristic_action(self, item: dict, venture: dict, state: dict) -> AgentAction | None:
        vid = str(venture.get("venture_id", ""))
        trust_status = str(venture.get("trust_review_status", "amber"))

        if trust_status == "red":
            return AgentAction(
                agent_type=self.agent_type,
                venture_id=vid,
                action="trust_escalation",
                reasoning="Trust status is RED — requires human review",
                confidence=0.9,
                requires_human=True,
            )

        return AgentAction(
            agent_type=self.agent_type,
            venture_id=vid,
            action="review_trust",
            reasoning=f"Trust status: {trust_status}",
            confidence=0.6,
        )


class CapitalOperatorAgent(_QueueAgent):
    """Manages investor matching and fundraising readiness."""

    agent_type = "capital_operator"
    queue_name = "capital"
    _system_prompt = (
        "You are a capital operator for early-stage ventures. "
        "Assess fundraising readiness, suggest investor profiles, and "
        "recommend timing for introductions. "
        "Respond with JSON: {\"action\": \"assess_readiness|investor_intro\", "
        "\"readiness_score\": 0.0-1.0, \"investor_criteria\": [...], "
        "\"reasoning\": \"...\", \"confidence\": 0.0-1.0}"
    )

    def _heuristic_action(self, item: dict, venture: dict, state: dict) -> AgentAction | None:
        vid = str(venture.get("venture_id", ""))
        revenue = float(venture.get("weekly_revenue", 0) or 0)
        stage = str(venture.get("stage", ""))

        if stage in ("growth", "scale") and revenue > 0:
            return AgentAction(
                agent_type=self.agent_type,
                venture_id=vid,
                action="assess_readiness",
                reasoning=f"Stage={stage}, revenue=${revenue:.0f}/wk — assess fundraising readiness",
                confidence=0.5,
            )

        return AgentAction(
            agent_type=self.agent_type,
            venture_id=vid,
            action="monitor",
            reasoning=f"Stage={stage} — too early for capital activity",
            confidence=0.6,
        )


class PortfolioLibrarianAgent(_QueueAgent):
    """Extracts patterns, manages doctrine, and cross-pollinates learnings."""

    agent_type = "portfolio_librarian"
    queue_name = "doctrine"
    _system_prompt = (
        "You are a portfolio librarian for a startup incubator. "
        "Extract reusable patterns from venture outcomes, identify "
        "cross-portfolio insights, and update the doctrine library. "
        "Respond with JSON: {\"action\": \"extract_pattern\", "
        "\"patterns\": [...], \"cross_venture_insights\": [...], "
        "\"reasoning\": \"...\", \"confidence\": 0.0-1.0}"
    )

    def _heuristic_action(self, item: dict, venture: dict, state: dict) -> AgentAction | None:
        vid = str(venture.get("venture_id", ""))
        return AgentAction(
            agent_type=self.agent_type,
            venture_id=vid,
            action="extract_pattern",
            reasoning="Routine doctrine extraction",
            confidence=0.4,
        )


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------

AGENT_REGISTRY: dict[str, type[_QueueAgent]] = {
    "founder_coach": FounderCoachAgent,
    "customer_research": CustomerResearchAgent,
    "gtm_operator": GTMOperatorAgent,
    "build_orchestrator": BuildOrchestratorAgent,
    "trust_diligence": TrustDiligenceAgent,
    "capital_operator": CapitalOperatorAgent,
    "portfolio_librarian": PortfolioLibrarianAgent,
}

QUEUE_TO_AGENT: dict[str, str] = {
    "office_hours": "founder_coach",
    "validation": "customer_research",
    "gtm": "gtm_operator",
    "build": "build_orchestrator",
    "trust": "trust_diligence",
    "capital": "capital_operator",
    "doctrine": "portfolio_librarian",
}


# ---------------------------------------------------------------------------
# AgentOrchestrator
# ---------------------------------------------------------------------------

class AgentOrchestrator:
    """Coordinates specialized agents across incubator work queues.

    For each queue with pending items:
    1. Instantiate the assigned agent
    2. Process each item
    3. Auto-execute safe actions, queue human-gated actions for review
    """

    def __init__(self, client: ClaudeClient | None = None) -> None:
        self.client = client or get_client()
        self._agents: dict[str, _QueueAgent] = {}
        for agent_type, cls in AGENT_REGISTRY.items():
            self._agents[agent_type] = cls(client=self.client)

    @property
    def available_agents(self) -> list[str]:
        return list(self._agents.keys())

    @property
    def llm_available(self) -> bool:
        return self.client.available

    async def process_queues(self, runtime_root: str) -> OrchestratorResult:
        """Process all work queues and return results."""
        state = load_state(runtime_root)
        queues = state.get("queues", {}) if isinstance(state.get("queues"), dict) else {}

        result = OrchestratorResult()
        all_actions: list[AgentAction] = []
        human_queue: list[AgentAction] = []

        for queue_name, agent_type in QUEUE_TO_AGENT.items():
            items = queues.get(queue_name, [])
            if not items:
                continue

            agent = self._agents.get(agent_type)
            if agent is None:
                continue

            processed = 0
            for item in items:
                if not isinstance(item, dict):
                    continue
                vid = str(item.get("venture_id", ""))
                venture = _find_venture(state, vid)
                if venture is None:
                    continue

                try:
                    action = await agent.process_item(item, venture, state)
                except Exception:
                    log.exception("Agent %s failed on %s", agent_type, vid)
                    result.errors.append(f"{agent_type}:{vid}")
                    continue

                if action is None:
                    continue

                all_actions.append(action)
                processed += 1

                if action.requires_human:
                    human_queue.append(action)
                else:
                    result.actions_auto_executed += 1

            result.agent_results[agent_type] = processed

        result.actions_generated = len(all_actions)
        result.actions_queued_for_human = len(human_queue)

        # Persist all actions
        for action in all_actions:
            append_log(runtime_root, "agent_actions", action.to_dict())

        # Persist human-gated items separately for review
        for action in human_queue:
            append_log(runtime_root, "human_review_queue", action.to_dict())

        return result


def _find_venture(state: dict[str, Any], venture_id: str) -> dict[str, Any] | None:
    """Find a venture by ID in state."""
    for v in state.get("ventures", []):
        if isinstance(v, dict) and str(v.get("venture_id", "")) == venture_id:
            return v
    return None
