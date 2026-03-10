from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .paths import advisory_root


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def log_advisory_outcome(
    runtime_root: Path,
    *,
    task: str,
    model: str,
    status: str,
    packet_ids: list[str],
    score: float | None = None,
    notes: str = "",
    domain: str = "generic",
) -> dict[str, object]:
    root = advisory_root(runtime_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "outcomes.jsonl"
    payload = {
        "created_at": _now_iso(),
        "task": task,
        "model": model,
        "domain": domain,
        "status": status,
        "packet_ids": list(packet_ids),
        "score": score,
        "notes": notes,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return {"path": str(path), "recorded": True, "payload": payload}
