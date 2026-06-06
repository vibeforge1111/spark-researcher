from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ProjectConfig, intent_policy, load_config
from .memory import search_memory
from .optimizer import optimizer_status
from .packets import search_packets
from .paths import resolve_runtime_root
from .ruvector import run_search as run_ruvector_search
from .ruvector import ruvector_status


def _search_query(config: ProjectConfig, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if config.intent.search_queries:
        return config.intent.search_queries[0]
    return config.intent.goal or config.intent.outcome


def _memory_context(config_path: Path, config: ProjectConfig, query: str, domain: str | None) -> dict[str, Any]:
    resources = set(config.intent.resource_modes)
    runtime_root = resolve_runtime_root(config_path)
    packet_hits = search_packets(config_path, query, limit=3, domain=domain) if "packets" in resources and query else {"packets": []}
    memory_hits: Any = []
    if "memory" in resources and query:
        try:
            memory_hits = search_memory(
                config_path.parent.resolve(),
                runtime_root,
                query,
                limit=3,
                backend=config.memory.backend,
                goal=config.eval_goal,
                config_path=config_path,
            )
        except (RuntimeError, OSError, ValueError) as exc:
            memory_hits = {"error": str(exc)}
    ruvector_hits: Any = []
    ruvector_info = ruvector_status() if "ruvector" in resources else {"status": "disabled"}
    if "ruvector" in resources and query and bool(ruvector_info.get("available")) and str(ruvector_info.get("status")) == "available":
        try:
            ruvector_hits = run_ruvector_search(query)
        except (RuntimeError, OSError, ValueError) as exc:
            ruvector_hits = {"error": str(exc)}
    return {
        "query": query,
        "packet_hits": packet_hits.get("packets", []),
        "memory_hits": memory_hits,
        "ruvector_status": ruvector_info,
        "ruvector_hits": ruvector_hits,
    }


def build_intent_brief(config_path: Path, *, domain: str | None = None, query: str | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    policy = intent_policy(config)
    search_query = _search_query(config, query)
    if not policy["active"]:
        return {
            **policy,
            "query": search_query,
            "memory_context": {"query": search_query, "packet_hits": [], "memory_hits": [], "ruvector_status": {"status": "disabled"}, "ruvector_hits": []},
            "optimizer": optimizer_status(),
        }
    return {
        **policy,
        "query": search_query,
        "memory_context": _memory_context(config_path, config, search_query, domain),
        "optimizer": optimizer_status() if "dspy" in set(config.intent.resource_modes) else {"available": False, "mode": "optional", "notes": ["DSPy optimization is disabled for this intent."]},
    }
