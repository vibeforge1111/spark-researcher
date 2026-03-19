"""Vibe Vibe API — live boundary between the dashboard and the chip.

Run:
    python src/domain_chip_vibe_incubator/api.py

Serves on http://localhost:4177 by default (VIBE_API_PORT env override).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from .ops_loop import (
        append_log,
        default_runtime_root,
        load_state,
        ops_write_lock,
        promote_learning,
        read_log,
        refresh_ops_artifacts,
        save_state,
    )
    from .cli import score_venture_candidate
except ImportError:
    from ops_loop import (  # type: ignore[no-redef]
        append_log,
        default_runtime_root,
        load_state,
        ops_write_lock,
        promote_learning,
        read_log,
        refresh_ops_artifacts,
        save_state,
    )
    from cli import score_venture_candidate  # type: ignore[no-redef]

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import datetime as _dt

RUNTIME_ROOT = default_runtime_root()
ARTIFACTS = Path(RUNTIME_ROOT) / "artifacts" / "incubator_os"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _read_json(name: str) -> Any:
    path = ARTIFACTS / name
    if not path.exists():
        return {}
    return json.loads(path.read_text("utf-8"))


def _read_jsonl(name: str) -> list[dict[str, Any]]:
    path = ARTIFACTS / name
    if not path.exists():
        return []
    lines = path.read_text("utf-8").splitlines()
    out: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _venture(state: dict[str, Any], venture_id: str) -> dict[str, Any]:
    for item in state.get("ventures", []):
        if isinstance(item, dict) and str(item.get("venture_id") or "") == venture_id:
            return item
    raise KeyError(f"Unknown venture_id: {venture_id}")


def _batch(state: dict[str, Any], batch_id: str) -> dict[str, Any]:
    for item in state.get("batches", []):
        if isinstance(item, dict) and str(item.get("batch_id") or "") == batch_id:
            return item
    raise KeyError(f"Unknown batch_id: {batch_id}")


# ---------------------------------------------------------------------------
# snapshot builder (mirrors build-dashboard-data.mjs logic in Python)
# ---------------------------------------------------------------------------

def build_dashboard_snapshot() -> dict[str, Any]:
    """Build the same snapshot that the Node script generates, but live."""
    state = load_state(RUNTIME_ROOT)
    latest_tick = _read_json("latest_tick.json")
    queue_snapshot = _read_json("queue_snapshot.json")
    execution_snapshot = _read_json("execution_snapshot.json")
    customer_snapshot = _read_json("customer_gtm_snapshot.json")
    trust_snapshot = _read_json("trust_capital_snapshot.json")
    learning_snapshot = _read_json("portfolio_learning_snapshot.json")
    scout_snapshot = _read_json("scout_snapshot.json")
    venture_task_packets = _read_json("venture_task_packets.json")
    office_hours_packets = _read_json("office_hours_packets.json")
    decision_packets = _read_json("decision_packets.json")

    # ensure lists
    if not isinstance(venture_task_packets, list):
        venture_task_packets = venture_task_packets.get("packets", []) if isinstance(venture_task_packets, dict) else []
    if not isinstance(office_hours_packets, list):
        office_hours_packets = office_hours_packets.get("packets", []) if isinstance(office_hours_packets, dict) else []
    if not isinstance(decision_packets, list):
        decision_packets = decision_packets.get("packets", []) if isinstance(decision_packets, dict) else []

    execution_map = {v["venture_id"]: v for v in (execution_snapshot.get("ventures") or []) if isinstance(v, dict)}
    customer_map = {v["venture_id"]: v for v in (customer_snapshot.get("ventures") or []) if isinstance(v, dict)}
    trust_map = {v["venture_id"]: v for v in (trust_snapshot.get("ventures") or []) if isinstance(v, dict)}
    learning_map = {v["venture_id"]: v for v in (learning_snapshot.get("ventures") or []) if isinstance(v, dict)}
    task_map = {v["venture_id"]: v for v in venture_task_packets if isinstance(v, dict)}

    ventures = []
    for venture in state.get("ventures", []):
        vid = venture.get("venture_id", "")
        ventures.append({
            **venture,
            "execution": execution_map.get(vid),
            "customer": customer_map.get(vid),
            "trust": trust_map.get(vid),
            "learning": learning_map.get(vid),
            "taskPacket": task_map.get(vid),
        })

    program = state.get("program", {})
    metrics = latest_tick.get("metrics", {})

    return {
        "generatedAt": latest_tick.get("generated_at") or state.get("updated_at") or _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "product": {
            "name": "Vibe Vibe",
            "runtimeName": program.get("name", "Vibe Incubator"),
            "operatorMode": program.get("operator_mode", "solo_plus_agents"),
            "batchStyle": program.get("batch_style", "cohort"),
            "portfolioCap": program.get("active_portfolio_cap") or metrics.get("portfolio_cap", 0),
        },
        "latestTick": latest_tick,
        "queueSnapshot": queue_snapshot,
        "state": {
            "founders": state.get("founders", []),
            "queues": state.get("queues", {}),
            "batches": state.get("batches", []),
        },
        "scout": scout_snapshot,
        "officeHoursPackets": office_hours_packets,
        "decisionPackets": decision_packets,
        "executionSnapshot": execution_snapshot,
        "customerSnapshot": customer_snapshot,
        "trustSnapshot": trust_snapshot,
        "learningSnapshot": learning_snapshot,
        "ventures": ventures,
    }


# ---------------------------------------------------------------------------
# status endpoint (mirrors control_plane.py status)
# ---------------------------------------------------------------------------

def build_status() -> dict[str, Any]:
    state = load_state(RUNTIME_ROOT)
    refreshed = refresh_ops_artifacts(RUNTIME_ROOT)
    ventures = state.get("ventures", [])
    batches = state.get("batches", [])
    return {
        "active_ventures": len(ventures),
        "batches": len(batches),
        "pending_applications": len([a for a in state.get("applications", []) if isinstance(a, dict) and a.get("status") == "pending"]),
        "tick": refreshed.get("tick", {}),
        "batches_detail": refreshed.get("batches", []),
    }


# ---------------------------------------------------------------------------
# write actions
# ---------------------------------------------------------------------------

def action_admissions_review(body: dict[str, Any]) -> dict[str, Any]:
    application_id = body["application_id"]
    decision = body["decision"]
    note = body.get("note", "")

    with ops_write_lock(RUNTIME_ROOT):
        state = load_state(RUNTIME_ROOT)
        applications = state.setdefault("applications", [])
        app = None
        for item in applications:
            if isinstance(item, dict) and str(item.get("application_id") or "") == application_id:
                app = item
                break
        if app is None:
            raise KeyError(f"Unknown application_id: {application_id}")

        if decision == "invite":
            # graduate to venture
            vid = app.get("venture_id") or f"{_slug(app.get('label', 'venture'))}"
            venture_exists = any(
                isinstance(v, dict) and v.get("venture_id") == vid
                for v in state.get("ventures", [])
            )
            if not venture_exists:
                state.setdefault("ventures", []).append({
                    "venture_id": vid,
                    "label": app.get("label", vid),
                    "venture_model": app.get("venture_model", ""),
                    "customer_surface": app.get("customer_surface", ""),
                    "distribution_engine": app.get("distribution_engine", ""),
                    "build_stack": app.get("build_stack", "template_factory"),
                    "validation_motion": app.get("validation_motion", "paid_pilot"),
                    "trust_model": app.get("trust_model", "manual_review_first"),
                    "operating_cadence": app.get("operating_cadence", "daily_ship"),
                    "venture_theme": app.get("venture_theme", ""),
                    "stage": "proof",
                    "status": "active",
                    "automation_coverage": 0.5,
                    "weekly_revenue": 0,
                    "customer_conversations_this_week": 0,
                    "paid_signals_this_week": 0,
                    "active_users": 0,
                })
            app["status"] = "admitted"
            app["decision"] = "invite"
        elif decision == "waitlist":
            app["status"] = "waitlisted"
            app["decision"] = "waitlist"
        elif decision == "reject":
            app["status"] = "rejected"
            app["decision"] = "reject"
        else:
            raise ValueError(f"Invalid decision: {decision}")

        event = append_log(RUNTIME_ROOT, "admissions_reviews", {
            "application_id": application_id,
            "decision": decision,
            "note": note,
        })
        save_state(RUNTIME_ROOT, state)
        refreshed = refresh_ops_artifacts(RUNTIME_ROOT)

    return {"event": event, "tick": refreshed.get("tick", {})}


def action_build_request_update(body: dict[str, Any]) -> dict[str, Any]:
    venture_id = body["venture_id"]
    request_id = body["request_id"]
    status = body["status"]

    with ops_write_lock(RUNTIME_ROOT):
        state = load_state(RUNTIME_ROOT)
        _venture(state, venture_id)  # validate
        event = append_log(RUNTIME_ROOT, "build_requests", {
            "venture_id": venture_id,
            "request_id": request_id,
            "status": status,
            "title": body.get("title", ""),
            "kind": body.get("kind", "workflow"),
            "priority": body.get("priority", "medium"),
        })
        refreshed = refresh_ops_artifacts(RUNTIME_ROOT)

    return {"event": event, "tick": refreshed.get("tick", {})}


def action_weekly_update(body: dict[str, Any]) -> dict[str, Any]:
    venture_id = body["venture_id"]

    with ops_write_lock(RUNTIME_ROOT):
        state = load_state(RUNTIME_ROOT)
        venture = _venture(state, venture_id)
        venture["weekly_update_freshness_days"] = 0
        if body.get("stage"):
            venture["stage"] = body["stage"]
        event = append_log(RUNTIME_ROOT, "weekly_updates", {
            "venture_id": venture_id,
            "note": body.get("note", ""),
            "stage": body.get("stage", venture.get("stage", "")),
        })
        save_state(RUNTIME_ROOT, state)
        refreshed = refresh_ops_artifacts(RUNTIME_ROOT)

    return {"event": event, "tick": refreshed.get("tick", {})}


def action_kpi_snapshot(body: dict[str, Any]) -> dict[str, Any]:
    venture_id = body["venture_id"]

    with ops_write_lock(RUNTIME_ROOT):
        state = load_state(RUNTIME_ROOT)
        venture = _venture(state, venture_id)
        for key in ("customer_conversations", "paid_signals", "weekly_revenue",
                     "pipeline_count", "active_users", "automation_coverage"):
            if key in body:
                # map to state field names
                state_key = {
                    "customer_conversations": "customer_conversations_this_week",
                    "paid_signals": "paid_signals_this_week",
                    "pipeline_count": "open_pipeline_count",
                }.get(key, key)
                venture[state_key] = body[key]
        event = append_log(RUNTIME_ROOT, "kpi_snapshots", {
            "venture_id": venture_id,
            **{k: v for k, v in body.items() if k != "venture_id"},
        })
        save_state(RUNTIME_ROOT, state)
        refreshed = refresh_ops_artifacts(RUNTIME_ROOT)

    return {"event": event, "tick": refreshed.get("tick", {})}


# ---------------------------------------------------------------------------
# slug helper
# ---------------------------------------------------------------------------

def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return cleaned.strip("-")[:64] or "venture"


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

ROUTES: dict[str, dict[str, Any]] = {
    "GET": {
        "/api/health": lambda _q: {"status": "ok"},
        "/api/status": lambda _q: build_status(),
        "/api/dashboard": lambda _q: build_dashboard_snapshot(),
    },
    "POST": {
        "/api/admissions-review": action_admissions_review,
        "/api/build-request": action_build_request_update,
        "/api/weekly-update": action_weekly_update,
        "/api/kpi-snapshot": action_kpi_snapshot,
    },
}


class ApiHandler(BaseHTTPRequestHandler):
    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        handler = ROUTES.get("GET", {}).get(parsed.path)
        if handler is None:
            self._send_json(404, {"error": "not found"})
            return
        try:
            result = handler(parse_qs(parsed.query))
            self._send_json(200, result)
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        handler = ROUTES.get("POST", {}).get(parsed.path)
        if handler is None:
            self._send_json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw)
            result = handler(body)
            self._send_json(200, result)
        except (KeyError, ValueError) as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[vibe-api] {fmt % args}")


def main() -> None:
    port = int(os.environ.get("VIBE_API_PORT", "4177"))
    server = HTTPServer(("127.0.0.1", port), ApiHandler)
    print(f"[vibe-api] serving on http://127.0.0.1:{port}")
    print(f"[vibe-api] runtime_root = {RUNTIME_ROOT}")
    print(f"[vibe-api] endpoints:")
    for method, routes in ROUTES.items():
        for path in routes:
            print(f"  {method} {path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[vibe-api] shutting down")
        server.server_close()


if __name__ == "__main__":
    main()
