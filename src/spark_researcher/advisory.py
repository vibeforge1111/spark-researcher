from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapters import adapter_request
from .chips import load_chip_context
from .config import load_config
from .intent import build_intent_brief
from .optimizer import optimizer_status
from .packets import search_packets


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


def build_advisory(config_path: Path, task: str, *, model: str = "generic", limit: int = 4, domain: str | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    selected_domain = _infer_domain(config_path, domain)
    packet_search = search_packets(config_path, task, limit=limit, domain=None if selected_domain == "generic" else selected_domain)
    packet_rows = packet_search["packets"]
    guidance, boundaries = _guidance_from_packets(packet_rows)
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
        "intent": build_intent_brief(config_path, domain=selected_domain, query=task),
    }
    advisory["adapter_request"] = adapter_request(model, task, advisory)
    return advisory
