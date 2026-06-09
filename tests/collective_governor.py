from __future__ import annotations

import sys
from pathlib import Path

for HARNESS_CORE_SRC in (
    Path(__file__).resolve().parents[2] / "spark-harness-core" / "src",
    Path.home() / ".spark" / "modules" / "spark-harness-core" / "source" / "src",
):
    if HARNESS_CORE_SRC.exists() and str(HARNESS_CORE_SRC) not in sys.path:
        sys.path.insert(0, str(HARNESS_CORE_SRC))
        break

from spark_harness_core import HarnessKernel, evidence_ref
from spark_researcher.authority import (
    COLLECTIVE_ABSORB_ACTION_TYPE,
    COLLECTIVE_ABSORB_CAPABILITY_ID,
    COLLECTIVE_ABSORB_TOOL_NAME,
    COLLECTIVE_PUBLISH_ACTION_TYPE,
    COLLECTIVE_PUBLISH_CAPABILITY_ID,
    COLLECTIVE_PUBLISH_TOOL_NAME,
    COLLECTIVE_SYNC_ACTION_TYPE,
    COLLECTIVE_SYNC_CAPABILITY_ID,
    COLLECTIVE_SYNC_TOOL_NAME,
)


def _collective_governor_decision(
    *,
    capability_id: str,
    action_type: str,
    tool_name: str,
    risk_tier: str,
    summary: str,
    args_path: str,
) -> dict:
    kernel = HarnessKernel(surface="cli")
    action = kernel.proposed_action(
        capability_id=capability_id,
        action_type=action_type,
        risk_tier=risk_tier,
        summary=summary,
        args_path=args_path,
        requires_confirmation=True,
    )
    fresh_intent = evidence_ref(
        "fresh_user_intent",
        "test",
        f"Fresh owner request: {summary}",
        confidence=1.0,
    )
    approval = evidence_ref(
        "human_confirmation",
        "test",
        f"Owner approved this exact collective authority binding: {summary}",
        confidence=1.0,
    )
    envelope = kernel.create_envelope(
        selected_move="execute_action",
        intent_summary=summary,
        raw_turn_summary=f"Owner explicitly requested this governed collective action: {summary}",
        evidence=[fresh_intent, approval],
        proposed_actions=[action],
        authority_state="executable",
        risk_tier=risk_tier,
        confidence=1.0,
    )
    authorization = kernel.authorize(envelope, action, approval_ref=approval)
    ledger = kernel.record_tool_call(
        envelope=envelope,
        action=action,
        authorization=authorization,
        tool_name=tool_name,
        status="not_started",
        output_path=args_path,
        summary="Collective action is authorized but not started.",
    )
    return kernel.governor_decision(
        envelope,
        authorizations=[authorization],
        tool_ledgers=[ledger],
        reply_style="compact_status",
        reply_instruction="Execute the governed collective action.",
    )


def collective_publish_governor_decision(*, summary: str = "Publish the latest collective capsule.") -> dict:
    return _collective_governor_decision(
        capability_id=COLLECTIVE_PUBLISH_CAPABILITY_ID,
        action_type=COLLECTIVE_PUBLISH_ACTION_TYPE,
        tool_name=COLLECTIVE_PUBLISH_TOOL_NAME,
        risk_tier="high",
        summary=summary,
        args_path="collective:publish-latest",
    )


def collective_sync_governor_decision(*, summary: str = "Sync the repo into the local collective.") -> dict:
    return _collective_governor_decision(
        capability_id=COLLECTIVE_SYNC_CAPABILITY_ID,
        action_type=COLLECTIVE_SYNC_ACTION_TYPE,
        tool_name=COLLECTIVE_SYNC_TOOL_NAME,
        risk_tier="medium",
        summary=summary,
        args_path="collective:sync-local",
    )


def collective_absorb_governor_decision(*, summary: str = "Absorb reviewed collective insights.") -> dict:
    return _collective_governor_decision(
        capability_id=COLLECTIVE_ABSORB_CAPABILITY_ID,
        action_type=COLLECTIVE_ABSORB_ACTION_TYPE,
        tool_name=COLLECTIVE_ABSORB_TOOL_NAME,
        risk_tier="high",
        summary=summary,
        args_path="collective:absorb",
    )
