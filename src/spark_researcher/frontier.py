from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request

from .adapters import execute_advisory
from .advisory import build_advisory
from .chips import load_chip_context
from .config import load_config
from .failures import surprise_status
from .intent import build_intent_brief
from .paths import resolve_runtime_root
from .safe_url import safe_urlopen
from .tracing import start_trace
from .trial_queue import merged_candidate_trials


def _signature(mutations: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), str(value)) for key, value in mutations.items()))


def _candidate_id(mutations: dict[str, str]) -> str:
    parts = [f"{name}-{value}".replace(":", "-").replace(".", "").replace(" ", "-") for name, value in sorted(mutations.items())]
    return "frontier-" + "-".join(parts)


def _parse_json(text: str) -> dict[str, Any] | None:
    for candidate in (text.strip(), text[text.find("{") : text.rfind("}") + 1] if "{" in text and "}" in text else ""):
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _match_open_field(block: str, field_name: str, pattern: str) -> str:
    field_match = re.search(rf"{re.escape(field_name)}\s*[:=]\s*`?([a-z0-9:_-]+)`?", block, flags=re.IGNORECASE)
    if field_match and re.fullmatch(pattern, field_match.group(1)):
        return field_match.group(1)
    for token in re.findall(r"[a-z0-9:_-]+", block, flags=re.IGNORECASE):
        if re.fullmatch(pattern, token):
            return token
    return ""


def _parse_text(text: str, allowed: dict[str, list[str]], open_fields: set[str], field_patterns: dict[str, str]) -> dict[str, Any]:
    proposals = []
    for block in [item.strip() for item in re.split(r"\n\s*(?:#{2,}\s*|\d+\.\s+)", text) if item.strip()]:
        mutations: dict[str, str] = {}
        for name, values in allowed.items():
            value = next((item for item in values if item in block), "")
            if not value and name in open_fields:
                value = _match_open_field(block, name, field_patterns.get(name, r"^[a-z0-9:_-]+$"))
            if value:
                mutations[name] = value
        if not mutations:
            continue
        rationale = re.search(r"Rationale\s*:\s*(.*)", block)
        hypothesis = re.search(r"Hypothesis\s*:\s*(.*)", block)
        proposals.append({"candidate_summary": block.splitlines()[0][:160], "hypothesis": hypothesis.group(1).strip() if hypothesis else "", "mutations": mutations, "why_now": [rationale.group(1).strip()] if rationale else []})
    return {"proposals": proposals}
def _web_notes(query: str, *, limit: int = 3) -> list[str]:
    url = "https://html.duckduckgo.com/html/?" + urlencode({"q": query})
    request = Request(url, headers={"User-Agent": "spark-researcher/0.1"})
    try:
        with safe_urlopen(request, timeout=6) as response:
            page = response.read().decode("utf-8", errors="replace")
    except (URLError, OSError, ValueError):
        return []
    titles = re.findall(r'result__a[^>]*>(.*?)</a>', page, flags=re.IGNORECASE | re.DOTALL)
    notes = []
    for title in titles[:limit]:
        clean = re.sub(r"<.*?>", "", unescape(title)).strip()
        if clean:
            notes.append(clean)
    return notes
def frontier_suggest(config_path: Path, command_name: str, *, rows: list[dict[str, Any]], limit: int = 3) -> dict[str, Any]:
    config = load_config(config_path)
    runtime_root = resolve_runtime_root(config_path)
    trace = start_trace(runtime_root, kind="frontier_suggest", name=command_name, attributes={"limit": limit})
    context = load_chip_context(config_path, config)
    spec = context.manifest.get("frontier", {}) if context is not None else {}
    if not isinstance(spec, dict) or not spec.get("enabled", False):
        trace.finish(status="ok", attributes={"suggestion_count": 0, "reason": "frontier_disabled"})
        return {"source": "frontier", "suggestion_count": 0, "suggestions": [], "reasons": ["No frontier sidecar is enabled for this chip."]}
    allowed = {str(name): [str(item) for item in values] for name, values in spec.get("allowed_mutations", {}).items() if isinstance(values, list)}
    open_fields = {str(item) for item in spec.get("open_mutation_fields", []) if isinstance(item, str)}
    field_patterns = {str(name): str(pattern) for name, pattern in spec.get("field_patterns", {}).items() if isinstance(pattern, str)}
    prompt_hints = [str(item) for item in spec.get("prompt_hints", []) if isinstance(item, str)]
    if not allowed:
        trace.finish(status="ok", attributes={"suggestion_count": 0, "reason": "missing_allowed_mutations"})
        return {"source": "frontier", "suggestion_count": 0, "suggestions": [], "reasons": ["No allowed mutation grammar is defined for this chip frontier."]}
    existing = {_signature(trial.mutations) for trial in merged_candidate_trials(config_path, config=config)}
    tested = {
        _signature({str(item["name"]): str(item["value"]) for item in row.get("applied_mutations", [])})
        for row in rows
        if row.get("command_name") == command_name
    }
    best_rows = [row for row in rows if row.get("command_name") == command_name and row.get("applied_mutations")][-3:]
    best_rows = sorted(best_rows, key=lambda item: float(item.get("metric_value", 0.0) or 0.0), reverse=config.eval_goal == "maximize")[:3]
    winner_text = [
        {"candidate_id": row.get("candidate_id"), "metric_value": row.get("metric_value"), "verdict": row.get("verdict"), "mutations": {str(item["name"]): str(item["value"]) for item in row.get("applied_mutations", [])}}
        for row in best_rows
    ]
    query = f"{context.manifest.get('domain', 'generic')} " + " ".join(str(value) for row in winner_text[:1] for value in row["mutations"].values())
    with trace.span("web_notes", attributes={"web_search": bool(spec.get("web_search", False)), "query": query}):
        web_notes = _web_notes(query) if spec.get("web_search", False) and query.strip() else []
    with trace.span("intent_brief", attributes={"domain": str(context.manifest.get("domain", "generic"))}):
        intent = build_intent_brief(config_path, domain=str(context.manifest.get("domain", "generic")), query=query)
    failure_priorities = surprise_status(runtime_root, limit=5)
    frontier_mode = str(intent.get("frontier_mode") or "relaxed")
    effective_open_fields = set() if frontier_mode == "bounded" else open_fields
    task = "\n".join(
        [
            f"Propose at most {limit} new bounded research candidates for the `{context.manifest.get('domain', 'generic')}` chip.",
            f"Command: {command_name}. Metric: {config.eval_metric}. Goal: {config.eval_goal}.",
            f"Mission goal: {intent.get('goal') or ''}",
            f"Mission target outcome: {intent.get('outcome') or ''}",
            f"Mission success criteria: {json.dumps(intent.get('success_criteria', []))}",
            f"Mission frontier mode: {intent.get('frontier_mode') or 'relaxed'}",
            f"Mission resources: {json.dumps(intent.get('resource_modes', []))}",
            f"Seed mutation grammar: {json.dumps(allowed, sort_keys=True)}",
            f"Open mutation fields: {json.dumps(sorted(effective_open_fields))}",
            f"Field patterns for open fields: {json.dumps(field_patterns, sort_keys=True)}",
            f"Required fields: {json.dumps([str(item) for item in spec.get('required_fields', [])])}",
            f"Already tested or queued signatures: {json.dumps([[name, value] for sig in sorted(tested | existing) for name, value in sig][:24])}",
            f"Current strongest rows: {json.dumps(winner_text, sort_keys=True)}",
            f"Web notes: {json.dumps(web_notes)}",
            f"Intent packet hits: {json.dumps(intent.get('memory_context', {}).get('packet_hits', []), sort_keys=True)}",
            f"Intent memory hits: {json.dumps(intent.get('memory_context', {}).get('memory_hits', []), sort_keys=True)}",
            f"RuVector status: {json.dumps(intent.get('memory_context', {}).get('ruvector_status', {}), sort_keys=True)}",
            f"RuVector hits: {json.dumps(intent.get('memory_context', {}).get('ruvector_hits', []), sort_keys=True)}",
            f"DSPy optimizer status: {json.dumps(intent.get('optimizer', {}), sort_keys=True)}",
            f"Current failure priorities: {json.dumps(failure_priorities, sort_keys=True)}",
            f"Prompt hints: {json.dumps(prompt_hints)}",
            'Return JSON only in the shape {"proposals":[{"candidate_id":"","candidate_summary":"","hypothesis":"","mutations":{},"why_now":["",""]}]}',
            "Rules: use only allowed field names, do not repeat tested signatures, prefer proposals that serve the active mission, and only invent new values for fields listed in `open_mutation_fields`.",
            "If frontier mode is `open`, prefer at least one serious novel proposal on an open field before repeating seeded values.",
        ]
    )
    advisory = build_advisory(config_path, task, model=str(spec.get("model", "generic")), limit=3, domain=str(context.manifest.get("domain", "generic")))
    try:
        response = execute_advisory(runtime_root, advisory=advisory, model=str(spec.get("model", "generic")), dry_run=False)
    except (RuntimeError, OSError) as exc:
        trace.finish(status="error", attributes={"error": str(exc)})
        return {"source": "frontier", "suggestion_count": 0, "suggestions": [], "reasons": [f"Frontier execution unavailable: {exc}"]}
    payload = response.get("response", {})
    if isinstance(payload, dict) and "proposals" in payload:
        parsed = payload
    else:
        parsed = _parse_json(str(payload.get("raw_response", ""))) if isinstance(payload, dict) else None
    if not isinstance(parsed, dict) or "proposals" not in parsed:
        parsed = _parse_text(str(payload.get("raw_response", "")), allowed, effective_open_fields, field_patterns) if isinstance(payload, dict) else {"proposals": []}
    proposals = parsed.get("proposals", []) if isinstance(parsed, dict) else []
    required = {str(item) for item in spec.get("required_fields", [])}
    suggestions: list[dict[str, Any]] = []
    reasons: list[str] = []
    for item in proposals:
        if not isinstance(item, dict):
            continue
        mutations = {str(key): str(value) for key, value in item.get("mutations", {}).items()}
        if not required.issubset(mutations):
            continue
        valid = True
        for name, value in mutations.items():
            if name not in allowed:
                valid = False
                break
            if value in allowed[name]:
                continue
            if name in effective_open_fields:
                pattern = field_patterns.get(name, r"^[a-z0-9:_-]+$")
                if re.fullmatch(pattern, value):
                    continue
            valid = False
            break
        if not valid:
            continue
        sig = _signature(mutations)
        if sig in tested or sig in existing:
            continue
        existing.add(sig)
        suggestions.append(
            {
                "candidate_id": str(item.get("candidate_id") or _candidate_id(mutations)),
                "candidate_summary": str(item.get("candidate_summary", "LLM frontier proposal.")),
                "hypothesis": str(item.get("hypothesis", "The next bounded probe may refine the current doctrine.")),
                "mutations": mutations,
            }
        )
        why_now = item.get("why_now", [])
        if isinstance(why_now, list) and why_now:
            reasons.append("; ".join(str(entry) for entry in why_now[:2]))
        if len(suggestions) >= limit:
            break
    packet = {
        "source": "frontier",
        "chip_name": context.manifest.get("chip_name"),
        "suggestion_count": len(suggestions),
        "suggestions": suggestions,
        "reasons": reasons[: len(suggestions)] or (["Frontier sidecar recovered valid bounded candidates from the model response."] if suggestions else ["Frontier sidecar did not produce any valid new candidates."]),
        "web_notes": web_notes,
        "trace_id": trace.trace_id,
        "trace_path": str(trace.path),
    }
    trace.finish(status="ok", attributes={"suggestion_count": len(suggestions), "web_note_count": len(web_notes)})
    return packet
