"""Tests for the chip knowledge adapter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from domain_chip_vibe_incubator.chip_knowledge_adapter import (
    AGENT_TO_CHIP,
    _evaluate_clause,
    _evaluate_condition,
    _match_play,
    _play_matches,
    chip_for_agent,
    enhance_heuristic,
    list_available_chips,
    load_chip_playbook,
    load_chip_rubric,
    load_routing_rules,
    match_routing_rule,
)


# ---------------------------------------------------------------------------
# Agent-to-chip mapping
# ---------------------------------------------------------------------------


class TestAgentToChip:
    def test_seven_mappings(self):
        assert len(AGENT_TO_CHIP) == 7

    def test_known_agent(self):
        assert chip_for_agent("founder_coach") == "domain-chip-founder-coaching"

    def test_unknown_agent(self):
        assert chip_for_agent("nonexistent") is None


# ---------------------------------------------------------------------------
# Graceful degradation (no chips installed)
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    def test_playbook_returns_empty(self):
        assert load_chip_playbook("nonexistent-chip") == {}

    def test_rubric_returns_empty(self):
        assert load_chip_rubric("nonexistent-chip") == {}

    def test_routing_rules_returns_empty(self):
        assert load_routing_rules("nonexistent-chip") == []

    def test_enhance_heuristic_no_chip(self):
        result = enhance_heuristic("founder_coach", {}, {})
        assert result["chip_available"] is False
        assert result["matched_play"] is None
        assert result["matched_rule"] is None

    def test_enhance_heuristic_unknown_agent(self):
        result = enhance_heuristic("nonexistent", {}, {})
        assert result["chip_available"] is False


# ---------------------------------------------------------------------------
# Loading from real exports
# ---------------------------------------------------------------------------


@pytest.fixture()
def chip_exports(tmp_path: Path):
    """Create a fake chip with exports."""
    chip_dir = tmp_path / "domain-chip-founder-coaching"
    export_dir = chip_dir / "research" / "exports"
    export_dir.mkdir(parents=True)

    playbook = {
        "chip": "domain-chip-founder-coaching",
        "version": "0.1.0",
        "plays": [
            {
                "play_id": "crisis-directive",
                "when": {"weekly_update_freshness_days_gt": 7, "revenue_trend_lt": -0.1},
                "then": {"style": "directive", "focus": "growth_blockers"},
                "confidence": 0.8,
            },
            {
                "play_id": "routine-socratic",
                "when": {"stage_eq": "validation"},
                "then": {"style": "socratic", "focus": "discovery"},
                "confidence": 0.6,
            },
        ],
    }
    (export_dir / "playbook.json").write_text(json.dumps(playbook))

    rubric = {
        "dimensions": ["coaching_style_fit", "question_quality"],
        "weights": {"coaching_style_fit": 0.5, "question_quality": 0.5},
        "thresholds": {"good": 0.7, "acceptable": 0.5},
    }
    (export_dir / "rubric.json").write_text(json.dumps(rubric))

    rules = [
        {"condition": "weekly_update_freshness_days > 7 AND revenue_trend < -0.1",
         "action": "directive-crisis", "priority": "critical"},
        {"condition": "customer_conversations_this_week == 0",
         "action": "discovery-push", "priority": "high"},
        {"condition": "default",
         "action": "routine-checkin", "priority": "normal"},
    ]
    (export_dir / "routing_rules.json").write_text(json.dumps(rules))

    return str(tmp_path)


class TestLoadExports:
    def test_load_playbook(self, chip_exports, monkeypatch):
        monkeypatch.setattr(
            "domain_chip_vibe_incubator.chip_knowledge_adapter.CHIP_BASE_DIR",
            chip_exports,
        )
        pb = load_chip_playbook("domain-chip-founder-coaching")
        assert pb["chip"] == "domain-chip-founder-coaching"
        assert len(pb["plays"]) == 2

    def test_load_rubric(self, chip_exports, monkeypatch):
        monkeypatch.setattr(
            "domain_chip_vibe_incubator.chip_knowledge_adapter.CHIP_BASE_DIR",
            chip_exports,
        )
        rubric = load_chip_rubric("domain-chip-founder-coaching")
        assert "dimensions" in rubric
        assert rubric["weights"]["coaching_style_fit"] == 0.5

    def test_load_routing_rules(self, chip_exports, monkeypatch):
        monkeypatch.setattr(
            "domain_chip_vibe_incubator.chip_knowledge_adapter.CHIP_BASE_DIR",
            chip_exports,
        )
        rules = load_routing_rules("domain-chip-founder-coaching")
        assert len(rules) == 3
        assert rules[2]["condition"] == "default"


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------


class TestConditionEvaluation:
    def test_greater_than(self):
        assert _evaluate_clause("freshness > 5", {"freshness": 7}) is True
        assert _evaluate_clause("freshness > 5", {"freshness": 3}) is False

    def test_less_than(self):
        assert _evaluate_clause("trend < -0.1", {"trend": -0.2}) is True
        assert _evaluate_clause("trend < -0.1", {"trend": 0.1}) is False

    def test_greater_equal(self):
        assert _evaluate_clause("count >= 5", {"count": 5}) is True
        assert _evaluate_clause("count >= 5", {"count": 4}) is False

    def test_less_equal(self):
        assert _evaluate_clause("score <= 0.5", {"score": 0.5}) is True
        assert _evaluate_clause("score <= 0.5", {"score": 0.6}) is False

    def test_equals(self):
        assert _evaluate_clause("count == 0", {"count": 0}) is True
        assert _evaluate_clause("count == 0", {"count": 1}) is False

    def test_not_equals(self):
        assert _evaluate_clause("status != active", {"status": "archived"}) is True

    def test_compound_and(self):
        venture = {"freshness": 10, "trend": -0.2}
        assert _evaluate_condition("freshness > 7 AND trend < -0.1", venture) is True
        venture["trend"] = 0.1
        assert _evaluate_condition("freshness > 7 AND trend < -0.1", venture) is False

    def test_missing_field_defaults_to_zero(self):
        assert _evaluate_clause("missing > 5", {}) is False
        assert _evaluate_clause("missing == 0", {}) is True


# ---------------------------------------------------------------------------
# Routing rule matching
# ---------------------------------------------------------------------------


class TestRoutingRuleMatch:
    def test_matches_first_rule(self):
        rules = [
            {"condition": "freshness > 7", "action": "crisis", "priority": "critical"},
            {"condition": "default", "action": "routine", "priority": "normal"},
        ]
        venture = {"freshness": 10}
        match = match_routing_rule(rules, venture)
        assert match is not None
        assert match["action"] == "crisis"

    def test_falls_through_to_default(self):
        rules = [
            {"condition": "freshness > 7", "action": "crisis"},
            {"condition": "default", "action": "routine"},
        ]
        venture = {"freshness": 3}
        match = match_routing_rule(rules, venture)
        assert match is not None
        assert match["action"] == "routine"

    def test_no_match_returns_none(self):
        rules = [
            {"condition": "freshness > 7", "action": "crisis"},
        ]
        venture = {"freshness": 3}
        match = match_routing_rule(rules, venture)
        assert match is None

    def test_empty_rules(self):
        assert match_routing_rule([], {}) is None


# ---------------------------------------------------------------------------
# Playbook play matching
# ---------------------------------------------------------------------------


class TestPlayMatching:
    def test_gt_suffix(self):
        when = {"weekly_update_freshness_days_gt": 7}
        assert _play_matches(when, {"weekly_update_freshness_days": 10}) is True
        assert _play_matches(when, {"weekly_update_freshness_days": 5}) is False

    def test_lt_suffix(self):
        when = {"revenue_trend_lt": -0.1}
        assert _play_matches(when, {"revenue_trend": -0.2}) is True
        assert _play_matches(when, {"revenue_trend": 0.1}) is False

    def test_eq_suffix(self):
        when = {"stage_eq": "validation"}
        assert _play_matches(when, {"stage": "validation"}) is True
        assert _play_matches(when, {"stage": "growth"}) is False

    def test_combined_conditions(self):
        when = {"weekly_update_freshness_days_gt": 7, "revenue_trend_lt": -0.1}
        venture = {"weekly_update_freshness_days": 10, "revenue_trend": -0.2}
        assert _play_matches(when, venture) is True
        venture["revenue_trend"] = 0.1
        assert _play_matches(when, venture) is False

    def test_match_play_from_playbook(self):
        playbook = {
            "plays": [
                {"play_id": "crisis", "when": {"freshness_gt": 7}, "then": {"style": "directive"}},
                {"play_id": "routine", "when": {"stage_eq": "growth"}, "then": {"style": "socratic"}},
            ],
        }
        # Matches first play
        venture = {"freshness": 10, "stage": "validation"}
        play = _match_play(playbook, venture)
        assert play is not None
        assert play["play_id"] == "crisis"

        # Matches second play
        venture = {"freshness": 3, "stage": "growth"}
        play = _match_play(playbook, venture)
        assert play is not None
        assert play["play_id"] == "routine"

        # No match
        venture = {"freshness": 3, "stage": "validation"}
        play = _match_play(playbook, venture)
        assert play is None


# ---------------------------------------------------------------------------
# Chip discovery
# ---------------------------------------------------------------------------


class TestChipDiscovery:
    def test_list_chips_no_installs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "domain_chip_vibe_incubator.chip_knowledge_adapter.CHIP_BASE_DIR",
            str(tmp_path),
        )
        chips = list_available_chips()
        assert len(chips) == 7
        assert all(c["installed"] is False for c in chips)

    def test_list_chips_with_install(self, chip_exports, monkeypatch):
        monkeypatch.setattr(
            "domain_chip_vibe_incubator.chip_knowledge_adapter.CHIP_BASE_DIR",
            chip_exports,
        )
        chips = list_available_chips()
        coaching = [c for c in chips if c["agent_type"] == "founder_coach"][0]
        assert coaching["installed"] is True
        assert coaching["has_playbook"] is True
        assert coaching["has_rubric"] is True
        assert coaching["has_routing_rules"] is True


# ---------------------------------------------------------------------------
# Full enhance_heuristic integration
# ---------------------------------------------------------------------------


class TestEnhanceHeuristic:
    def test_with_exports(self, chip_exports, monkeypatch):
        monkeypatch.setattr(
            "domain_chip_vibe_incubator.chip_knowledge_adapter.CHIP_BASE_DIR",
            chip_exports,
        )
        venture = {"weekly_update_freshness_days": 10, "revenue_trend": -0.2}
        result = enhance_heuristic("founder_coach", venture, {})
        assert result["chip_available"] is True
        assert result["matched_play"] is not None
        assert result["matched_play"]["play_id"] == "crisis-directive"
        assert result["matched_rule"] is not None
        assert result["matched_rule"]["action"] == "directive-crisis"
        assert result["rubric"]["weights"]["coaching_style_fit"] == 0.5

    def test_with_routine_venture(self, chip_exports, monkeypatch):
        monkeypatch.setattr(
            "domain_chip_vibe_incubator.chip_knowledge_adapter.CHIP_BASE_DIR",
            chip_exports,
        )
        venture = {"weekly_update_freshness_days": 3, "revenue_trend": 0.1,
                    "customer_conversations_this_week": 2, "stage": "validation"}
        result = enhance_heuristic("founder_coach", venture, {})
        assert result["chip_available"] is True
        # Should match "routine-socratic" play (stage_eq: validation)
        assert result["matched_play"]["play_id"] == "routine-socratic"
        # Should match "default" routing rule
        assert result["matched_rule"]["action"] == "routine-checkin"
