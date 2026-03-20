"""Chip Knowledge Adapter — bridges domain chip exports to agent heuristics.

Each domain chip (one per queue agent) produces structured knowledge artifacts
via the spark-researcher autoloop.  This adapter loads those artifacts and
makes them available to the orchestrator agents so their heuristic decisions
become progressively smarter as the chips accumulate doctrine.

Exported artifacts per chip (in ``research/exports/``):

* ``playbook.json``  — decision plays keyed by venture-state conditions
* ``rubric.json``    — scoring dimensions + weights for the domain
* ``routing_rules.json`` — condition → action decision trees

The adapter **degrades gracefully**: when no chips are installed or no exports
exist, every function returns empty/default values and agents fall back to
their built-in heuristic logic.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_CHIP_BASE = str(
    Path(__file__).resolve().parent.parent.parent.parent  # spark-researcher root
)
CHIP_BASE_DIR = os.environ.get("VIBE_CHIP_BASE_DIR", _DEFAULT_CHIP_BASE)

# Map agent_type → chip directory name
AGENT_TO_CHIP: dict[str, str] = {
    "founder_coach": "domain-chip-founder-coaching",
    "customer_research": "domain-chip-customer-validation",
    "gtm_operator": "domain-chip-gtm-distribution",
    "build_orchestrator": "domain-chip-build-orchestration",
    "trust_diligence": "domain-chip-trust-compliance",
    "capital_operator": "domain-chip-capital-readiness",
    "portfolio_librarian": "domain-chip-portfolio-knowledge",
}


# ---------------------------------------------------------------------------
# Low-level loaders
# ---------------------------------------------------------------------------


def _chip_export_dir(chip_name: str) -> Path:
    """Return the exports directory for a chip, or Path("") if missing."""
    base = Path(CHIP_BASE_DIR) / chip_name / "research" / "exports"
    return base if base.is_dir() else Path("")


def _load_json(path: Path) -> dict | list:
    """Safely load a JSON file.  Returns {} on any failure."""
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        log.debug("Failed to load %s", path)
        return {}


def load_chip_playbook(chip_name: str) -> dict[str, Any]:
    """Load a chip's playbook (decision plays keyed by venture conditions).

    Returns ``{}`` if chip is not installed or has no exports.
    """
    export_dir = _chip_export_dir(chip_name)
    if not export_dir.name:
        return {}
    data = _load_json(export_dir / "playbook.json")
    return data if isinstance(data, dict) else {}


def load_chip_rubric(chip_name: str) -> dict[str, Any]:
    """Load a chip's scoring rubric (dimensions, weights, thresholds).

    Returns ``{}`` if chip is not installed or has no exports.
    """
    export_dir = _chip_export_dir(chip_name)
    if not export_dir.name:
        return {}
    data = _load_json(export_dir / "rubric.json")
    return data if isinstance(data, dict) else {}


def load_routing_rules(chip_name: str) -> list[dict[str, Any]]:
    """Load a chip's routing rules (condition → action decision trees).

    Returns ``[]`` if chip is not installed or has no exports.
    """
    export_dir = _chip_export_dir(chip_name)
    if not export_dir.name:
        return []
    data = _load_json(export_dir / "routing_rules.json")
    return data if isinstance(data, list) else []


# ---------------------------------------------------------------------------
# High-level adapter
# ---------------------------------------------------------------------------


def list_available_chips() -> list[dict[str, Any]]:
    """Discover which agent chips are installed and have exports.

    Returns a list of dicts:
    ``[{"agent_type": ..., "chip_name": ..., "has_playbook": bool, ...}]``
    """
    result: list[dict[str, Any]] = []
    for agent_type, chip_name in AGENT_TO_CHIP.items():
        chip_dir = Path(CHIP_BASE_DIR) / chip_name
        export_dir = _chip_export_dir(chip_name)
        has_exports = bool(export_dir.name)
        result.append({
            "agent_type": agent_type,
            "chip_name": chip_name,
            "installed": chip_dir.is_dir(),
            "has_playbook": has_exports and (export_dir / "playbook.json").is_file(),
            "has_rubric": has_exports and (export_dir / "rubric.json").is_file(),
            "has_routing_rules": has_exports and (export_dir / "routing_rules.json").is_file(),
        })
    return result


def chip_for_agent(agent_type: str) -> str | None:
    """Return the chip name for an agent type, or None if unknown."""
    return AGENT_TO_CHIP.get(agent_type)


def match_routing_rule(
    rules: list[dict[str, Any]],
    venture: dict[str, Any],
) -> dict[str, Any] | None:
    """Evaluate routing rules against a venture and return the first match.

    Rule format::

        {"condition": "freshness_days > 7 AND revenue_trend < -0.1",
         "action": "directive-crisis", "priority": "critical"}

    The special condition ``"default"`` always matches.

    Supported operators: ``>``, ``<``, ``>=``, ``<=``, ``==``, ``!=``
    Supported connectors: ``AND``  (all must pass)
    """
    for rule in rules:
        cond = str(rule.get("condition", ""))
        if cond == "default" or _evaluate_condition(cond, venture):
            return rule
    return None


def _evaluate_condition(condition: str, venture: dict[str, Any]) -> bool:
    """Parse a simple condition string and evaluate against venture data."""
    clauses = [c.strip() for c in condition.split("AND")]
    for clause in clauses:
        if not _evaluate_clause(clause, venture):
            return False
    return True


def _evaluate_clause(clause: str, venture: dict[str, Any]) -> bool:
    """Evaluate a single comparison clause like ``freshness_days > 7``."""
    ops = [">=", "<=", "!=", "==", ">", "<"]
    for op in ops:
        if op in clause:
            parts = clause.split(op, 1)
            if len(parts) != 2:
                return False
            field = parts[0].strip()
            try:
                threshold = float(parts[1].strip())
            except (ValueError, TypeError):
                # String comparison
                val = str(venture.get(field, ""))
                target = parts[1].strip().strip("'\"")
                if op == "==":
                    return val == target
                if op == "!=":
                    return val != target
                return False

            actual = float(venture.get(field, 0) or 0)
            if op == ">":
                return actual > threshold
            if op == "<":
                return actual < threshold
            if op == ">=":
                return actual >= threshold
            if op == "<=":
                return actual <= threshold
            if op == "==":
                return actual == threshold
            if op == "!=":
                return actual != threshold
    return False


def enhance_heuristic(
    agent_type: str,
    venture: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Apply chip knowledge to produce enriched context for agent decisions.

    Returns a dict with:
    * ``matched_play`` — the playbook play that matches, or None
    * ``matched_rule`` — the routing rule that matches, or None
    * ``rubric``       — the scoring rubric, or {}
    * ``chip_available`` — whether the chip has exports

    Agents can use this to upgrade their heuristic actions.
    """
    chip_name = chip_for_agent(agent_type)
    if chip_name is None:
        return {"chip_available": False, "matched_play": None, "matched_rule": None, "rubric": {}}

    playbook = load_chip_playbook(chip_name)
    rubric = load_chip_rubric(chip_name)
    rules = load_routing_rules(chip_name)

    # Match a routing rule
    matched_rule = match_routing_rule(rules, venture) if rules else None

    # Match a playbook play
    matched_play = _match_play(playbook, venture)

    return {
        "chip_available": bool(playbook or rubric or rules),
        "matched_play": matched_play,
        "matched_rule": matched_rule,
        "rubric": rubric,
    }


def _match_play(playbook: dict[str, Any], venture: dict[str, Any]) -> dict[str, Any] | None:
    """Find the first playbook play whose ``when`` conditions match the venture."""
    plays = playbook.get("plays", [])
    if not isinstance(plays, list):
        return None
    for play in plays:
        if not isinstance(play, dict):
            continue
        when = play.get("when", {})
        if not isinstance(when, dict):
            continue
        if _play_matches(when, venture):
            return play
    return None


def _play_matches(when: dict[str, Any], venture: dict[str, Any]) -> bool:
    """Check if all ``when`` conditions match.

    Condition keys use suffixes: ``_gt``, ``_lt``, ``_gte``, ``_lte``, ``_eq``.
    Example: ``{"freshness_days_gt": 5, "revenue_trend_lt": -0.1}``
    """
    for key, target in when.items():
        if key.endswith("_gt"):
            field = key[:-3]
            if float(venture.get(field, 0) or 0) <= float(target):
                return False
        elif key.endswith("_lt"):
            field = key[:-3]
            if float(venture.get(field, 0) or 0) >= float(target):
                return False
        elif key.endswith("_gte"):
            field = key[:-4]
            if float(venture.get(field, 0) or 0) < float(target):
                return False
        elif key.endswith("_lte"):
            field = key[:-4]
            if float(venture.get(field, 0) or 0) > float(target):
                return False
        elif key.endswith("_eq"):
            field = key[:-3]
            if str(venture.get(field, "")) != str(target):
                return False
        else:
            # Direct equality check
            if str(venture.get(key, "")) != str(target):
                return False
    return True
