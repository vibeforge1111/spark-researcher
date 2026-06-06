from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

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


def load_advisory_outcomes(runtime_root: Path) -> list[dict[str, object]]:
    path = advisory_root(runtime_root) / "outcomes.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
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


def review_advisory_outcomes(runtime_root: Path) -> dict[str, object]:
    rows = load_advisory_outcomes(runtime_root)
    per_packet: dict[str, dict[str, object]] = {}
    for row in rows:
        packet_ids = [str(item) for item in row.get("packet_ids", [])]
        status = str(row.get("status", "mixed"))
        score = row.get("score")
        for packet_id in packet_ids:
            record = per_packet.setdefault(
                packet_id,
                {"packet_id": packet_id, "uses": 0, "ok": 0, "mixed": 0, "fail": 0, "scores": []},
            )
            record["uses"] = int(record["uses"]) + 1
            record[status] = int(record.get(status, 0)) + 1
            if isinstance(score, (int, float)):
                record["scores"].append(float(score))
    reviewed = []
    for packet_id, record in sorted(per_packet.items()):
        scores = list(record.pop("scores"))
        avg_score = round(mean(scores), 3) if scores else None
        ok = int(record["ok"])
        fail = int(record["fail"])
        if avg_score is not None and avg_score >= 0.75 and ok > fail:
            recommendation = "keep"
        elif avg_score is not None and avg_score < 0.45:
            recommendation = "drop"
        else:
            recommendation = "rewrite"
        reviewed.append({**record, "average_score": avg_score, "recommendation": recommendation})
    return {"outcome_count": len(rows), "packet_reviews": reviewed}
