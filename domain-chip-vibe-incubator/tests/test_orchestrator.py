"""Tests for the multi-agent orchestrator (Tier 6)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from domain_chip_vibe_incubator.ops_loop import load_state, read_log, save_state
from domain_chip_vibe_incubator.orchestrator import (
    AGENT_REGISTRY,
    HUMAN_GATE_ACTIONS,
    QUEUE_TO_AGENT,
    AgentAction,
    AgentOrchestrator,
    BuildOrchestratorAgent,
    CapitalOperatorAgent,
    CustomerResearchAgent,
    FounderCoachAgent,
    GTMOperatorAgent,
    OrchestratorResult,
    PortfolioLibrarianAgent,
    TrustDiligenceAgent,
    _find_venture,
    requires_human_gate,
)


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
                "stage": "validation",
                "status": "active",
                "venture_model": "agentic_saas",
                "customer_surface": "founder_backoffice",
                "distribution_engine": "operator_content",
                "build_stack": "template_factory",
                "automation_coverage": 0.5,
                "weekly_revenue": 200,
                "revenue_trend": 0.1,
                "retention_signal": 0.6,
                "customer_conversations_this_week": 2,
                "paid_signals_this_week": 1,
                "weekly_update_freshness_days": 3,
                "last_review_days": 5,
                "trust_review_status": "green",
                "build_backlog_count": 4,
            },
            {
                "venture_id": "v-beta",
                "label": "Beta Venture",
                "stage": "growth",
                "status": "active",
                "venture_model": "marketplace",
                "trust_review_status": "red",
                "weekly_revenue": 500,
                "revenue_trend": -0.05,
                "customer_conversations_this_week": 0,
                "paid_signals_this_week": 0,
                "weekly_update_freshness_days": 10,
                "last_review_days": 15,
                "build_backlog_count": 8,
            },
        ],
        "applications": [],
        "founders": [],
        "batches": [],
        "queues": {
            "office_hours": [{"venture_id": "v-alpha", "priority": "high"}],
            "validation": [{"venture_id": "v-alpha", "priority": "medium"}],
            "build": [{"venture_id": "v-alpha", "priority": "high"}],
            "trust": [{"venture_id": "v-beta", "priority": "high"}],
            "capital": [],
            "doctrine": [{"venture_id": "v-alpha", "priority": "low"}],
            "gtm": [{"venture_id": "v-alpha", "priority": "medium"}],
        },
    }
    (artifacts / "state.json").write_text(json.dumps(state))
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Human gate tests
# ---------------------------------------------------------------------------


class TestHumanGate:
    def test_admit_requires_human(self):
        assert requires_human_gate("admit") is True

    def test_kill_requires_human(self):
        assert requires_human_gate("kill") is True

    def test_exit_requires_human(self):
        assert requires_human_gate("exit") is True

    def test_equity_grant_requires_human(self):
        assert requires_human_gate("equity_grant") is True

    def test_investor_intro_requires_human(self):
        assert requires_human_gate("investor_intro") is True

    def test_trust_escalation_requires_human(self):
        assert requires_human_gate("trust_escalation") is True

    def test_treasury_disbursement_requires_human(self):
        assert requires_human_gate("treasury_disbursement") is True

    def test_coach_does_not_require_human(self):
        assert requires_human_gate("coach") is False

    def test_research_does_not_require_human(self):
        assert requires_human_gate("research") is False

    def test_monitor_does_not_require_human(self):
        assert requires_human_gate("monitor") is False


# ---------------------------------------------------------------------------
# AgentAction
# ---------------------------------------------------------------------------


class TestAgentAction:
    def test_to_dict(self):
        a = AgentAction(
            agent_type="founder_coach",
            venture_id="v-1",
            action="coach",
            reasoning="Routine check-in",
            confidence=0.7,
        )
        d = a.to_dict()
        assert d["agent_type"] == "founder_coach"
        assert d["action"] == "coach"
        assert d["requires_human"] is False

    def test_human_gate_flag(self):
        a = AgentAction(
            agent_type="trust_diligence",
            venture_id="v-1",
            action="trust_escalation",
            requires_human=True,
        )
        assert a.requires_human is True


# ---------------------------------------------------------------------------
# Individual agent heuristic tests
# ---------------------------------------------------------------------------


class TestFounderCoachHeuristic:
    def test_stale_venture_coaching(self):
        agent = FounderCoachAgent()
        venture = {
            "venture_id": "v-1",
            "weekly_update_freshness_days": 8,
            "customer_conversations_this_week": 0,
            "revenue_trend": -0.15,
        }
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert action is not None
        assert action.action == "coach"
        assert "No update" in action.reasoning
        assert "Zero customer" in action.reasoning

    def test_healthy_venture_coaching(self):
        agent = FounderCoachAgent()
        venture = {
            "venture_id": "v-1",
            "weekly_update_freshness_days": 2,
            "customer_conversations_this_week": 3,
            "revenue_trend": 0.1,
        }
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert action is not None
        assert "routine" in action.reasoning.lower()


class TestCustomerResearchHeuristic:
    def test_no_conversations(self):
        agent = CustomerResearchAgent()
        venture = {
            "venture_id": "v-1",
            "customer_conversations_this_week": 0,
            "paid_signals_this_week": 0,
        }
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert action is not None
        assert action.action == "research"

    def test_conversations_no_paid(self):
        agent = CustomerResearchAgent()
        venture = {
            "venture_id": "v-1",
            "customer_conversations_this_week": 3,
            "paid_signals_this_week": 0,
        }
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert action.action == "research"
        assert "ICP" in action.reasoning

    def test_on_track(self):
        agent = CustomerResearchAgent()
        venture = {
            "venture_id": "v-1",
            "customer_conversations_this_week": 3,
            "paid_signals_this_week": 1,
        }
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert action.action == "monitor"


class TestTrustDiligenceHeuristic:
    def test_red_trust_escalation(self):
        agent = TrustDiligenceAgent()
        venture = {"venture_id": "v-1", "trust_review_status": "red"}
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert action is not None
        assert action.action == "trust_escalation"
        assert action.requires_human is True

    def test_green_trust_review(self):
        agent = TrustDiligenceAgent()
        venture = {"venture_id": "v-1", "trust_review_status": "green"}
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert action.action == "review_trust"
        assert action.requires_human is False


class TestBuildOrchestratorHeuristic:
    def test_high_backlog(self):
        agent = BuildOrchestratorAgent()
        venture = {"venture_id": "v-1", "build_backlog_count": 8}
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert "high priority" in action.reasoning

    def test_normal_backlog(self):
        agent = BuildOrchestratorAgent()
        venture = {"venture_id": "v-1", "build_backlog_count": 3}
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert "normal" in action.reasoning


class TestCapitalOperatorHeuristic:
    def test_growth_stage_with_revenue(self):
        agent = CapitalOperatorAgent()
        venture = {"venture_id": "v-1", "stage": "growth", "weekly_revenue": 500}
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert action.action == "assess_readiness"

    def test_early_stage(self):
        agent = CapitalOperatorAgent()
        venture = {"venture_id": "v-1", "stage": "validation", "weekly_revenue": 0}
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert action.action == "monitor"


class TestPortfolioLibrarianHeuristic:
    def test_returns_extract_pattern(self):
        agent = PortfolioLibrarianAgent()
        venture = {"venture_id": "v-1"}
        action = agent._heuristic_action({}, venture, {"ventures": []})
        assert action.action == "extract_pattern"


# ---------------------------------------------------------------------------
# Registry and mapping
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_all_queues_have_agents(self):
        for queue_name, agent_type in QUEUE_TO_AGENT.items():
            assert agent_type in AGENT_REGISTRY, f"Queue {queue_name} maps to unknown agent {agent_type}"

    def test_seven_agent_types(self):
        assert len(AGENT_REGISTRY) == 7

    def test_seven_queue_mappings(self):
        assert len(QUEUE_TO_AGENT) == 7


# ---------------------------------------------------------------------------
# find_venture helper
# ---------------------------------------------------------------------------


class TestFindVenture:
    def test_finds_existing(self):
        state = {"ventures": [{"venture_id": "v-1"}, {"venture_id": "v-2"}]}
        v = _find_venture(state, "v-2")
        assert v is not None
        assert v["venture_id"] == "v-2"

    def test_returns_none_for_missing(self):
        state = {"ventures": [{"venture_id": "v-1"}]}
        assert _find_venture(state, "v-999") is None


# ---------------------------------------------------------------------------
# OrchestratorResult
# ---------------------------------------------------------------------------


class TestOrchestratorResult:
    def test_to_dict(self):
        r = OrchestratorResult(
            actions_generated=5,
            actions_auto_executed=3,
            actions_queued_for_human=2,
        )
        d = r.to_dict()
        assert d["actions_generated"] == 5
        assert d["actions_queued_for_human"] == 2


# ---------------------------------------------------------------------------
# Full orchestration (heuristic mode)
# ---------------------------------------------------------------------------


class TestOrchestration:
    def test_process_queues_heuristic(self, runtime_root):
        """Without LLM, all agents fall back to heuristic mode."""
        orchestrator = AgentOrchestrator()
        result = asyncio.run(orchestrator.process_queues(runtime_root))

        # We have items in 6 queues (capital is empty)
        assert result.actions_generated >= 1
        assert isinstance(result.agent_results, dict)

        # Trust queue has v-beta with red status → should flag for human
        assert result.actions_queued_for_human >= 1

    def test_actions_persisted_to_log(self, runtime_root):
        orchestrator = AgentOrchestrator()
        asyncio.run(orchestrator.process_queues(runtime_root))

        actions = read_log(runtime_root, "agent_actions")
        assert len(actions) >= 1

    def test_human_queue_persisted(self, runtime_root):
        orchestrator = AgentOrchestrator()
        asyncio.run(orchestrator.process_queues(runtime_root))

        human_items = read_log(runtime_root, "human_review_queue")
        # v-beta has red trust → trust_escalation → human gate
        assert any(
            item.get("action") == "trust_escalation"
            for item in human_items
        )

    def test_available_agents(self):
        orchestrator = AgentOrchestrator()
        assert len(orchestrator.available_agents) == 7

    def test_empty_queues(self, tmp_path):
        """No queued items → no actions generated."""
        artifacts = tmp_path / "artifacts" / "incubator_os"
        artifacts.mkdir(parents=True)
        (artifacts / "logs").mkdir()
        state = {
            "ventures": [],
            "applications": [],
            "founders": [],
            "batches": [],
            "queues": {
                "office_hours": [], "validation": [], "build": [],
                "trust": [], "capital": [], "doctrine": [], "gtm": [],
            },
        }
        (artifacts / "state.json").write_text(json.dumps(state))

        orchestrator = AgentOrchestrator()
        result = asyncio.run(orchestrator.process_queues(str(tmp_path)))
        assert result.actions_generated == 0
