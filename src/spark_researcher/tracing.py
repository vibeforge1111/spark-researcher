from __future__ import annotations

import json
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from .paths import artifacts_root


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _token(size: int = 8) -> str:
    return secrets.token_hex(size)


def traces_root(runtime_root: Path) -> Path:
    return artifacts_root(runtime_root) / "traces"


def _index_path(runtime_root: Path) -> Path:
    return traces_root(runtime_root) / "index.jsonl"


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


@dataclass
class TraceRecorder:
    runtime_root: Path
    trace_id: str
    kind: str
    name: str
    parent_trace_id: str | None
    path: Path

    def write(self, event_type: str, **payload: Any) -> None:
        _append_jsonl(
            self.path,
            {
                "created_at": _now_iso(),
                "event_type": event_type,
                "trace_id": self.trace_id,
                "trace_kind": self.kind,
                "trace_name": self.name,
                "parent_trace_id": self.parent_trace_id,
                **payload,
            },
        )

    def start_span(
        self,
        name: str,
        *,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        span_id = _token()
        self.write(
            "span_start",
            span_id=span_id,
            parent_span_id=parent_span_id,
            span_name=name,
            attributes=attributes or {},
        )
        return span_id

    def event(
        self,
        name: str,
        *,
        span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.write(
            "event",
            span_id=span_id,
            event_name=name,
            attributes=attributes or {},
        )

    def end_span(
        self,
        span_id: str,
        *,
        status: str = "ok",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.write(
            "span_end",
            span_id=span_id,
            status=status,
            attributes=attributes or {},
        )

    @contextmanager
    def span(
        self,
        name: str,
        *,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        span_id = self.start_span(name, parent_span_id=parent_span_id, attributes=attributes)
        try:
            yield span_id
        except Exception as exc:
            self.event("exception", span_id=span_id, attributes={"error": str(exc)})
            self.end_span(span_id, status="error")
            raise
        else:
            self.end_span(span_id, status="ok")

    def finish(self, *, status: str = "ok", attributes: dict[str, Any] | None = None) -> None:
        self.write("trace_end", status=status, attributes=attributes or {})


def start_trace(
    runtime_root: Path,
    *,
    kind: str,
    name: str,
    parent_trace_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> TraceRecorder:
    root = traces_root(runtime_root)
    root.mkdir(parents=True, exist_ok=True)
    trace_id = _token(16)
    path = root / f"{trace_id}.jsonl"
    recorder = TraceRecorder(
        runtime_root=runtime_root,
        trace_id=trace_id,
        kind=kind,
        name=name,
        parent_trace_id=parent_trace_id,
        path=path,
    )
    recorder.write("trace_start", attributes=attributes or {})
    _append_jsonl(
        _index_path(runtime_root),
        {
            "created_at": _now_iso(),
            "trace_id": trace_id,
            "trace_kind": kind,
            "trace_name": name,
            "parent_trace_id": parent_trace_id,
            "path": str(path),
        },
    )
    return recorder


def trace_status(runtime_root: Path) -> dict[str, Any]:
    root = traces_root(runtime_root)
    index_path = _index_path(runtime_root)
    if not index_path.exists():
        return {"trace_count": 0, "traces_root": str(root), "recent": []}
    rows = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {"trace_count": len(rows), "traces_root": str(root), "recent": list(reversed(rows[-10:]))}
