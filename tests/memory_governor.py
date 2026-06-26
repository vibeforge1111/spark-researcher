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
from spark_researcher.authority import MEMORY_WRITE_ACTION_TYPE, MEMORY_WRITE_CAPABILITY_ID, MEMORY_WRITE_TOOL_NAME


def memory_governor_decision(binding_refs: tuple[str, ...] = ("memory:materialize",)) -> dict:
    refs = tuple(str(ref) for ref in binding_refs if str(ref).strip())
    args_path = refs[0] if refs else "memory:materialize"
    kernel = HarnessKernel(surface="cli")
    action = kernel.proposed_action(
        capability_id=MEMORY_WRITE_CAPABILITY_ID,
        action_type=MEMORY_WRITE_ACTION_TYPE,
        risk_tier="low",
        summary="Materialize Spark memory artifacts.",
        args_path=args_path,
        requires_confirmation=False,
    )
    fresh_intent = evidence_ref(
        "fresh_user_intent",
        "test",
        "Fresh owner request for governed memory materialization.",
        confidence=1.0,
    )
    approval = evidence_ref(
        "human_confirmation",
        "test",
        "Owner approved governed memory materialization.",
        confidence=1.0,
    )
    binding_evidence = [
        evidence_ref(
            "authority_binding_ref",
            "test",
            ref,
            confidence=1.0,
        )
        for ref in refs
    ]
    canonical_binding_evidence = [
        evidence_ref(
            "policy",
            "issuer:spark-harness-core/governor",
            "Harness Core Governor issued this memory-write decision.",
            confidence=1.0,
        ),
        evidence_ref(
            "authority_binding_ref",
            "provenance:spark-harness-core/authorization",
            "Harness Core authorization provenance is bound to this decision.",
            confidence=1.0,
        ),
        evidence_ref(
            "runtime_state",
            "current-binding:spark-researcher",
            "Decision is bound to the current Spark Researcher runtime.",
            confidence=1.0,
        ),
    ]
    envelope = kernel.create_envelope(
        selected_move="execute_action",
        intent_summary="Materialize Spark memory.",
        raw_turn_summary="Owner requested governed memory materialization.",
        evidence=[fresh_intent, approval, *binding_evidence, *canonical_binding_evidence],
        proposed_actions=[action],
        authority_state="executable",
        risk_tier="low",
        confidence=1.0,
    )
    authorization = kernel.authorize(envelope, action, approval_ref=approval)
    ledger = kernel.record_tool_call(
        envelope=envelope,
        action=action,
        authorization=authorization,
        tool_name=MEMORY_WRITE_TOOL_NAME,
        status="not_started",
        output_path="memory:materialize",
        summary="Memory materialization is authorized but not started.",
    )
    return kernel.governor_decision(
        envelope,
        authorizations=[authorization],
        tool_ledgers=[ledger],
        reply_style="compact_status",
        reply_instruction="Materialize memory artifacts.",
    )
