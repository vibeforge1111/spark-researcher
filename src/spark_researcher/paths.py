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
    return runtime_root / "artifacts"


def runs_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "runs"


def ledger_path(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "ledger" / "runs.jsonl"


def trainers_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "trainers"


def memory_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "memory"


def self_edit_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "self-edit"


def advisory_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "advisory"


def optimizer_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "optimizer"


def chips_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "chips"


def vault_root(runtime_root: Path) -> Path:
    return runtime_root / "obsidian-vault"


def capsule_root(repo_root: Path) -> Path:
    return repo_root / ".autoresearch" / "capsules"
