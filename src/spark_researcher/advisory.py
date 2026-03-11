from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapters import adapter_request
from .chips import load_chip_context
from .config import load_config
from .failures import surprise_status
from .intent import build_intent_brief
from .memory import write_working_memory
from .optimizer import optimizer_status
from .packets import search_packets
from .paths import resolve_runtime_root
from .tracing import start_trace


def _infer_domain(config_path: Path, explicit_domain: str | None = None) -> str:
    if explicit_domain:
        return explicit_domain
    context = load_chip_context(config_path)
    if context is not None:
        return str(context.manifest.get("domain", "generic"))
    return "generic"


def _task_type(task: str, domain: str) -> str:
    lowered = task.lower()
    if "belief" in lowered or "packet" in lowered:
        return f"{domain}_packeting"
    if "research" in lowered or "explore" in lowered:
        return f"{domain}_research"
    if "improve" in lowered or "optimize" in lowered:
        return f"{domain}_optimization"
    return f"{domain}_advisory"


def _compress_claim(text: str, *, limit: int = 140) -> str:
    compact = " ".join(text.split()).lstrip("- ").strip()
    return compact if len(compact) <= limit else compact[: limit - 3].rstrip() + "..."


def _guidance_from_packets(packet_rows: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    guidance: list[str] = []
    boundaries: list[str] = []
    for row in packet_rows:
        claim = str(row.get("claim") or "").strip()
        boundary = str(row.get("boundary") or "").strip()
        if claim:
            guidance.append(_compress_claim(claim))
        if boundary:
            boundaries.append(_compress_claim(boundary))
    deduped_guidance = list(dict.fromkeys(guidance))[:4]
    deduped_boundaries = list(dict.fromkeys(boundaries))[:3]
    return deduped_guidance, deduped_boundaries


def _result_count(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            return len(payload["results"])
        if "error" in payload:
            return 0
    return 0


def _epistemic_packet(
    *,
    task: str,
    packet_rows: list[dict[str, Any]],
    guidance: list[str],
    boundaries: list[str],
    intent: dict[str, Any],
) -> dict[str, Any]:
    memory_context = intent.get("memory_context", {}) if isinstance(intent, dict) else {}
    memory_hits = _result_count(memory_context.get("memory_hits", []))
    ruvector_hits = _result_count(memory_context.get("ruvector_hits", []))
    packet_count = len(packet_rows)
    if packet_count >= 1 and guidance and boundaries:
        status = "grounded"
    elif packet_count >= 1 or memory_hits > 0 or ruvector_hits > 0:
        status = "partial"
    else:
        status = "under_supported"
    missing = []
    if packet_count == 0:
        missing.append("No directly relevant packets were selected.")
    if memory_hits <= 0 and ruvector_hits <= 0:
        missing.append("No supporting memory hits were found for this task.")
    if not boundaries:
        missing.append("No explicit boundary guidance was available, so claims should stay narrow.")
    recommended = {
        "grounded": [
            "Use the selected packets, but keep claims bounded by the listed boundaries.",
        ],
        "partial": [
            "State uncertainty explicitly before making strong claims.",
            "Ask at least one clarifying question if the task depends on unstated constraints.",
            "Prefer verification or fresh research before giving irreversible advice.",
        ],
        "under_supported": [
            "Ask clarifying questions before answering.",
            "Research or retrieve evidence before making durable claims.",
            "Avoid confident recommendations until evidence improves.",
        ],
    }[status]
    questions = []
    if status != "grounded":
        questions = [
            "What exact outcome or evaluator should this answer optimize for?",
            "What constraints, boundaries, or source requirements should the answer respect?",
            "Which parts of this task are time-sensitive enough to require fresh verification?",
        ]
    return {
        "status": status,
        "packet_count": packet_count,
        "memory_hit_count": memory_hits,
        "ruvector_hit_count": ruvector_hits,
        "missing_evidence": missing,
        "recommended_actions": recommended,
        "clarifying_questions": questions,
        "task": task,
    }


def build_advisory(config_path: Path, task: str, *, model: str = "generic", limit: int = 4, domain: str | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    runtime_root = resolve_runtime_root(config_path)
    trace = start_trace(
        runtime_root,
        kind="advisory_build",
        name=task[:80],
        attributes={"model": model, "limit": limit},
    )
    selected_domain = _infer_domain(config_path, domain)
    try:
        with trace.span("packet_search", attributes={"domain": selected_domain}):
            packet_search = search_packets(config_path, task, limit=limit, domain=None if selected_domain == "generic" else selected_domain)
            packet_rows = packet_search["packets"]
        guidance, boundaries = _guidance_from_packets(packet_rows)
        with trace.span("intent_brief", attributes={"domain": selected_domain}):
            intent = build_intent_brief(config_path, domain=selected_domain, query=task)
        failure_priorities = surprise_status(runtime_root, limit=5)
        epistemic = _epistemic_packet(task=task, packet_rows=packet_rows, guidance=guidance, boundaries=boundaries, intent=intent)
        advisory = {
            "project_name": config.project_name,
            "task": task,
            "task_type": _task_type(task, selected_domain),
            "domain": selected_domain,
            "selected_packet_ids": [str(item["packet_id"]) for item in packet_rows],
            "guidance": guidance,
            "boundaries": boundaries,
            "packets": packet_rows,
            "optimizer": optimizer_status(),
            "intent": intent,
            "failure_priorities": failure_priorities,
            "epistemic_status": epistemic,
            "trace_id": trace.trace_id,
            "trace_path": str(trace.path),
        }
        advisory["adapter_request"] = adapter_request(model, task, advisory)
        write_working_memory(
            runtime_root,
            kind="advisory",
            focus=task,
            status=str(epistemic.get("status") or "unknown"),
            trace_id=trace.trace_id,
            notes=[*guidance[:2], *epistemic.get("recommended_actions", [])[:2]],
            questions=list(epistemic.get("clarifying_questions", []))[:3],
        )
        trace.event(
            "epistemic_status",
            attributes={
                "status": epistemic["status"],
                "packet_count": epistemic["packet_count"],
                "memory_hit_count": epistemic["memory_hit_count"],
                "ruvector_hit_count": epistemic["ruvector_hit_count"],
                "priority_count": len(failure_priorities.get("priorities", [])),
            },
        )
        trace.finish(status="ok", attributes={"status": epistemic["status"]})
        return advisory
    except Exception as exc:
        trace.finish(status="error", attributes={"error": str(exc)})
        raise
