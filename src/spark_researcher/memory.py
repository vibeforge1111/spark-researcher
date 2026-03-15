from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .beliefs import build_beliefs
from .chips import chip_has_hook, invoke_chip_hook
from .paths import memory_root, self_edit_root
from .runner import read_jsonl
from .ruvector import run_search as run_ruvector_search
from .ruvector import ruvector_status


MAX_QUERY_LENGTH = 500
MAX_RESULTS_LIMIT = 20
MAX_DOCUMENT_STEM_LENGTH = 80


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _documents_root(runtime_root: Path) -> Path:
    return memory_root(runtime_root) / "documents"


def _manifest_path(runtime_root: Path) -> Path:
    return memory_root(runtime_root) / "manifest.json"


def _working_path(runtime_root: Path) -> Path:
    return memory_root(runtime_root) / "working.json"


def _episodes_path(runtime_root: Path) -> Path:
    return memory_root(runtime_root) / "episodes.jsonl"


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except PermissionError:
        # Windows/Obsidian can transiently hold generated docs open. Keep going;
        # later writes will refresh files that still exist.
        return


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    return slug.strip("-") or "item"


def _bounded_document_stem(value: str, *, limit: int = MAX_DOCUMENT_STEM_LENGTH) -> str:
    safe = _safe_slug(value)
    if len(safe) <= limit:
        return safe
    digest = hashlib.sha1(safe.encode("utf-8")).hexdigest()[:12]
    head_limit = max(1, limit - len(digest) - 1)
    head = safe[:head_limit].rstrip("-._") or "item"
    return f"{head}-{digest}"


def _trim_document_stem(value: str, *, limit: int) -> str:
    trimmed = value[: max(1, limit)].rstrip("-._")
    return trimmed or "item"


def _unique_document_path(docs_root: Path, stem: str, used_paths: set[str]) -> Path:
    base = _bounded_document_stem(stem)
    candidate = base
    index = 2
    path = docs_root / f"{candidate}.md"
    while str(path) in used_paths:
        suffix = f"-{index}"
        trimmed = _trim_document_stem(base, limit=MAX_DOCUMENT_STEM_LENGTH - len(suffix))
        candidate = f"{trimmed}{suffix}"
        path = docs_root / f"{candidate}.md"
        index += 1
    used_paths.add(str(path))
    return path


def _normalize_query(query: str) -> str:
    normalized = " ".join(query.split())
    if not normalized:
        raise RuntimeError("Search query must not be empty.")
    if len(normalized) > MAX_QUERY_LENGTH:
        raise RuntimeError(f"Search query is too long. Keep it under {MAX_QUERY_LENGTH} characters.")
    return normalized


def _normalize_limit(limit: int) -> int:
    if limit < 1:
        return 1
    return min(limit, MAX_RESULTS_LIMIT)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _local_manifest(runtime_root: Path, *, repo_root: Path, goal: str, config_path: Path | None) -> dict[str, Any]:
    manifest_path = _manifest_path(runtime_root)
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # A concurrent memory sync may briefly leave the manifest half-written.
            pass
    return sync_memory(repo_root, runtime_root, goal=goal, config_path=config_path)


def _kind_priority(kind: str) -> int:
    priorities = {
        "startup_research": 20,
        "startup_doctrine": 18,
        "startup_boundary": 16,
        "startup_benchmark": 14,
        "belief": 12,
        "self_edit": 8,
        "episode": 6,
        "outcome": 4,
        "run": 2,
        "working": 0,
    }
    return priorities.get(kind, 0)


def _tier_priority(tier: str) -> int:
    priorities = {
        "research_grounded": 28,
        "grounded_doctrine": 30,
        "grounded_boundary": 26,
        "benchmark_evidence": 22,
        "state_snapshot": 18,
        "belief": 16,
        "exploratory_frontier": 8,
        "raw_outcome": 4,
        "raw_run": 2,
    }
    return priorities.get(tier, 0)


def _default_memory_tier(kind: str) -> str:
    defaults = {
        "startup_research": "research_grounded",
        "startup_doctrine": "grounded_doctrine",
        "startup_boundary": "grounded_boundary",
        "startup_benchmark": "benchmark_evidence",
        "belief": "belief",
        "working": "state_snapshot",
        "episode": "state_snapshot",
        "outcome": "raw_outcome",
        "run": "raw_run",
        "startup_factor": "exploratory_frontier",
    }
    return defaults.get(kind, "raw_run")


def _infer_document_kind(path: Path) -> str:
    stem = path.stem
    if stem == "working-memory":
        return "working"
    if stem == "episode-memory":
        return "episode"
    if stem.startswith("run-"):
        return "run"
    if stem.startswith("outcome-"):
        return "outcome"
    if stem.startswith("belief-"):
        return "belief"
    if stem.startswith("self-edit-"):
        return "self_edit"
    if stem.startswith("startup_doctrine-"):
        return "startup_doctrine"
    if stem.startswith("startup_boundary-"):
        return "startup_boundary"
    if stem.startswith("startup_benchmark-"):
        return "startup_benchmark"
    if stem.startswith("startup_research-"):
        return "startup_research"
    if stem.startswith("startup_factor-"):
        return "startup_factor"
    return "unknown"


def _manifest_docs_by_path(runtime_root: Path, *, repo_root: Path, goal: str, config_path: Path | None) -> dict[str, dict[str, Any]]:
    manifest = _local_manifest(runtime_root, repo_root=repo_root, goal=goal, config_path=config_path)
    mapped: dict[str, dict[str, Any]] = {}
    for collection_name in ("chip_documents",):
        collection = manifest.get(collection_name, [])
        if isinstance(collection, list):
            for item in collection:
                if isinstance(item, dict) and item.get("path"):
                    mapped[str(item["path"])] = item
    docs_root = Path(str(manifest["documents_root"])) if manifest.get("documents_root") else None
    if docs_root is not None:
        for path in docs_root.glob("*.md"):
            mapped.setdefault(
                str(path),
                {
                    "path": str(path),
                    "kind": _infer_document_kind(path),
                    "title": path.stem,
                    "memory_tier": _default_memory_tier(_infer_document_kind(path)),
                },
            )
    return mapped


def _local_search_results(
    runtime_root: Path,
    docs_root: Path,
    query: str,
    *,
    limit: int,
    repo_root: Path,
    goal: str,
    config_path: Path | None,
) -> list[dict[str, Any]]:
    normalized_query = _normalize_query(query)
    terms = [term for term in normalized_query.lower().split() if term]
    docs_by_path = _manifest_docs_by_path(runtime_root, repo_root=repo_root, goal=goal, config_path=config_path)
    results = []
    for path in sorted(docs_root.glob("*.md")):
        try:
            text = _read_text(path)
        except FileNotFoundError:
            # Memory sync rewrites docs in place; skip files that disappeared mid-search.
            continue
        lowered = text.lower()
        lexical_score = sum(1 for term in terms if term in lowered)
        if lexical_score <= 0:
            continue
        doc_meta = docs_by_path.get(str(path), {})
        kind = str(doc_meta.get("kind") or "unknown")
        memory_tier = str(doc_meta.get("memory_tier") or _default_memory_tier(kind))
        title = str(doc_meta.get("title") or (text.splitlines()[0].lstrip("# ").strip() if text else path.stem))
        title_lower = title.lower()
        title_bonus = sum(4 for term in terms if term in title_lower)
        phrase_bonus = 6 if normalized_query.lower() in lowered else 0
        score = lexical_score + title_bonus + phrase_bonus + _kind_priority(kind) + _tier_priority(memory_tier)
        results.append(
            {
                "backend": "local",
                "path": str(path),
                "title": title,
                "kind": kind,
                "memory_tier": memory_tier,
                "score": score,
                "snippet": _build_snippet(text, normalized_query),
            }
        )
    results.sort(
        key=lambda item: (
            -int(item["score"]),
            -_tier_priority(str(item.get("memory_tier") or "raw_run")),
            -_kind_priority(str(item.get("kind") or "unknown")),
            str(item["path"]),
        )
    )
    return results[: _normalize_limit(limit)]


def _build_snippet(text: str, query: str, *, width: int = 180) -> str:
    lowered = text.lower()
    query_lower = query.lower()
    index = lowered.find(query_lower)
    if index < 0:
        return text[:width].replace("\n", " ").strip()
    start = max(0, index - width // 3)
    end = min(len(text), index + len(query) + width // 2)
    return text[start:end].replace("\n", " ").strip()


def build_run_doc(record: dict[str, Any]) -> str:
    title = record.get("candidate_id") or record.get("run_id")
    mutations = record.get("applied_mutations") or []
    mutation_lines = [f"- `{item['name']}` -> `{item['value']}`" for item in mutations] or ["- none"]
    return "\n".join(
        [
            f"# Run Memory {title}",
            "",
            f"- run_id: `{record.get('run_id')}`",
            f"- project: `{record.get('project_name')}`",
            f"- command: `{record.get('command_name')}`",
            f"- verdict: `{record.get('verdict')}`",
            f"- metric: `{record.get('metric_name')}` = `{record.get('metric_value')}`",
            f"- baseline: `{record.get('baseline_value')}`",
            f"- trace_id: `{record.get('trace_id')}`",
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
            f"- trace: `{record.get('trace_path')}`",
        ]
    )


def build_outcome_doc(outcome: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Outcome {outcome['title']}",
            "",
            f"- outcome_id: `{outcome['outcome_id']}`",
            f"- command: `{outcome['command_name']}`",
            f"- candidate: `{outcome['candidate_id']}`",
            f"- run_count: `{outcome['run_count']}`",
            f"- improved_runs: `{outcome['improved_runs']}`",
            f"- latest_verdict: `{outcome['latest_verdict']}`",
            f"- best_metric: `{outcome['best_metric']}`",
            f"- latest_metric: `{outcome['latest_metric']}`",
            "",
            "## Runs",
            "",
            *[f"- `{run_id}`" for run_id in outcome["run_ids"]],
        ]
    )


def build_self_edit_doc(proposal: dict[str, Any], review: dict[str, Any] | None) -> str:
    lines = [
        f"# Self Edit {proposal.get('proposal_id')}",
        "",
        f"- proposal_id: `{proposal.get('proposal_id')}`",
        f"- status: `{proposal.get('status')}`",
        f"- change_count: `{proposal.get('change_count')}`",
        f"- blocked_changes: `{len(proposal.get('blocked_changes', []))}`",
        f"- trace_id: `{proposal.get('trace_id')}`",
        "",
        "## Prompt",
        "",
        str(proposal.get("prompt") or "n/a"),
        "",
    ]
    if review:
        lines.extend(
            [
                "## Review",
                "",
                f"- decision: `{review.get('decision')}`",
                f"- root_lesson: {review.get('root_lesson') or 'n/a'}",
                f"- counterfactual: {review.get('counterfactual') or 'n/a'}",
                f"- rollback_condition: {review.get('rollback_condition') or 'n/a'}",
                f"- trace_id: `{review.get('trace_id')}`",
                "",
                "## Lineage Failures",
                "",
                *[f"- {item}" for item in review.get("lineage_failures", [])],
                "",
            ]
        )
    return "\n".join(lines)


def build_working_memory_doc(payload: dict[str, Any]) -> str:
    lines = [
        "# Working Memory",
        "",
        f"- updated_at: `{payload.get('updated_at', 'n/a')}`",
        f"- kind: `{payload.get('kind', 'n/a')}`",
        f"- status: `{payload.get('status', 'n/a')}`",
        f"- trace_id: `{payload.get('trace_id', 'n/a')}`",
        "",
        "## Focus",
        "",
        str(payload.get("focus") or "No active focus recorded."),
        "",
    ]
    notes = [str(item) for item in payload.get("notes", []) if str(item).strip()]
    if notes:
        lines.extend(["## Notes", "", *[f"- {item}" for item in notes], ""])
    questions = [str(item) for item in payload.get("questions", []) if str(item).strip()]
    if questions:
        lines.extend(["## Open Questions", "", *[f"- {item}" for item in questions], ""])
    return "\n".join(lines)


def build_episode_memory_doc(rows: list[dict[str, Any]]) -> str:
    lines = ["# Episode Memory", ""]
    if not rows:
        lines.append("No episodes yet.")
        return "\n".join(lines)
    for row in rows:
        lines.extend(
            [
                f"## {row.get('title', row.get('kind', 'episode'))}",
                "",
                f"- created_at: `{row.get('created_at', 'n/a')}`",
                f"- kind: `{row.get('kind', 'n/a')}`",
                f"- status: `{row.get('status', 'n/a')}`",
                f"- trace_id: `{row.get('trace_id', 'n/a')}`",
                "",
                str(row.get("summary") or "n/a"),
                "",
            ]
        )
    return "\n".join(lines)


def write_working_memory(
    runtime_root: Path,
    *,
    kind: str,
    focus: str,
    status: str,
    trace_id: str | None = None,
    notes: list[str] | None = None,
    questions: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "updated_at": _now_iso(),
        "kind": kind,
        "focus": focus.strip(),
        "status": status.strip(),
        "trace_id": trace_id,
        "notes": [str(item).strip() for item in list(notes or []) if str(item).strip()],
        "questions": [str(item).strip() for item in list(questions or []) if str(item).strip()],
    }
    path = _working_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def load_working_memory(runtime_root: Path) -> dict[str, Any]:
    path = _working_path(runtime_root)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def record_episode(
    runtime_root: Path,
    *,
    kind: str,
    title: str,
    summary: str,
    status: str,
    trace_id: str | None = None,
) -> dict[str, Any]:
    payload = {
        "created_at": _now_iso(),
        "kind": kind,
        "title": title.strip(),
        "summary": summary.strip(),
        "status": status.strip(),
        "trace_id": trace_id,
    }
    _append_jsonl(_episodes_path(runtime_root), payload)
    return payload


def load_episode_memory(runtime_root: Path, *, limit: int = 12) -> list[dict[str, Any]]:
    path = _episodes_path(runtime_root)
    if not path.exists():
        return []
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return list(reversed(rows[-limit:]))


def _is_better(candidate: float, current: float | None, goal: str) -> bool:
    if current is None:
        return True
    return candidate > current if goal == "maximize" else candidate < current


def _build_outcomes(rows: list[dict[str, Any]], *, goal: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        command_name = str(row.get("command_name") or "command")
        candidate_id = str(row.get("candidate_id") or "baseline")
        key = f"{command_name}|{candidate_id}"
        group = grouped.setdefault(
            key,
            {
                "outcome_id": f"outcome-{_safe_slug(command_name)}-{_safe_slug(candidate_id)}",
                "title": f"{command_name} / {candidate_id}",
                "command_name": command_name,
                "candidate_id": candidate_id,
                "run_count": 0,
                "improved_runs": 0,
                "latest_verdict": "unknown",
                "latest_metric": None,
                "best_metric": None,
                "run_ids": [],
            },
        )
        group["run_count"] += 1
        if row.get("verdict") == "improved":
            group["improved_runs"] += 1
        group["latest_verdict"] = row.get("verdict")
        group["latest_metric"] = row.get("metric_value")
        group["run_ids"].append(str(row.get("run_id")))
        metric_value = row.get("metric_value")
        if isinstance(metric_value, (int, float)) and _is_better(float(metric_value), group["best_metric"], goal):
            group["best_metric"] = float(metric_value)
    return sorted(grouped.values(), key=lambda item: (str(item["command_name"]), str(item["candidate_id"])))


def sync_memory(repo_root: Path, runtime_root: Path, *, goal: str = "minimize", config_path: Path | None = None) -> dict[str, Any]:
    rows = read_jsonl(runtime_root / "artifacts" / "ledger" / "runs.jsonl")
    docs_root = _documents_root(runtime_root)
    docs_root.mkdir(parents=True, exist_ok=True)
    for path in docs_root.glob("*"):
        if path.is_file():
            _safe_unlink(path)
    build_beliefs(repo_root, runtime_root)
    written: list[dict[str, str]] = []
    kind_counts: dict[str, int] = defaultdict(int)
    tier_counts: dict[str, int] = defaultdict(int)
    used_paths: set[str] = set()

    for record in rows:
        path = _unique_document_path(docs_root, f"run-{record.get('run_id', 'run')}", used_paths)
        write_text(path, build_run_doc(record))
        memory_tier = "raw_run"
        written.append({"path": str(path), "kind": "run", "title": str(record.get("run_id") or path.stem), "memory_tier": memory_tier})
        kind_counts["run"] += 1
        tier_counts[memory_tier] += 1

    beliefs_root = repo_root / "docs" / "beliefs"
    if beliefs_root.exists():
        for path in sorted(beliefs_root.glob("*.md")):
            if path.name.upper() == "INDEX.MD":
                continue
            target = _unique_document_path(docs_root, f"belief-{path.stem}", used_paths)
            shutil.copyfile(path, target)
            written.append({"path": str(target), "kind": "belief", "title": path.stem, "memory_tier": "belief"})
            kind_counts["belief"] += 1
            tier_counts["belief"] += 1

    self_edit_docs = []
    proposals_root = self_edit_root(runtime_root)
    if proposals_root.exists():
        for proposal_path in sorted(proposals_root.glob("*/proposal.json")):
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            review_path = proposal_path.parent / "review.json"
            review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else None
            target = _unique_document_path(docs_root, f"self-edit-{proposal.get('proposal_id')}", used_paths)
            write_text(target, build_self_edit_doc(proposal, review))
            written.append({"path": str(target), "kind": "self_edit", "title": str(proposal.get("proposal_id")), "memory_tier": "raw_outcome"})
            kind_counts["self_edit"] += 1
            tier_counts["raw_outcome"] += 1
            self_edit_docs.append(str(target))

    working = load_working_memory(runtime_root)
    if working:
        target = docs_root / "working-memory.md"
        used_paths.add(str(target))
        write_text(target, build_working_memory_doc(working))
        working_tier = "state_snapshot"
        written.append({"path": str(target), "kind": "working", "title": "Working Memory", "memory_tier": working_tier})
        kind_counts["working"] += 1
        tier_counts[working_tier] += 1

    episodes = load_episode_memory(runtime_root)
    if episodes:
        target = docs_root / "episode-memory.md"
        used_paths.add(str(target))
        write_text(target, build_episode_memory_doc(episodes))
        written.append({"path": str(target), "kind": "episode", "title": "Episode Memory", "memory_tier": "state_snapshot"})
        kind_counts["episode"] += 1
        tier_counts["state_snapshot"] += 1

    outcomes = _build_outcomes(rows, goal=goal)
    for outcome in outcomes:
        path = _unique_document_path(docs_root, outcome["outcome_id"], used_paths)
        write_text(path, build_outcome_doc(outcome))
        written.append({"path": str(path), "kind": "outcome", "title": outcome["title"], "memory_tier": "raw_outcome"})
        kind_counts["outcome"] += 1
        tier_counts["raw_outcome"] += 1

    chip_documents: list[dict[str, str]] = []
    if config_path is not None and chip_has_hook(config_path, "packets"):
        packet = invoke_chip_hook(
            config_path,
            "packets",
            {
                "project_name": repo_root.name,
                "ledger_rows": rows,
                "outcomes": outcomes,
                "documents_root": str(docs_root),
            },
        )
        seen_chip_documents: set[tuple[str, str, str, str]] = set()
        for item in packet.get("documents", []):
            title = str(item.get("title") or "Chip Document")
            kind = str(item.get("kind") or "chip")
            slug = _safe_slug(str(item.get("slug") or title))
            memory_tier = str(item.get("memory_tier") or _default_memory_tier(kind))
            content = str(item.get("content") or "")
            signature = (kind, title, content, memory_tier)
            if signature in seen_chip_documents:
                continue
            seen_chip_documents.add(signature)
            path = _unique_document_path(docs_root, f"{kind}-{slug}", used_paths)
            write_text(path, content)
            record = {"path": str(path), "kind": kind, "title": title, "memory_tier": memory_tier}
            written.append(record)
            chip_documents.append(record)
            kind_counts[kind] += 1
            tier_counts[memory_tier] += 1

    index_lines = [
        "# Memory Index",
        "",
        f"- documents_root: `{docs_root}`",
        f"- total_documents: `{len(written)}`",
        "",
        "## Kinds",
        "",
        *[f"- {kind}: `{count}`" for kind, count in sorted(kind_counts.items())],
        "",
        "## Memory Tiers",
        "",
        *[f"- {tier}: `{count}`" for tier, count in sorted(tier_counts.items())],
        "",
        "## Outcomes",
        "",
    ]
    index_lines.extend(f"- [[{item['outcome_id']}]]" for item in outcomes)
    write_text(docs_root / "INDEX.md", "\n".join(index_lines))
    manifest = {
        "backend": "local",
        "document_count": len(written),
        "documents_root": str(docs_root),
        "source_runs": len(rows),
        "kinds": dict(kind_counts),
        "memory_tiers": dict(tier_counts),
        "outcomes": outcomes,
        "self_edit_documents": self_edit_docs,
        "chip_documents": chip_documents,
        "working_memory": working,
        "episode_count": len(episodes),
    }
    write_text(_manifest_path(runtime_root), json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def search_memory(
    repo_root: Path,
    runtime_root: Path,
    query: str,
    *,
    limit: int = 5,
    backend: str = "local",
    goal: str = "minimize",
    config_path: Path | None = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    sync_memory(repo_root, runtime_root, goal=goal, config_path=config_path)
    docs_root = _documents_root(runtime_root)
    local_results = _local_search_results(
        runtime_root,
        docs_root,
        query,
        limit=limit,
        repo_root=repo_root,
        goal=goal,
        config_path=config_path,
    )
    if backend != "ruvector":
        return local_results
    status = ruvector_status()
    if str(status.get("status")) == "available":
        return run_ruvector_search(query)
    return {
        "backend": "ruvector",
        "active_backend": "local",
        "fallback_reason": status.get("status"),
        "ruvector_status": status,
        "results": local_results,
        "notes": [
            "RuVector is configured as the default retrieval backend.",
            "Spark fell back to local memory search because RuVector is not fully ready in this shell.",
        ],
    }


def memory_status(
    repo_root: Path,
    runtime_root: Path,
    *,
    backend: str = "local",
    configured_backend: str = "local",
    goal: str = "minimize",
    config_path: Path | None = None,
) -> dict[str, Any]:
    manifest_path = _manifest_path(runtime_root)
    manifest = _local_manifest(runtime_root, repo_root=repo_root, goal=goal, config_path=config_path)
    if backend == "ruvector":
        status = ruvector_status()
        status["configured_backend"] = configured_backend
        status["local_documents_root"] = manifest["documents_root"]
        status["local_document_count"] = manifest["document_count"]
        status["local_kinds"] = manifest.get("kinds", {})
        status["local_storage_backend"] = "local"
        status["default_role"] = "retrieval"
        return status
    return {
        "backend": "local",
        "configured_backend": configured_backend,
        "documents_root": manifest["documents_root"],
        "document_count": manifest["document_count"],
        "kinds": manifest.get("kinds", {}),
        "manifest_present": manifest_path.exists(),
        "notes": [
            "Local memory remains Spark's canonical storage layer.",
            "Search runs over exported Markdown memory documents.",
        ],
    }
