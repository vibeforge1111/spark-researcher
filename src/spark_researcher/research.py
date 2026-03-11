from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .adapters import adapter_request
from .paths import advisory_root
from .tracing import start_trace
from .verifier import execute_with_verifier


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _now_slug() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")


def _bounded_web_results(query: str, *, limit: int = 5) -> list[dict[str, str]]:
    url = "https://html.duckduckgo.com/html/?" + urlencode({"q": query})
    request = Request(url, headers={"User-Agent": "spark-researcher/0.1"})
    try:
        page = urlopen(request, timeout=6).read().decode("utf-8", errors="replace")
    except Exception:
        return []
    titles = re.findall(r'result__a[^>]*>(.*?)</a>', page, flags=re.IGNORECASE | re.DOTALL)
    snippets = re.findall(r'result__snippet[^>]*>(.*?)</[^>]+>', page, flags=re.IGNORECASE | re.DOTALL)
    results: list[dict[str, str]] = []
    for index, title in enumerate(titles[:limit]):
        clean_title = re.sub(r"<.*?>", "", unescape(title)).strip()
        clean_snippet = ""
        if index < len(snippets):
            clean_snippet = re.sub(r"<.*?>", "", unescape(snippets[index])).strip()
        if clean_title:
            results.append({"title": clean_title, "snippet": clean_snippet})
    return results


def _write_research_artifact(runtime_root: Path, payload: dict[str, Any]) -> Path:
    root = advisory_root(runtime_root) / "research"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{_now_slug()}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _research_task(original_task: str, research: dict[str, Any]) -> str:
    lines = [
        "Answer the original task using only the bounded research notes below plus the existing advisory guidance.",
        "Treat the notes as dated evidence collected in one lightweight research pass.",
        "If the notes still do not support a strong answer, prefer `needs_verification` over bluffing.",
        "",
        "Original Task",
        original_task,
        "",
        f"Research Query: {research.get('query', '')}",
        f"Collected At: {research.get('collected_at', '')}",
        "Research Notes",
    ]
    for item in research.get("results", [])[:5]:
        title = str(item.get("title") or "").strip()
        snippet = str(item.get("snippet") or "").strip()
        if title:
            lines.append(f"- {title}")
        if snippet:
            lines.append(f"  Note: {snippet}")
    return "\n".join(lines)


def _followup_advisory(
    advisory: dict[str, Any],
    *,
    model: str,
    research: dict[str, Any],
) -> dict[str, Any]:
    original_task = str(advisory.get("task") or "")
    followup_task = _research_task(original_task, research)
    clone = dict(advisory)
    clone["task"] = followup_task
    clone["research_context"] = {
        "attempted": True,
        "original_task": original_task,
        "query": research.get("query"),
        "collected_at": research.get("collected_at"),
        "result_count": research.get("result_count"),
        "artifact_path": research.get("artifact_path"),
    }
    epistemic = dict(clone.get("epistemic_status", {}))
    if int(research.get("result_count", 0) or 0) > 0 and str(epistemic.get("status") or "") == "under_supported":
        epistemic["status"] = "partial"
    clone["epistemic_status"] = epistemic
    clone["adapter_request"] = adapter_request(model, followup_task, clone)
    return clone


def execute_with_research(
    runtime_root: Path,
    *,
    advisory: dict[str, Any],
    model: str,
    command_override: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    trace = start_trace(
        runtime_root,
        kind="advisory_research",
        name=model,
        parent_trace_id=str(advisory.get("trace_id") or "") or None,
        attributes={"model": model, "dry_run": dry_run},
    )
    if dry_run:
        packet = execute_with_verifier(
            runtime_root,
            advisory=advisory,
            model=model,
            command_override=command_override,
            dry_run=True,
        )
        packet["steps"] = list(dict.fromkeys([*list(packet.get("steps", [])), "conditional_research_retry"]))
        packet["research_trace_id"] = trace.trace_id
        packet["research_trace_path"] = str(trace.path)
        trace.finish(status="ok", attributes={"mode": "dry_run"})
        return packet
    initial = execute_with_verifier(
        runtime_root,
        advisory=advisory,
        model=model,
        command_override=command_override,
        dry_run=False,
    )
    if str(initial.get("status") or "") != "research_needed":
        trace.finish(status="ok", attributes={"decision": initial.get("decision", initial.get("status", "unknown"))})
        return initial
    query = str(initial.get("research_query") or advisory.get("task") or "").strip()
    with trace.span("bounded_research", attributes={"query": query}):
        results = _bounded_web_results(query)
    research = {
        "query": query,
        "collected_at": _now_iso(),
        "result_count": len(results),
        "results": results,
        "targets": list(initial.get("research_targets", [])),
    }
    artifact_path = _write_research_artifact(runtime_root, research)
    research["artifact_path"] = str(artifact_path)
    if not results:
        packet = dict(initial)
        packet["research_attempted"] = True
        packet["research_result_count"] = 0
        packet["research_artifact_path"] = str(artifact_path)
        packet["recommended_actions"] = [
            "Research attempt returned no usable web notes.",
            *list(packet.get("recommended_actions", [])),
        ]
        trace.finish(status="ok", attributes={"decision": "research_needed", "research_result_count": 0})
        return packet
    followup = execute_with_verifier(
        runtime_root,
        advisory=_followup_advisory(advisory, model=model, research=research),
        model=model,
        command_override=command_override,
        dry_run=False,
    )
    if isinstance(followup, dict):
        followup["initial_research_packet"] = initial
        followup["research_context"] = research
        followup["research_trace_id"] = trace.trace_id
        followup["research_trace_path"] = str(trace.path)
    trace.finish(
        status="ok",
        attributes={
            "decision": followup.get("decision", followup.get("status", "unknown")),
            "research_result_count": len(results),
        },
    )
    return followup
