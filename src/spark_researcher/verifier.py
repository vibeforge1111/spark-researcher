from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapters import adapter_request, execute_advisory
from .failures import record_failure
from .tracing import start_trace

_TIME_SENSITIVE_MARKERS = (
    "latest",
    "recent",
    "current",
    "today",
    "now",
    "new",
    "version",
    "release",
    "price",
    "market",
    "law",
    "policy",
    "schedule",
    "availability",
    "news",
    "trend",
    "trending",
    "people saying",
)


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


def _failure_priority_checks(advisory: dict[str, Any], *, limit: int = 3) -> list[dict[str, Any]]:
    failure_priorities = advisory.get("failure_priorities", {})
    if not isinstance(failure_priorities, dict):
        return []
    checks: list[dict[str, Any]] = []
    for item in failure_priorities.get("priorities", [])[:limit]:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain") or "generic").strip() or "generic"
        surface = str(item.get("surface") or "unknown").strip() or "unknown"
        examples = []
        for example in item.get("top_examples", [])[:2]:
            if not isinstance(example, dict):
                continue
            summary = str(example.get("summary") or "").strip()
            if summary:
                examples.append(summary)
        checks.append(
            {
                "label": f"{domain}/{surface}",
                "score": item.get("surprise_score"),
                "examples": examples,
            }
        )
    return checks


def _critique_task(advisory: dict[str, Any], draft_text: str) -> str:
    epistemic = advisory.get("epistemic_status", {})
    lines = [
        "Review the draft answer below.",
        "Judge it against the guidance, boundaries, evidence status, and recent failure surfaces in the advisory request.",
        "If the evidence is too weak, prefer `needs_verification` over bluffing.",
        "",
        "Return JSON only in this exact shape:",
        '{"decision":"approve|revise|needs_verification","issues":[""],"missing_evidence":[""],"rewrite_instructions":[""],"best_next_question":"","implicated_failure_surface":""}',
        "",
        "Draft Answer",
        draft_text or "(empty)",
        "",
        f"Evidence Status: {epistemic.get('status', 'unknown')}",
    ]
    checks = _failure_priority_checks(advisory)
    if checks:
        lines.extend(["", "High-Surprise Failure Checks"])
        for item in checks:
            label = str(item.get("label") or "generic/unknown")
            score = item.get("score")
            lines.append(f"- Guard against {label} (surprise={score}).")
            for example in item.get("examples", []):
                lines.append(f"  Example: {example}")
        lines.append("If one of these failure surfaces is implicated, set `implicated_failure_surface` to the matching `domain/surface` label.")
    return "\n".join(lines)


def _revision_task(draft_text: str, critique: dict[str, Any]) -> str:
    issues = [str(item) for item in critique.get("issues", []) if str(item).strip()]
    missing = [str(item) for item in critique.get("missing_evidence", []) if str(item).strip()]
    instructions = [str(item) for item in critique.get("rewrite_instructions", []) if str(item).strip()]
    next_question = str(critique.get("best_next_question") or "").strip()
    implicated_surface = str(critique.get("implicated_failure_surface") or "").strip()
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
    if implicated_surface:
        lines.append(f"- Guardrail: do not repeat the high-surprise failure surface {implicated_surface}.")
    if next_question:
        lines.append(f"- If still under-supported, ask: {next_question}")
    return "\n".join(lines)


def _task_needs_fresh_research(advisory: dict[str, Any], critique: dict[str, Any]) -> bool:
    research_context = advisory.get("research_context", {})
    if isinstance(research_context, dict) and bool(research_context.get("attempted")):
        return False
    task = str(advisory.get("task") or "").lower()
    task_type = str(advisory.get("task_type") or "").lower()
    intent = advisory.get("intent", {})
    resources = {str(item).strip().lower() for item in intent.get("resource_modes", [])} if isinstance(intent, dict) else set()
    if "web" not in resources:
        return False
    if task_type.endswith("_research"):
        return True
    if any(marker in task for marker in _TIME_SENSITIVE_MARKERS):
        return True
    missing_evidence = [str(item).lower() for item in critique.get("missing_evidence", [])]
    issues = [str(item).lower() for item in critique.get("issues", [])]
    return any(
        marker in text
        for text in [*missing_evidence, *issues]
        for marker in ("fresh", "current", "recent", "source", "verify", "time-sensitive", "timely")
    )


def _research_packet(advisory: dict[str, Any], critique: dict[str, Any], *, trace_id: str, trace_path: str) -> dict[str, Any]:
    intent = advisory.get("intent", {})
    epistemic = advisory.get("epistemic_status", {})
    query = ""
    if isinstance(intent, dict):
        query = str(intent.get("query") or "").strip()
    if not query:
        query = str(advisory.get("task") or "").strip()
    targets = ["primary sources", "recent official documentation", "recent firsthand reports"]
    if str(advisory.get("task_type") or "").endswith("_research"):
        targets = ["recent primary sources", "contradictory viewpoints", "dated citations"]
    return {
        "status": "research_needed",
        "decision": "research_needed",
        "reason": "fresh_support_required",
        "research_query": query,
        "research_targets": targets,
        "recommended_actions": [
            "Search for fresh sources before answering.",
            "Prefer primary or official sources over secondary summaries.",
            "Return with dated evidence or keep the answer tentative.",
        ],
        "clarifying_questions": [
            item
            for item in [
                str(critique.get("best_next_question") or "").strip(),
                *list(epistemic.get("clarifying_questions", [])),
            ]
            if item
        ],
        "missing_evidence": list(critique.get("missing_evidence", [])),
        "implicated_failure_surface": str(critique.get("implicated_failure_surface") or "").strip(),
        "trace_id": trace_id,
        "trace_path": trace_path,
    }


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
        record_failure(
            runtime_root,
            failure_type="advisory_under_supported",
            summary=str(advisory.get("task") or "Task lacked enough evidence."),
            surface="advisory",
            domain=str(advisory.get("domain") or "generic"),
            severity="warn",
            novelty_key=f"{advisory.get('domain', 'generic')}:under_supported",
            evidence=[str(item) for item in epistemic.get("missing_evidence", [])],
            trace_id=trace.trace_id,
            metadata={"task": advisory.get("task"), "status": status},
        )
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
        "implicated_failure_surface": "",
    }
    decision = str(critique.get("decision") or "needs_verification").strip().lower()
    implicated_surface = str(critique.get("implicated_failure_surface") or "").strip()
    if implicated_surface:
        trace.event("implicated_failure_surface", attributes={"surface": implicated_surface})
    if decision == "approve":
        trace.finish(status="ok", attributes={"decision": decision, "implicated_failure_surface": implicated_surface})
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
        trace.finish(status="ok", attributes={"decision": "revise", "implicated_failure_surface": implicated_surface})
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
    if _task_needs_fresh_research(advisory, critique):
        packet = _research_packet(advisory, critique, trace_id=trace.trace_id, trace_path=str(trace.path))
        record_failure(
            runtime_root,
            failure_type="verifier_research_needed",
            summary=str(advisory.get("task") or "Verifier requested fresh research."),
            surface="verifier",
            domain=str(advisory.get("domain") or "generic"),
            severity="warn",
            novelty_key=f"{advisory.get('domain', 'generic')}:research_needed",
            evidence=[str(item) for item in critique.get("issues", [])[:2]] + [str(item) for item in critique.get("missing_evidence", [])[:2]],
            trace_id=trace.trace_id,
            metadata={
                "task": advisory.get("task"),
                "decision": decision,
                "research_query": packet["research_query"],
                "implicated_failure_surface": implicated_surface,
            },
        )
        trace.event(
            "research_escalation",
            attributes={
                "research_query": packet["research_query"],
                "implicated_failure_surface": implicated_surface,
            },
        )
        trace.finish(status="ok", attributes={"decision": "research_needed", "implicated_failure_surface": implicated_surface})
        return packet
    record_failure(
        runtime_root,
        failure_type="verifier_needs_verification",
        summary=str(advisory.get("task") or "Verifier requested further checking."),
        surface="verifier",
        domain=str(advisory.get("domain") or "generic"),
        severity="warn",
        novelty_key=f"{advisory.get('domain', 'generic')}:needs_verification",
        evidence=[str(item) for item in critique.get("issues", [])[:3]],
        trace_id=trace.trace_id,
        metadata={
            "task": advisory.get("task"),
            "decision": decision,
            "implicated_failure_surface": implicated_surface,
        },
    )
    trace.finish(status="ok", attributes={"decision": "needs_verification", "implicated_failure_surface": implicated_surface})
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
