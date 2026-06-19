from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

for HARNESS_CORE_SRC in (
    Path(__file__).resolve().parents[2] / "spark-harness-core" / "src",
    Path.home() / ".spark" / "modules" / "spark-harness-core" / "source" / "src",
):
    if HARNESS_CORE_SRC.exists() and str(HARNESS_CORE_SRC) not in sys.path:
        sys.path.insert(0, str(HARNESS_CORE_SRC))
        break

from spark_harness_core import HarnessKernel, evidence_ref
from spark_researcher.authority import ADVISORY_EXECUTE_ACTION_TYPE, ADVISORY_EXECUTE_CAPABILITY_ID, ADVISORY_EXECUTE_TOOL_NAME
from spark_researcher.research import execute_with_research
from spark_researcher.verifier import execute_with_verifier


def _governor_decision() -> dict:
    kernel = HarnessKernel(surface="cli")
    action = kernel.proposed_action(
        capability_id=ADVISORY_EXECUTE_CAPABILITY_ID,
        action_type=ADVISORY_EXECUTE_ACTION_TYPE,
        risk_tier="medium",
        summary="Execute a Spark Researcher advisory through a provider adapter.",
        args_path="advisory:test",
        requires_confirmation=True,
    )
    fresh_intent = evidence_ref(
        "fresh_user_intent",
        "test",
        "Fresh owner request for Researcher advisory execution.",
        confidence=1.0,
    )
    approval = evidence_ref(
        "human_confirmation",
        "test",
        "Owner approved Researcher advisory execution.",
        confidence=1.0,
    )
    envelope = kernel.create_envelope(
        selected_move="execute_action",
        intent_summary="Execute Spark Researcher advisory.",
        raw_turn_summary="Owner requested provider execution for this advisory.",
        evidence=[fresh_intent, approval],
        proposed_actions=[action],
        authority_state="executable",
        risk_tier="medium",
        confidence=1.0,
    )
    authorization = kernel.authorize(envelope, action, approval_ref=approval)
    ledger = kernel.record_tool_call(
        envelope=envelope,
        action=action,
        authorization=authorization,
        tool_name=ADVISORY_EXECUTE_TOOL_NAME,
        status="not_started",
        output_path="advisory:test",
        summary="Researcher advisory execution is authorized but not started.",
    )
    return kernel.governor_decision(
        envelope,
        authorizations=[authorization],
        tool_ledgers=[ledger],
        reply_style="compact_status",
        reply_instruction="Execute the advisory.",
    )


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

    packet = execute_with_verifier(tmp_path, advisory=advisory, model="generic", governor_decision=_governor_decision())

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

    packet = execute_with_verifier(tmp_path, advisory=advisory, model="generic", governor_decision=_governor_decision())

    assert packet["status"] == "needs_verification"
    assert packet["decision"] == "needs_verification"
    assert packet["clarifying_questions"] == ["What tradeoff matters most?"]


def test_execute_with_verifier_threads_governor_to_provider_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    decision = _governor_decision()
    calls: list[dict | None] = []

    def fake_execute_advisory(*args, **kwargs):
        calls.append(kwargs.get("governor_decision"))
        if len(calls) == 3:
            return {
                "response": {
                    "raw_response": json.dumps(
                        {
                            "decision": "approve",
                            "selected": "a",
                            "issues": [],
                            "missing_evidence": [],
                            "rewrite_instructions": [],
                            "best_next_question": "",
                            "implicated_failure_surface": "",
                        }
                    )
                }
            }
        return {"response": {"raw_response": "draft"}}

    monkeypatch.setattr("spark_researcher.verifier.execute_advisory", fake_execute_advisory)
    packet = execute_with_verifier(
        tmp_path,
        advisory={"task": "Answer with the available evidence.", "domain": "generic", "epistemic_status": {"status": "supported"}},
        model="generic",
        governor_decision=decision,
    )

    assert packet["decision"] == "approve"
    assert calls == [decision, decision, decision]


def test_execute_with_research_requires_governor_before_research_artifacts(tmp_path: Path) -> None:
    advisory = {
        "task": "Find the latest official API changes for the product",
        "task_type": "product_research",
        "domain": "generic",
        "intent": {"resource_modes": ["web"]},
        "epistemic_status": {
            "status": "under_supported",
            "missing_evidence": ["Need fresh official sources."],
            "clarifying_questions": [],
        },
    }

    with pytest.raises(RuntimeError, match="missing_governor_decision"):
        execute_with_research(tmp_path, advisory=advisory, model="generic")

    assert not (tmp_path / "artifacts").exists()
