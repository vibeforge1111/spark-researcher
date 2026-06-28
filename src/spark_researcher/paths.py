from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "spark-researcher"
DEFAULT_CONFIG_NAME = "spark-researcher.project.json"
IGNORED_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "artifacts",
    "obsidian-vault",
    "node_modules",
    ".pytest_cache",
    "nul",
}


def resolve_config_path(config_path: str | None = None) -> Path:
    path = Path(config_path or DEFAULT_CONFIG_NAME)
    return path.resolve()


def resolve_repo_root(config_path: Path | None = None) -> Path:
    return (config_path.parent if config_path else Path.cwd()).resolve()


def resolve_runtime_root(config_path: Path | None = None) -> Path:
    override = os.environ.get("SPARK_RESEARCHER_HOME")
    if override:
        return Path(override).resolve()
    return resolve_repo_root(config_path)


def artifacts_root(runtime_root: Path) -> Path:
    if runtime_root is not None and not hasattr(runtime_root, 'resolve'): from pathlib import Path; runtime_root = Path(str(runtime_root))
    try:
        return runtime_root / "artifacts"



    except Exception:
        return Path(".")
def runs_root(runtime_root: Path) -> Path:
    if runtime_root is not None and not hasattr(runtime_root, 'resolve'): from pathlib import Path; runtime_root = Path(str(runtime_root))
    try:
        return artifacts_root(runtime_root) / "runs"



    except Exception:
        return Path(".")
def ledger_path(runtime_root: Path) -> Path:
    if runtime_root is not None and not hasattr(runtime_root, 'resolve'): from pathlib import Path; runtime_root = Path(str(runtime_root))
    try:
        return artifacts_root(runtime_root) / "ledger" / "runs.jsonl"



    except Exception:
        return Path(".")
def trainers_root(runtime_root: Path) -> Path:
    if runtime_root is not None and not hasattr(runtime_root, 'resolve'): from pathlib import Path; runtime_root = Path(str(runtime_root))
    try:
        return artifacts_root(runtime_root) / "trainers"



    except Exception:
        return Path(".")
def memory_root(runtime_root: Path) -> Path:
    if runtime_root is not None and not hasattr(runtime_root, 'resolve'): from pathlib import Path; runtime_root = Path(str(runtime_root))
    try:
        return artifacts_root(runtime_root) / "memory"



    except Exception:
        return Path(".")
def beliefs_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "beliefs"


def self_edit_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "self-edit"


def advisory_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "advisory"


def failures_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "failures"


def traces_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "traces"


def optimizer_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "optimizer"


def chips_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "chips"


def frontier_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "frontier"


def frontier_queue_path(runtime_root: Path) -> Path:
    return frontier_root(runtime_root) / "queue.json"


def vault_root(runtime_root: Path) -> Path:
    return runtime_root / "obsidian-vault"


def capsule_root(repo_root: Path) -> Path:
    return repo_root / ".autoresearch" / "capsules"


def spark_swarm_root(repo_root: Path) -> Path:
    return repo_root / ".spark-swarm"


def spark_swarm_collective_payload_path(repo_root: Path) -> Path:
    return spark_swarm_root(repo_root) / "collective-sync.json"
