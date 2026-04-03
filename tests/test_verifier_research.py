from __future__ import annotations

from pathlib import Path

from spark_researcher.verifier import execute_with_verifier


def test_under_supported_web_task_escalates_to_research(tmp_path: Path) -> None:
    advisory = {
        "task": "Find the latest official API changes for the product",
        "task_type": "product_research",
        "domain": "generic",
        "intent": {"resource_modes": ["web"]},
        "epistemic_status": {
            "status": "under_supported",
            "missing_evidence": ["Need fresh official sources."],
            "clarifying_questions": ["Which product matters most?"],
        },
    }

    packet = execute_with_verifier(tmp_path, advisory=advisory, model="generic")

    assert packet["status"] == "research_needed"
    assert packet["decision"] == "research_needed"
    assert packet["research_query"] == advisory["task"]
    assert packet["clarifying_questions"] == []


def test_under_supported_non_web_task_stays_needs_verification(tmp_path: Path) -> None:
    advisory = {
        "task": "Summarize the project tradeoffs",
        "task_type": "analysis",
        "domain": "generic",
        "intent": {"resource_modes": ["memory"]},
        "epistemic_status": {
            "status": "under_supported",
            "missing_evidence": ["Need more constraints from the owner."],
            "clarifying_questions": ["What tradeoff matters most?"],
        },
    }

    packet = execute_with_verifier(tmp_path, advisory=advisory, model="generic")

    assert packet["status"] == "needs_verification"
    assert packet["decision"] == "needs_verification"
    assert packet["clarifying_questions"] == ["What tradeoff matters most?"]
