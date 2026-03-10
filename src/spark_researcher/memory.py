from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import ledger_path, memory_root


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def build_run_doc(record: dict[str, Any]) -> str:
    title = record.get("candidate_id") or record.get("run_id")
    mutations = record.get("applied_mutations") or []
    mutation_lines = [f"- `{item['name']}` -> `{item['value']}`" for item in mutations] or ["- none"]
    return "\n".join(
        [
            f"# {title}",
            "",
            f"- run_id: `{record.get('run_id')}`",
            f"- project: `{record.get('project_name')}`",
            f"- command: `{record.get('command_name')}`",
            f"- verdict: `{record.get('verdict')}`",
            f"- metric: `{record.get('metric_name')}` = `{record.get('metric_value')}`",
            f"- baseline: `{record.get('baseline_value')}`",
            "",
            "## Hypothesis",
            "",
            str(record.get("hypothesis") or "n/a"),
            "",
            "## Mutations",
            "",
            *mutation_lines,
            "",
            "## Notes",
            "",
            str(record.get("candidate_summary") or "n/a"),
            "",
            "## Paths",
            "",
            f"- log: `{record.get('log_path')}`",
            f"- run_dir: `{record.get('run_dir')}`",
        ]
    )


def sync_memory(runtime_root: Path) -> dict[str, Any]:
    rows = read_jsonl(ledger_path(runtime_root))
    docs_root = memory_root(runtime_root) / "documents"
    docs_root.mkdir(parents=True, exist_ok=True)
    written = []
    for record in rows:
        path = docs_root / f"{record.get('run_id', 'run')}.md"
        write_text(path, build_run_doc(record))
        written.append(str(path))
    manifest = {
        "document_count": len(written),
        "documents_root": str(docs_root),
        "source_runs": len(rows),
    }
    write_text(memory_root(runtime_root) / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def search_memory(runtime_root: Path, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    sync_memory(runtime_root)
    docs_root = memory_root(runtime_root) / "documents"
    terms = [term for term in query.lower().split() if term]
    results = []
    for path in sorted(docs_root.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
        score = sum(lowered.count(term) for term in terms)
        if score <= 0:
            continue
        first_line = text.splitlines()[0].lstrip("# ").strip() if text else path.stem
        results.append({"path": str(path), "title": first_line, "score": score, "snippet": text[:180].replace("\n", " ")})
    results.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
    return results[:limit]


def memory_status(runtime_root: Path) -> dict[str, Any]:
    docs_root = memory_root(runtime_root) / "documents"
    manifest_path = memory_root(runtime_root) / "manifest.json"
    return {
        "backend": "markdown-local",
        "documents_root": str(docs_root),
        "document_count": len(list(docs_root.glob("*.md"))) if docs_root.exists() else 0,
        "manifest_present": manifest_path.exists(),
    }
