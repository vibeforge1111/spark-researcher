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
from spark_researcher.authority import RUN_EXECUTION_ACTION_TYPE, RUN_EXECUTION_CAPABILITY_ID, RUN_EXECUTION_TOOL_NAME


def run_governor_decision(args_path: str, *, summary: str = "Execute governed Researcher run.") -> dict:
    kernel = HarnessKernel(surface="cli")
    action = kernel.proposed_action(
        capability_id=RUN_EXECUTION_CAPABILITY_ID,
        action_type=RUN_EXECUTION_ACTION_TYPE,
        risk_tier="medium",
        summary=summary,
        args_path=args_path,
        requires_confirmation=True,
    )
    fresh_intent = evidence_ref(
        "fresh_user_intent",
        "test",
        "Fresh owner request to execute a governed Researcher run.",
        confidence=1.0,
    )
    approval = evidence_ref(
        "human_confirmation",
        "test",
        "Owner approved this exact Researcher run authority binding.",
        confidence=1.0,
    )
    envelope = kernel.create_envelope(
        selected_move="execute_action",
        intent_summary=summary,
        raw_turn_summary="Owner explicitly requested this governed Researcher run.",
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
        tool_name=RUN_EXECUTION_TOOL_NAME,
        status="not_started",
        output_path=args_path,
        summary="Researcher run is authorized but not started.",
    )
    return kernel.governor_decision(
        envelope,
        authorizations=[authorization],
        tool_ledgers=[ledger],
        reply_style="compact_status",
        reply_instruction="Execute the governed Researcher run.",
    )
