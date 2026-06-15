from __future__ import annotations

from .advisory import build_advisory
from .collective import write_spark_swarm_collective_payload_from_latest
from .config import ProjectConfig, load_config
from .paths import ledger_path, resolve_runtime_root
from .research import execute_with_research, research_memory_authority_refs

BRIDGE_API_VERSION = "2026-06-13"

__all__ = [
    "BRIDGE_API_VERSION",
    "ProjectConfig",
    "build_advisory",
    "execute_with_research",
    "ledger_path",
    "load_config",
    "research_memory_authority_refs",
    "resolve_runtime_root",
    "write_spark_swarm_collective_payload_from_latest",
]
