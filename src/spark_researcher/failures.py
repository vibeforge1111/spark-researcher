from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .paths import artifacts_root


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def failures_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "failures"


def failures_path(runtime_root: Path) -> Path:
    return failures_root(runtime_root) / "registry.jsonl"


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def record_failure(
    runtime_root: Path,
    *,
    failure_type: str,
    summary: str,
    surface: str,
    domain: str = "generic",
    severity: str = "warn",
    novelty_key: str = "",
    evidence: list[str] | None = None,
    trace_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "created_at": _now_iso(),
        "failure_type": failure_type,
        "summary": summary.strip(),
        "surface": surface,
        "domain": domain or "generic",
        "severity": severity,
        "novelty_key": novelty_key.strip() or failure_type,
        "evidence": list(evidence or []),
        "trace_id": trace_id,
        "metadata": metadata or {},
    }
    _append_jsonl(failures_path(runtime_root), payload)
    return payload


def load_failures(runtime_root: Path) -> list[dict[str, Any]]:
    path = failures_path(runtime_root)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _parse_created_at(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def surprise_status(runtime_root: Path, *, limit: int = 10) -> dict[str, Any]:
    rows = load_failures(runtime_root)
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    now = datetime.now(UTC)
    for row in rows:
        domain = str(row.get("domain") or "generic")
        surface = str(row.get("surface") or "unknown")
        key = (domain, surface)
        group = grouped.setdefault(
            key,
            {
                "domain": domain,
                "surface": surface,
                "count": 0,
                "novelty_keys": set(),
                "latest_created_at": "",
                "severity_counts": {},
                "top_examples": [],
            },
        )
        group["count"] += 1
        novelty_key = str(row.get("novelty_key") or row.get("failure_type") or "failure")
        group["novelty_keys"].add(novelty_key)
        created_at = str(row.get("created_at") or "")
        if created_at > str(group["latest_created_at"]):
            group["latest_created_at"] = created_at
        severity = str(row.get("severity") or "warn")
        group["severity_counts"][severity] = int(group["severity_counts"].get(severity, 0)) + 1
        if len(group["top_examples"]) < 3:
            group["top_examples"].append(
                {
                    "failure_type": row.get("failure_type"),
                    "summary": row.get("summary"),
                    "created_at": created_at,
                    "trace_id": row.get("trace_id"),
                }
            )
    ranked = []
    total = max(len(rows), 1)
    for group in grouped.values():
        latest = _parse_created_at(str(group["latest_created_at"]))
        age_days = max((now - latest).total_seconds() / 86400.0, 0.0) if latest else 999.0
        recency_weight = 2.0 if age_days <= 1 else 1.5 if age_days <= 7 else 1.0
        novelty_weight = 1.0 + (0.25 * len(group["novelty_keys"]))
        error_rate = group["count"] / total
        surprise_score = round(error_rate * novelty_weight * recency_weight, 4)
        ranked.append(
            {
                "domain": group["domain"],
                "surface": group["surface"],
                "count": group["count"],
                "novelty_count": len(group["novelty_keys"]),
                "latest_created_at": group["latest_created_at"],
                "severity_counts": group["severity_counts"],
                "surprise_score": surprise_score,
                "top_examples": group["top_examples"],
            }
        )
    ranked.sort(key=lambda item: (-float(item["surprise_score"]), -int(item["count"]), str(item["domain"]), str(item["surface"])))
    return {"failure_count": len(rows), "priorities": ranked[:limit]}
