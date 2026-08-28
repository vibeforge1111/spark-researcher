from __future__ import annotations

import os
import re
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


def canonical_identifier(value: object) -> str:
    text = value if isinstance(value, str) else ""
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", text) is None:
        raise ValueError("Identifier is invalid")
    return text


def canonical_relative_path(path_text: object, *, allow_trailing_separator: bool = False) -> str | None:
    normalized = path_text.replace("\\", "/") if isinstance(path_text, str) else ""
    if allow_trailing_separator:
        normalized = normalized.rstrip("/")
    if (
        not normalized
        or normalized.startswith("/")
        or (len(normalized) >= 2 and normalized[1] == ":")
        or "\x00" in normalized
    ):
        return None
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    return "/".join(parts)


def resolve_owned_path(root: Path, path_text: object) -> Path:
    relative = canonical_relative_path(path_text)
    if relative is None:
        raise ValueError("Path is outside the owned root")
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve(strict=False)
    if not resolved.is_relative_to(resolved_root):
        raise ValueError("Path is outside the owned root")
    return resolved


def resolve_config_path(config_path: str | None = None) -> Path:
    path = Path(config_path or DEFAULT_CONFIG_NAME)
    return path.resolve()


def resolve_repo_root(config_path: Path | None = None) -> Path:
    return (config_path.parent if config_path else Path.cwd()).resolve()


def resolve_runtime_root(config_path: Path | None = None) -> Path:
    for env_name in ("SPARK_RESEARCHER_HOME", "SPARK_RESEARCHER_ROOT"):
        override = (os.environ.get(env_name) or "").strip()
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
    if repo_root is not None and not hasattr(repo_root, 'resolve'): from pathlib import Path; repo_root = Path(str(repo_root))
    try:
        return repo_root / ".spark-swarm"



    except Exception:
        return Path(".")
def spark_swarm_collective_payload_path(repo_root: Path) -> Path:
    if repo_root is not None and not hasattr(repo_root, 'resolve'): from pathlib import Path; repo_root = Path(str(repo_root))
    try:
        return spark_swarm_root(repo_root) / "collective-sync.json"

    except Exception:
        return Path(".")
