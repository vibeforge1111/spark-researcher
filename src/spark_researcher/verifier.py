from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapters import adapter_request, execute_advisory
from .tracing import start_trace


def _response_text(payload: Any) -> str:
    if isinstance(payload, dict):
        raw = payload.get("raw_response")
        if isinstance(raw, str):
            return raw.strip()
        return json.dumps(payload, indent=2, sort_keys=True)
    if isinstance(payload, str):
        return payload.strip()
    return str(payload).strip()


def _parse_json(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    candidates = [stripped]
    if "{" in stripped and "}" in stripped:
        candidates.append(stripped[stripped.find("{") : stripped.rfind("}") + 1])
    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _advisory_clone(advisory: dict[str, Any], *, task: str, model: str) -> dict[str, Any]:
    clone = dict(advisory)
    clone["task"] = task
    clone["adapter_request"] = adapter_request(model, task, clone)
    return clone


def _critique_task(advisory: dict[str, Any], draft_text: str) -> str:
    epistemic = advisory.get("epistemic_status", {})
    return "\n".join(
        [
            "Review the draft answer below.",
            "Judge it against the guidance, boundaries, and evidence status in the advisory request.",
            "If the evidence is too weak, prefer `needs_verification` over bluffing.",
            "",
            "Return JSON only in this exact shape:",
            '{"decision":"approve|revise|needs_verification","issues":[""],"missing_evidence":[""],"rewrite_instructions":[""],"best_next_question":""}',
            "",
            "Draft Answer",
            draft_text or "(empty)",
            "",
            f"Evidence Status: {epistemic.get('status', 'unknown')}",
        ]
    )


def _revision_task(draft_text: str, critique: dict[str, Any]) -> str:
    issues = [str(item) for item in critique.get("issues", []) if str(item).strip()]
    missing = [str(item) for item in critique.get("missing_evidence", []) if str(item).strip()]
    instructions = [str(item) for item in critique.get("rewrite_instructions", []) if str(item).strip()]
    next_question = str(critique.get("best_next_question") or "").strip()
    lines = [
        "Revise the answer below using the critique.",
        "Stay within the evidence you actually have.",
        "Do not invent support that is missing.",
        "",
        "Current Draft",
        draft_text or "(empty)",
        "",
        "Critique",
    ]
    lines.extend(f"- Issue: {item}" for item in issues[:4])
    lines.extend(f"- Missing Evidence: {item}" for item in missing[:3])
    lines.extend(f"- Rewrite Instruction: {item}" for item in instructions[:4])
    if next_question:
        lines.append(f"- If still under-supported, ask: {next_question}")
    return "\n".join(lines)


def execute_with_verifier(
    runtime_root: Path,
    *,
    advisory: dict[str, Any],
    model: str,
    command_override: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    trace = start_trace(
        runtime_root,
        kind="advisory_verify",
        name=model,
        parent_trace_id=str(advisory.get("trace_id") or "") or None,
        attributes={"model": model, "dry_run": dry_run},
    )
    epistemic = advisory.get("epistemic_status", {})
    status = str(epistemic.get("status") or "unknown")
    if status == "under_supported":
        packet = {
            "status": "needs_verification",
            "decision": "needs_verification",
            "reason": "advisory_under_supported",
            "clarifying_questions": list(epistemic.get("clarifying_questions", [])),
            "missing_evidence": list(epistemic.get("missing_evidence", [])),
            "trace_id": trace.trace_id,
            "trace_path": str(trace.path),
        }
        trace.finish(status="ok", attributes={"decision": "needs_verification", "reason": "advisory_under_supported"})
        return packet
    if dry_run:
        draft = execute_advisory(runtime_root, advisory=advisory, model=model, command_override=command_override, dry_run=True)
        trace.finish(status="ok", attributes={"mode": "dry_run", "steps": ["draft", "critique", "optional_revise"]})
        return {
            "status": "dry_run",
            "decision": "planned",
            "steps": ["draft", "critique", "optional_revise"],
            "draft": draft,
            "trace_id": trace.trace_id,
            "trace_path": str(trace.path),
        }
    with trace.span("draft"):
        draft = execute_advisory(runtime_root, advisory=advisory, model=model, command_override=command_override, dry_run=False)
    draft_text = _response_text(draft.get("response", {}))
    critique_task = _critique_task(advisory, draft_text)
    critique_advisory = _advisory_clone(advisory, task=critique_task, model=model)
    with trace.span("critique"):
        critique_result = execute_advisory(runtime_root, advisory=critique_advisory, model=model, command_override=command_override, dry_run=False)
    critique_text = _response_text(critique_result.get("response", {}))
    critique = _parse_json(critique_text) or {
        "decision": "needs_verification",
        "issues": ["Verifier did not return parseable JSON."],
        "missing_evidence": [],
        "rewrite_instructions": [],
        "best_next_question": "",
    }
    decision = str(critique.get("decision") or "needs_verification").strip().lower()
    if decision == "approve":
        trace.finish(status="ok", attributes={"decision": decision})
        return {
            "status": "ok",
            "decision": decision,
            "response": draft.get("response"),
            "draft": draft,
            "critique": critique,
            "trace_id": trace.trace_id,
            "trace_path": str(trace.path),
        }
    if decision == "revise":
        revision_task = _revision_task(draft_text, critique)
        revision_advisory = _advisory_clone(advisory, task=revision_task, model=model)
        with trace.span("revise"):
            revised = execute_advisory(runtime_root, advisory=revision_advisory, model=model, command_override=command_override, dry_run=False)
        trace.finish(status="ok", attributes={"decision": "revise"})
        return {
            "status": "ok",
            "decision": "revise",
            "response": revised.get("response"),
            "draft": draft,
            "critique": critique,
            "revised": revised,
            "trace_id": trace.trace_id,
            "trace_path": str(trace.path),
        }
    trace.finish(status="ok", attributes={"decision": "needs_verification"})
    return {
        "status": "needs_verification",
        "decision": "needs_verification",
        "response": None,
        "draft": draft,
        "critique": critique,
        "clarifying_questions": [item for item in [str(critique.get("best_next_question") or "").strip(), *list(epistemic.get("clarifying_questions", []))] if item],
        "trace_id": trace.trace_id,
        "trace_path": str(trace.path),
    }
