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
        return {"trace_count": 0, "traces_root": str(root), "recent": [], "research_signals": {"research_retry_count": 0, "research_escalation_count": 0, "citation_check_count": 0, "citation_mismatch_count": 0, "verifier_selection_count": 0, "packet_selection_count": 0, "recent": []}}
    rows = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    research_retry_count = 0
    research_escalation_count = 0
    citation_check_count = 0
    citation_mismatch_count = 0
    verifier_selection_count = 0
    packet_selection_count = 0
    recent_signals: list[dict[str, Any]] = []
    for row in rows:
        trace_kind = str(row.get("trace_kind") or "")
        if trace_kind == "advisory_research":
            research_retry_count += 1
        path_value = row.get("path")
        if not isinstance(path_value, str):
            continue
        path = Path(path_value)
        if not path.exists():
            continue
        events = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        for event in events:
            if event.get("event_type") != "event":
                continue
            event_name = str(event.get("event_name") or "")
            attributes = event.get("attributes", {})
            if not isinstance(attributes, dict):
                attributes = {}
            if event_name == "research_escalation":
                research_escalation_count += 1
                recent_signals.append(
                    {
                        "created_at": event.get("created_at"),
                        "trace_id": event.get("trace_id"),
                        "signal": "research_escalation",
                        "research_query": attributes.get("research_query"),
                        "implicated_failure_surface": attributes.get("implicated_failure_surface"),
                    }
                )
            if event_name == "citation_check":
                citation_check_count += 1
                used_note_ids = [str(item) for item in attributes.get("used_note_ids", []) if str(item).strip()]
                relevant_note_ids = [str(item) for item in attributes.get("relevant_note_ids", []) if str(item).strip()]
                mismatch = bool(relevant_note_ids) and not any(item in relevant_note_ids for item in used_note_ids)
                if mismatch:
                    citation_mismatch_count += 1
                recent_signals.append(
                    {
                        "created_at": event.get("created_at"),
                        "trace_id": event.get("trace_id"),
                        "signal": "citation_check",
                        "used_note_ids": used_note_ids,
                        "relevant_note_ids": relevant_note_ids,
                        "mismatch": mismatch,
                    }
                )
            if event_name == "research_sources":
                sources = []
                for item in attributes.get("sources", [])[:3]:
                    if not isinstance(item, dict):
                        continue
                    sources.append(
                        {
                            "note_id": str(item.get("note_id") or "").strip(),
                            "title": str(item.get("title") or "").strip(),
                            "domain": str(item.get("domain") or "").strip(),
                            "url": str(item.get("url") or "").strip(),
                        }
                    )
                recent_signals.append(
                    {
                        "created_at": event.get("created_at"),
                        "trace_id": event.get("trace_id"),
                        "signal": "research_sources",
                        "research_query": attributes.get("research_query"),
                        "result_count": attributes.get("result_count"),
                        "sources": sources,
                    }
                )
            if event_name == "selected_candidate":
                verifier_selection_count += 1
                recent_signals.append(
                    {
                        "created_at": event.get("created_at"),
                        "trace_id": event.get("trace_id"),
                        "signal": "verifier_selection",
                        "selected": str(attributes.get("selected") or "").strip(),
                        "decision": str(attributes.get("decision") or "").strip(),
                        "issue_count": attributes.get("issue_count"),
                        "top_issue": str(attributes.get("top_issue") or "").strip(),
                        "best_next_question": str(attributes.get("best_next_question") or "").strip(),
                        "implicated_failure_surface": str(attributes.get("implicated_failure_surface") or "").strip(),
                    }
                )
            if event_name == "packet_selection":
                packet_selection_count += 1
                recent_signals.append(
                    {
                        "created_at": event.get("created_at"),
                        "trace_id": event.get("trace_id"),
                        "signal": "packet_selection",
                        "selected_packet_ids": [str(item) for item in attributes.get("selected_packet_ids", []) if str(item).strip()],
                        "packet_stability": str(attributes.get("packet_stability") or "").strip(),
                        "durable_belief_count": attributes.get("durable_belief_count", 0),
                        "provisional_belief_count": attributes.get("provisional_belief_count", 0),
                        "contradiction_count": attributes.get("contradiction_count", 0),
                    }
                )
    return {
        "trace_count": len(rows),
        "traces_root": str(root),
        "recent": list(reversed(rows[-10:])),
        "research_signals": {
            "research_retry_count": research_retry_count,
            "research_escalation_count": research_escalation_count,
            "citation_check_count": citation_check_count,
            "citation_mismatch_count": citation_mismatch_count,
            "verifier_selection_count": verifier_selection_count,
            "packet_selection_count": packet_selection_count,
            "recent": list(reversed(recent_signals[-10:])),
        },
    }
