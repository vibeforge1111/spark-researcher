from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .paths import capsule_root, ledger_path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")


def latest_metric_run(runtime_root: Path) -> dict[str, Any] | None:
    rows = read_jsonl(ledger_path(runtime_root))
    metric_rows = [row for row in rows if isinstance(row.get("metric_value"), (int, float))]
    return metric_rows[-1] if metric_rows else None


def publish_latest(repo_root: Path, runtime_root: Path) -> dict[str, Any]:
    run = latest_metric_run(runtime_root)
    if run is None:
        raise RuntimeError("No metric runs available to publish.")
    capsule_id = f"{now_stamp()}-{run.get('run_id')}"
    root = capsule_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "capsule_id": capsule_id,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "title": f"{run.get('project_name')} {run.get('candidate_id') or run.get('run_id')}",
        "summary": f"{run.get('verdict')} on {run.get('metric_name')}={run.get('metric_value')}",
        "metric_name": run.get("metric_name"),
        "metric_value": run.get("metric_value"),
        "baseline_value": run.get("baseline_value"),
        "verdict": run.get("verdict"),
        "run_id": run.get("run_id"),
        "artifact_paths": [run.get("run_dir"), run.get("log_path")],
    }
    markdown = "\n".join(
        [
            "---",
            *(f"{key}: {json.dumps(value) if isinstance(value, (dict, list)) else value}" for key, value in payload.items()),
            "export_kind: latest",
            "---",
            "",
            f"# {payload['title']}",
            "",
            payload["summary"],
            "",
            f"- metric: `{payload['metric_name']}` = `{payload['metric_value']}`",
            f"- baseline: `{payload['baseline_value']}`",
            f"- verdict: `{payload['verdict']}`",
            f"- run_id: `{payload['run_id']}`",
        ]
    )
    md_path = root / f"{capsule_id}.md"
    json_path = root / f"{capsule_id}.manifest.json"
    md_path.write_text(markdown + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"capsule_id": capsule_id, "markdown_path": str(md_path), "manifest_path": str(json_path)}


def collective_status(repo_root: Path, runtime_root: Path) -> dict[str, Any]:
    root = capsule_root(repo_root)
    sibling_collective = repo_root.parent / "autoresearch-collective"
    latest = latest_metric_run(runtime_root)
    return {
        "capsule_root": str(root),
        "capsule_count": len(list(root.glob("*.md"))) if root.exists() else 0,
        "latest_metric_run": latest.get("run_id") if latest else None,
        "collective_repo_present": sibling_collective.exists(),
        "collective_repo_path": str(sibling_collective),
    }


def _repo_sources_path(collective_root: Path) -> Path:
    return collective_root / "dashboard" / "config" / "repo-sources.local.json"


def _generated_index_path(collective_root: Path) -> Path:
    return collective_root / "dashboard" / "public" / "data" / "collective.generated.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_repo_slug(repo_root: Path) -> str:
    path = repo_root / "AUTORESEARCH.md"
    if not path.exists():
        return repo_root.name
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("repo:"):
            return line.split(":", 1)[1].strip()
    return repo_root.name


def sync_local_collective(repo_root: Path, runtime_root: Path, *, label: str | None = None, rebuild: bool = True) -> dict[str, Any]:
    collective_root = repo_root.parent / "autoresearch-collective"
    if not collective_root.exists():
        raise RuntimeError(f"Collective repo not found: {collective_root}")
    config_path = _repo_sources_path(collective_root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _load_json(config_path) if config_path.exists() else {"sources": []}
    sources = list(payload.get("sources", []))
    repo_path_text = str(repo_root).replace("\\", "/")
    entry = next((item for item in sources if str(item.get("path", "")).replace("\\", "/") == repo_path_text), None)
    if entry is None:
        entry = {"kind": "repo", "label": label or repo_root.name, "path": repo_path_text}
        sources.append(entry)
    else:
        if label:
            entry["label"] = label
    payload["sources"] = sources
    config_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    commands_run = []
    if rebuild:
        for script_name in ("build-collective-data.mjs", "build-graph-data.mjs"):
            command = ["node", f"./scripts/{script_name}"]
            process = subprocess.run(
                command,
                cwd=str(collective_root / "dashboard"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            commands_run.append(
                {
                    "command": command,
                    "returncode": process.returncode,
                    "stdout_excerpt": process.stdout[:400],
                    "stderr_excerpt": process.stderr[:400],
                }
            )
            if process.returncode != 0:
                raise RuntimeError(f"Collective rebuild failed for {script_name}: {process.stderr.strip()}")
    generated = _load_json(_generated_index_path(collective_root))
    repo_slug = _manifest_repo_slug(repo_root)
    repo_connected = any(item.get("repo") == repo_slug for item in generated.get("repoDirectory", []))
    capsule_indexed = any(item.get("repo") == repo_slug for item in generated.get("capsuleLibrary", []))
    return {
        "collective_root": str(collective_root),
        "repo_sources_path": str(config_path),
        "repo_registered": True,
        "repo_connected": repo_connected,
        "capsule_indexed": capsule_indexed,
        "commands_run": commands_run,
        "collective_status": collective_status(repo_root, runtime_root),
    }
