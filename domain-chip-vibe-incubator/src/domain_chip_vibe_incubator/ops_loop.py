from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_POLICY = {
    "portfolio_cap": "3",
    "review_cadence": "weekly",
    "admissions_mode": "thesis_gate",
    "build_routing": "template_first",
    "validation_pressure": "paid_every_week",
    "trust_gate": "balanced",
    "capital_mode": "after_validation",
    "knowledge_capture": "every_review",
    "founder_update_sla": "48h",
}

POLICY_BONUSES = {
    "portfolio_cap": {"2": {"focus": 0.18, "knowledge": 0.06}, "3": {"focus": 0.14, "knowledge": 0.08}, "5": {"focus": 0.03, "knowledge": 0.11}},
    "review_cadence": {"daily": {"review": 0.15, "trust": 0.06}, "weekly": {"review": 0.11, "focus": 0.03}, "twice_weekly": {"review": 0.13, "trust": 0.04}},
    "admissions_mode": {"manual_gate": {"focus": 0.10, "trust": 0.05}, "thesis_gate": {"focus": 0.12, "validation": 0.03}, "warm_referral_only": {"trust": 0.08, "validation": -0.02}},
    "build_routing": {"template_first": {"automation": 0.12, "knowledge": 0.08}, "agent_workflows": {"automation": 0.10, "validation": 0.03}, "custom_build_heavy": {"automation": -0.03, "focus": -0.04}},
    "validation_pressure": {"paid_every_week": {"validation": 0.14, "focus": 0.04}, "design_partner_first": {"validation": 0.10, "trust": 0.03}, "dogfood_bias": {"knowledge": 0.08, "validation": -0.05}},
    "trust_gate": {"strict": {"trust": 0.14, "focus": -0.02}, "balanced": {"trust": 0.10}, "light": {"trust": -0.08, "automation": 0.02}},
    "capital_mode": {"after_validation": {"focus": 0.08, "trust": 0.03}, "parallel_scouting": {"validation": -0.02, "focus": -0.07}, "off": {"focus": 0.06}},
    "knowledge_capture": {"every_review": {"knowledge": 0.14}, "weekly_summary": {"knowledge": 0.09}, "ad_hoc": {"knowledge": -0.06}},
    "founder_update_sla": {"24h": {"review": 0.09}, "48h": {"review": 0.06}, "72h": {"review": -0.03}},
}


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _clamp(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


def _root(runtime_root: str) -> Path:
    return Path(runtime_root) / "artifacts" / "incubator_os"


def _path(runtime_root: str, name: str) -> Path:
    return _root(runtime_root) / name


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return cleaned.strip("-")[:64] or "item"


def _signature(mutations: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), str(value)) for key, value in mutations.items()))


def _mean(values: list[float], default: float = 0.0) -> float:
    return sum(values) / len(values) if values else default


def _num(value: Any, default: float) -> float:
    """Safe numeric coercion that treats 0 as a valid value (not falsy)."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _trust_score(status: str) -> float:
    return {"green": 0.92, "amber": 0.65, "red": 0.28}.get(status, 0.45)


def default_runtime_root() -> str:
    return str(Path(__file__).resolve().parents[2])


def state_path(runtime_root: str) -> Path:
    return _path(runtime_root, "state.json")


def log_path(runtime_root: str, name: str) -> Path:
    return _path(runtime_root, f"{name}.jsonl")


@contextmanager
def ops_write_lock(runtime_root: str, timeout_seconds: float = 10.0, poll_seconds: float = 0.05):
    path = _path(runtime_root, ".write.lock")
    deadline = time.monotonic() + timeout_seconds
    fd: int | None = None
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, f"{os.getpid()} {_now_iso()}".encode("utf-8"))
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Timed out waiting for incubator ops lock: {path}")
            time.sleep(poll_seconds)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _normalize_state(state: dict[str, Any]) -> dict[str, Any]:
    ventures = [item for item in state.get("ventures", []) if isinstance(item, dict)]
    deduped_ventures: list[dict[str, Any]] = []
    seen_ventures: set[str] = set()
    for item in ventures:
        venture_id = str(item.get("venture_id") or "").strip()
        if not venture_id or venture_id in seen_ventures:
            continue
        seen_ventures.add(venture_id)
        deduped_ventures.append(item)
    state["ventures"] = deduped_ventures
    founders = [item for item in state.get("founders", []) if isinstance(item, dict)]
    for founder in founders:
        venture_ids = []
        for venture_id in founder.get("venture_ids", []):
            text = str(venture_id).strip()
            if text and text in seen_ventures and text not in venture_ids:
                venture_ids.append(text)
        founder["venture_ids"] = venture_ids
    state["founders"] = founders
    # Normalize batches
    batches = [item for item in state.get("batches", []) if isinstance(item, dict)]
    deduped_batches: list[dict[str, Any]] = []
    seen_batches: set[str] = set()
    for item in batches:
        batch_id = str(item.get("batch_id") or "").strip()
        if not batch_id or batch_id in seen_batches:
            continue
        seen_batches.add(batch_id)
        item["venture_ids"] = [vid for vid in item.get("venture_ids", []) if vid in seen_ventures]
        deduped_batches.append(item)
    state["batches"] = deduped_batches
    return state


def _bootstrap_state(runtime_root: str) -> dict[str, Any]:
    rows = [
        row
        for row in _read_jsonl(Path(runtime_root) / "artifacts" / "ledger" / "runs.jsonl")
        if row.get("command_name") == "research" and isinstance(row.get("metric_value"), (int, float))
    ]
    rows.sort(key=lambda row: float(row.get("metric_value", 0.0) or 0.0), reverse=True)
    seeded: list[dict[str, Any]] = []
    for row in rows[:3]:
        candidate_id = str(row.get("candidate_id") or "venture")
        result = row.get("chip_result", {}) if isinstance(row.get("chip_result"), dict) else {}
        mutations = {
            str(item.get("name")): str(item.get("value"))
            for item in row.get("applied_mutations", [])
            if isinstance(item, dict) and item.get("name")
        }
        seeded.append(
            {
                "venture_id": candidate_id,
                "label": str(result.get("label") or candidate_id),
                "status": "active",
                "stage": "validation",
                "bottleneck": str(result.get("bottleneck") or "distribution_gap"),
                "weekly_update_freshness_days": 2,
                "last_review_days": 3,
                "automation_coverage": float(result.get("automation_leverage_score", 0.55) or 0.55),
                "reuse_assets_count": 3,
                "customer_conversations_this_week": 2,
                "paid_signals_this_week": 1 if float(result.get("revenue_readiness_score", 0.0) or 0.0) >= 0.6 else 0,
                "trust_review_status": "green" if float(result.get("resilience_score", 0.0) or 0.0) >= 0.62 else "amber",
                "founder_update_latency_hours": 18,
                "build_backlog_count": 4,
                "decision_status": "continue",
                "venture_model": mutations.get("venture_model", ""),
                "customer_surface": mutations.get("customer_surface", ""),
                "distribution_engine": mutations.get("distribution_engine", ""),
            }
        )
    if not seeded:
        seeded = [
            {
                "venture_id": "founder-backoffice-studio",
                "label": "Founder backoffice command center",
                "status": "active",
                "stage": "validation",
                "bottleneck": "distribution_gap",
                "weekly_update_freshness_days": 2,
                "last_review_days": 3,
                "automation_coverage": 0.64,
                "reuse_assets_count": 4,
                "customer_conversations_this_week": 2,
                "paid_signals_this_week": 1,
                "trust_review_status": "green",
                "founder_update_latency_hours": 12,
                "build_backlog_count": 5,
                "decision_status": "continue",
                "venture_model": "agentic_saas",
                "customer_surface": "founder_backoffice",
                "distribution_engine": "operator_content",
            },
            {
                "venture_id": "internal-os-spinout",
                "label": "Incubator operating system",
                "status": "active",
                "stage": "qualification",
                "bottleneck": "revenue_gap",
                "weekly_update_freshness_days": 3,
                "last_review_days": 4,
                "automation_coverage": 0.68,
                "reuse_assets_count": 5,
                "customer_conversations_this_week": 1,
                "paid_signals_this_week": 0,
                "trust_review_status": "green",
                "founder_update_latency_hours": 20,
                "build_backlog_count": 6,
                "decision_status": "continue",
                "venture_model": "internal_tool_spinout",
                "customer_surface": "founder_backoffice",
                "distribution_engine": "portfolio_crosssell",
            },
        ]
    return {
        "generated_at": _now_iso(),
        "program": {
            "name": "Vibe Incubator",
            "operator_mode": "solo_plus_agents",
            "batch_style": "cohort",
            "active_portfolio_cap": 3,
        },
        "founders": [
            {
                "founder_id": "owner",
                "label": "Primary operator",
                "status": "active",
                "venture_ids": [item["venture_id"] for item in seeded],
                "response_latency_hours": 14,
            }
        ],
        "ventures": seeded,
        "queues": {
            "admissions": [{"venture_id": "agency-ops-rollup", "priority": "medium"}],
            "office_hours": [{"venture_id": item["venture_id"], "priority": "high"} for item in seeded],
            "build": [{"venture_id": item["venture_id"], "priority": "high"} for item in seeded],
            "validation": [{"venture_id": item["venture_id"], "priority": "high"} for item in seeded],
            "capital": [],
            "trust": [{"venture_id": item["venture_id"], "priority": "medium"} for item in seeded if item["trust_review_status"] != "green"],
            "doctrine": [],
        },
    }


def ensure_state(runtime_root: str) -> dict[str, Any]:
    path = state_path(runtime_root)
    if path.exists():
        state = _normalize_state(_read_json(path))
        if not isinstance(state.get("queues"), dict):
            state["queues"] = rebuild_queues(state)
            save_state(runtime_root, state)
        return state
    state = _normalize_state(_bootstrap_state(runtime_root))
    _write_json(path, state)
    return state


def load_state(runtime_root: str) -> dict[str, Any]:
    return ensure_state(runtime_root)


def save_state(runtime_root: str, state: dict[str, Any]) -> dict[str, Any]:
    state = _normalize_state(state)
    state["updated_at"] = _now_iso()
    state["queues"] = rebuild_queues(state)
    _write_json(state_path(runtime_root), state)
    return state


def read_log(runtime_root: str, name: str) -> list[dict[str, Any]]:
    return _read_jsonl(log_path(runtime_root, name))


def append_log(runtime_root: str, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    record = {"created_at": _now_iso(), **payload}
    _append_jsonl(log_path(runtime_root, name), record)
    return record


def _latest_records_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = str(row.get(key) or "").strip()
        if value:
            latest[value] = row
    return latest


def _priority_value(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(str(priority or "medium"), 3)


def _execution_snapshot(runtime_root: str, state: dict[str, Any], priorities: list[dict[str, Any]]) -> dict[str, Any]:
    active_ventures = [item for item in state.get("ventures", []) if isinstance(item, dict) and str(item.get("status") or "") == "active"]
    priority_lookup = {str(item.get("venture_id") or ""): item for item in priorities if isinstance(item, dict)}
    latest_experiments = _latest_records_by_key(read_log(runtime_root, "experiments"), "experiment_id")
    latest_build_requests = _latest_records_by_key(read_log(runtime_root, "build_requests"), "request_id")
    latest_kpis: dict[str, dict[str, Any]] = {}
    for row in read_log(runtime_root, "kpi_snapshots"):
        if not isinstance(row, dict):
            continue
        venture_id = str(row.get("venture_id") or "").strip()
        if venture_id:
            latest_kpis[venture_id] = row
    active_experiments: list[dict[str, Any]] = []
    open_build_requests: list[dict[str, Any]] = []
    experiments_by_venture: dict[str, list[dict[str, Any]]] = {}
    requests_by_venture: dict[str, list[dict[str, Any]]] = {}
    experiment_seen: set[str] = set()
    build_request_seen: set[str] = set()
    for row in latest_experiments.values():
        venture_id = str(row.get("venture_id") or "").strip()
        if not venture_id:
            continue
        experiment_seen.add(venture_id)
        status = str(row.get("status") or "proposed")
        if status in {"won", "lost", "cancelled", "archived"}:
            continue
        compact = {
            "venture_id": venture_id,
            "experiment_id": str(row.get("experiment_id") or ""),
            "focus": str(row.get("focus") or ""),
            "status": status,
            "target_metric": str(row.get("target_metric") or ""),
            "next_step": str(row.get("next_step") or ""),
        }
        active_experiments.append(compact)
        experiments_by_venture.setdefault(venture_id, []).append(compact)
    for row in latest_build_requests.values():
        venture_id = str(row.get("venture_id") or "").strip()
        if not venture_id:
            continue
        build_request_seen.add(venture_id)
        status = str(row.get("status") or "open")
        if status in {"shipped", "cancelled", "archived"}:
            continue
        compact = {
            "venture_id": venture_id,
            "request_id": str(row.get("request_id") or ""),
            "title": str(row.get("title") or ""),
            "kind": str(row.get("kind") or ""),
            "priority": str(row.get("priority") or "medium"),
            "status": status,
            "linked_experiment_id": str(row.get("linked_experiment_id") or ""),
        }
        open_build_requests.append(compact)
        requests_by_venture.setdefault(venture_id, []).append(compact)
    active_experiments.sort(key=lambda item: (str(item.get("venture_id") or ""), str(item.get("experiment_id") or "")))
    open_build_requests.sort(key=lambda item: (_priority_value(str(item.get("priority") or "medium")), str(item.get("venture_id") or ""), str(item.get("request_id") or "")))
    ventures: list[dict[str, Any]] = []
    stale_kpi_ventures: list[str] = []
    for venture in active_ventures:
        venture_id = str(venture.get("venture_id") or "venture")
        priority_meta = priority_lookup.get(venture_id, {})
        venture_experiments = experiments_by_venture.get(venture_id, [])
        venture_requests = requests_by_venture.get(venture_id, [])
        latest_kpi = latest_kpis.get(venture_id, {})
        required_tasks: list[str] = []
        if not venture_experiments:
            required_tasks.append("open_or_refresh_validation_experiment")
        if not latest_kpi:
            required_tasks.append("capture_kpi_snapshot")
            stale_kpi_ventures.append(venture_id)
        if venture_requests:
            required_tasks.append("collapse_build_backlog_to_one_shippable_slice" if len(venture_requests) >= 4 else "ship_highest_priority_build_request")
        revenue = float(latest_kpi.get("weekly_revenue", 0.0) or 0.0) if latest_kpi else 0.0
        if int(venture.get("paid_signals_this_week", 0) or 0) <= 0 and revenue <= 0.0:
            required_tasks.append("force_paid_signal_test")
        if str(venture.get("trust_review_status") or "amber") != "green":
            required_tasks.append("run_trust_review")
        if int(venture.get("weekly_update_freshness_days", 0) or 0) >= 5:
            required_tasks.append("capture_founder_update")
        if not required_tasks:
            required_tasks.append(str(priority_meta.get("next_action") or "ship_next_validation_commitment"))
        ventures.append(
            {
                "venture_id": venture_id,
                "label": str(venture.get("label") or venture_id),
                "priority": int(priority_meta.get("priority", 0) or 0),
                "bottleneck": str(venture.get("bottleneck") or priority_meta.get("bottleneck") or "model_gap"),
                "next_action": str(priority_meta.get("next_action") or "ship_next_validation_commitment"),
                "active_experiment_count": len(venture_experiments),
                "open_build_request_count": len(venture_requests),
                "experiment_seen": venture_id in experiment_seen,
                "build_request_seen": venture_id in build_request_seen,
                "kpi_seen": bool(latest_kpi),
                "active_experiments": venture_experiments[:3],
                "open_build_requests": venture_requests[:3],
                "latest_kpi_snapshot": latest_kpi if isinstance(latest_kpi, dict) else {},
                "required_tasks": required_tasks,
            }
        )
    ventures.sort(key=lambda item: (-int(item.get("priority", 0) or 0), str(item.get("venture_id") or "")))
    return {
        "generated_at": _now_iso(),
        "active_experiment_count": len(active_experiments),
        "open_build_request_count": len(open_build_requests),
        "stale_kpi_ventures": stale_kpi_ventures,
        "active_experiments": active_experiments,
        "open_build_requests": open_build_requests,
        "ventures": ventures,
    }


def _sync_execution_state(state: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    summary_by_venture = {
        str(item.get("venture_id") or ""): item
        for item in execution.get("ventures", [])
        if isinstance(item, dict) and item.get("venture_id")
    }
    for venture in state.get("ventures", []):
        if not isinstance(venture, dict):
            continue
        venture_id = str(venture.get("venture_id") or "")
        summary = summary_by_venture.get(venture_id)
        if not summary:
            continue
        venture["active_experiment_count"] = int(summary.get("active_experiment_count", 0) or 0)
        venture["open_build_request_count"] = int(summary.get("open_build_request_count", 0) or 0)
        if summary.get("build_request_seen"):
            venture["build_backlog_count"] = int(summary.get("open_build_request_count", 0) or 0)
        latest_kpi = summary.get("latest_kpi_snapshot", {})
        if not isinstance(latest_kpi, dict) or not summary.get("kpi_seen"):
            continue
        venture["latest_kpi_snapshot_at"] = str(latest_kpi.get("created_at") or venture.get("latest_kpi_snapshot_at") or "")
        for key in ("stage", "customer_conversations_this_week", "paid_signals_this_week", "automation_coverage", "weekly_revenue", "pipeline_count", "active_users"):
            if latest_kpi.get(key) is not None:
                venture[key] = latest_kpi[key]
    return state


def _sync_customer_gtm_state(state: dict[str, Any], customer_gtm: dict[str, Any]) -> dict[str, Any]:
    summary_by_venture = {
        str(item.get("venture_id") or ""): item
        for item in customer_gtm.get("ventures", [])
        if isinstance(item, dict) and item.get("venture_id")
    }
    for venture in state.get("ventures", []):
        if not isinstance(venture, dict):
            continue
        summary = summary_by_venture.get(str(venture.get("venture_id") or ""))
        if not summary:
            continue
        venture["customer_signal_count"] = int(summary.get("conversation_count", 0) or 0)
        venture["willingness_signal_count"] = int(summary.get("willingness_signal_count", 0) or 0)
        venture["open_pipeline_count"] = int(summary.get("open_pipeline_count", 0) or 0)
        venture["open_pipeline_value"] = float(summary.get("open_pipeline_value", 0.0) or 0.0)
        if summary.get("top_objections"):
            venture["top_objection"] = str(summary["top_objections"][0])
        venture["customer_conversations_this_week"] = max(
            int(venture.get("customer_conversations_this_week", 0) or 0),
            int(summary.get("conversation_count", 0) or 0),
        )
        venture["pipeline_count"] = max(
            int(venture.get("pipeline_count", 0) or 0),
            int(summary.get("open_pipeline_count", 0) or 0),
        )
    return state


def _sync_trust_capital_state(state: dict[str, Any], trust_capital: dict[str, Any]) -> dict[str, Any]:
    summary_by_venture = {
        str(item.get("venture_id") or ""): item
        for item in trust_capital.get("ventures", [])
        if isinstance(item, dict) and item.get("venture_id")
    }
    for venture in state.get("ventures", []):
        if not isinstance(venture, dict):
            continue
        summary = summary_by_venture.get(str(venture.get("venture_id") or ""))
        if not summary:
            continue
        venture["trust_review_status"] = str(summary.get("trust_status") or venture.get("trust_review_status") or "amber")
        venture["capital_readiness"] = bool(summary.get("capital_readiness") or False)
        venture["blocking_trust_review"] = bool(summary.get("blocking") or False)
        venture["ready_data_room_count"] = int(summary.get("ready_data_room_count", 0) or 0)
        venture["total_data_room_count"] = int(summary.get("total_data_room_count", 0) or 0)
        venture["investor_target_count"] = int(summary.get("open_investor_count", 0) or 0)
        venture["interested_investor_count"] = int(summary.get("interested_investor_count", 0) or 0)
        if summary.get("risk_area"):
            venture["trust_risk_area"] = str(summary.get("risk_area"))
    return state


def _sync_portfolio_learning_state(state: dict[str, Any], portfolio_learning: dict[str, Any]) -> dict[str, Any]:
    summary_by_venture = {
        str(item.get("venture_id") or ""): item
        for item in portfolio_learning.get("ventures", [])
        if isinstance(item, dict) and item.get("venture_id")
    }
    for venture in state.get("ventures", []):
        if not isinstance(venture, dict):
            continue
        summary = summary_by_venture.get(str(venture.get("venture_id") or ""))
        if not summary:
            continue
        venture["portfolio_retrospective_count"] = int(summary.get("retrospective_count", 0) or 0)
        venture["promoted_playbook_count"] = int(summary.get("promoted_playbook_count", 0) or 0)
        venture["shared_asset_count"] = int(summary.get("reusable_asset_count", 0) or 0)
        venture["repeated_failure_count"] = int(summary.get("repeated_failure_count", 0) or 0)
        venture["doctrine_ready"] = bool(summary.get("doctrine_ready") or False)
    return state


def _build_venture_task_packets(
    execution: dict[str, Any],
    customer_gtm: dict[str, Any],
    trust_capital: dict[str, Any],
    portfolio_learning: dict[str, Any],
) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    gtm_by_venture = {
        str(item.get("venture_id") or ""): item
        for item in customer_gtm.get("ventures", [])
        if isinstance(item, dict) and item.get("venture_id")
    }
    trust_by_venture = {
        str(item.get("venture_id") or ""): item
        for item in trust_capital.get("ventures", [])
        if isinstance(item, dict) and item.get("venture_id")
    }
    learning_by_venture = {
        str(item.get("venture_id") or ""): item
        for item in portfolio_learning.get("ventures", [])
        if isinstance(item, dict) and item.get("venture_id")
    }
    for item in execution.get("ventures", []):
        if not isinstance(item, dict):
            continue
        latest_kpi = item.get("latest_kpi_snapshot", {}) if isinstance(item.get("latest_kpi_snapshot"), dict) else {}
        gtm = gtm_by_venture.get(str(item.get("venture_id") or ""), {})
        trust = trust_by_venture.get(str(item.get("venture_id") or ""), {})
        learning = learning_by_venture.get(str(item.get("venture_id") or ""), {})
        combined_tasks = [str(task) for task in item.get("required_tasks", [])[:5]]
        for task in gtm.get("gtm_tasks", []):
            text = str(task)
            if text and text not in combined_tasks:
                combined_tasks.append(text)
        for task in trust.get("capital_tasks", []):
            text = str(task)
            if text and text not in combined_tasks:
                combined_tasks.append(text)
        for task in learning.get("knowledge_tasks", []):
            text = str(task)
            if text and text not in combined_tasks:
                combined_tasks.append(text)
        packets.append(
            {
                "venture_id": str(item.get("venture_id") or "venture"),
                "label": str(item.get("label") or item.get("venture_id") or "venture"),
                "priority": int(item.get("priority", 0) or 0),
                "bottleneck": str(item.get("bottleneck") or "model_gap"),
                "next_action": str(item.get("next_action") or "ship_next_validation_commitment"),
                "required_tasks": combined_tasks[:8],
                "active_experiment_count": int(item.get("active_experiment_count", 0) or 0),
                "open_build_request_count": int(item.get("open_build_request_count", 0) or 0),
                "customer_signal_count": int(gtm.get("conversation_count", 0) or 0),
                "willingness_signal_count": int(gtm.get("willingness_signal_count", 0) or 0),
                "open_pipeline_count": int(gtm.get("open_pipeline_count", 0) or 0),
                "open_pipeline_value": float(gtm.get("open_pipeline_value", 0.0) or 0.0),
                "top_objections": [str(entry) for entry in gtm.get("top_objections", [])[:3]],
                "trust_status": str(trust.get("trust_status") or ""),
                "capital_readiness": bool(trust.get("capital_readiness") or False),
                "ready_data_room_count": int(trust.get("ready_data_room_count", 0) or 0),
                "investor_target_count": int(trust.get("open_investor_count", 0) or 0),
                "portfolio_retrospective_count": int(learning.get("retrospective_count", 0) or 0),
                "promoted_playbook_count": int(learning.get("promoted_playbook_count", 0) or 0),
                "reusable_asset_count": int(learning.get("reusable_asset_count", 0) or 0),
                "doctrine_ready": bool(learning.get("doctrine_ready") or False),
                "latest_weekly_revenue": latest_kpi.get("weekly_revenue"),
                "latest_pipeline_count": latest_kpi.get("pipeline_count"),
                "latest_active_users": latest_kpi.get("active_users"),
            }
        )
    return packets


def _scout_snapshot(runtime_root: str) -> dict[str, Any]:
    latest_applications = _latest_records_by_key(read_log(runtime_root, "scout_applications"), "application_id")
    latest_reviews = _latest_records_by_key(read_log(runtime_root, "admission_reviews"), "application_id")
    admissions = read_log(runtime_root, "admissions")
    admitted_venture_ids = {
        str(item.get("venture_id") or "")
        for item in admissions
        if isinstance(item, dict) and str(item.get("venture_id") or "").strip()
    }
    applications: list[dict[str, Any]] = []
    packets: list[dict[str, Any]] = []
    for application in latest_applications.values():
        application_id = str(application.get("application_id") or "").strip()
        venture_id = str(application.get("venture_id") or "").strip()
        review = latest_reviews.get(application_id, {})
        review_decision = str(review.get("decision") or "").strip()
        if venture_id and venture_id in admitted_venture_ids:
            status = "admitted"
        elif review_decision == "reject":
            status = "rejected"
        elif review_decision in {"watchlist", "invite"}:
            status = review_decision
        else:
            status = "pending"
        score = float(application.get("incubator_compound_score", 0.0) or 0.0)
        item = {
            "application_id": application_id,
            "venture_id": venture_id,
            "label": str(application.get("label") or venture_id or application_id),
            "founder_id": str(application.get("founder_id") or ""),
            "founder_label": str(application.get("founder_label") or application.get("founder_id") or ""),
            "entry_source": str(application.get("entry_source") or ""),
            "thesis_summary": str(application.get("thesis_summary") or ""),
            "incubator_compound_score": round(score, 4),
            "resilience_score": float(application.get("resilience_score", 0.0) or 0.0),
            "recommended_decision": str(application.get("recommended_admission_decision") or "watchlist"),
            "manual_review_required": bool(application.get("manual_review_required") or False),
            "status": status,
            "review_decision": review_decision,
            "review_note": str(review.get("note") or ""),
            "recommended_next_step": str(application.get("recommended_next_step") or ""),
            "first_week_plan": [str(item) for item in application.get("first_week_plan", [])[:3]] if isinstance(application.get("first_week_plan"), list) else [],
            "created_at": str(application.get("created_at") or ""),
        }
        applications.append(item)
        if status in {"pending", "watchlist", "invite"}:
            packets.append(
                {
                    "application_id": item["application_id"],
                    "venture_id": item["venture_id"],
                    "label": item["label"],
                    "founder_label": item["founder_label"],
                    "entry_source": item["entry_source"],
                    "incubator_compound_score": item["incubator_compound_score"],
                    "recommended_decision": item["recommended_decision"],
                    "manual_review_required": item["manual_review_required"],
                    "recommended_next_step": item["recommended_next_step"],
                    "first_week_plan": list(item["first_week_plan"]),
                    "status": item["status"],
                }
            )
    applications.sort(key=lambda item: (-float(item.get("incubator_compound_score", 0.0) or 0.0), str(item.get("application_id") or "")))
    packets.sort(key=lambda item: (-float(item.get("incubator_compound_score", 0.0) or 0.0), str(item.get("application_id") or "")))
    return {
        "generated_at": _now_iso(),
        "application_count": len(applications),
        "pending_count": len([item for item in applications if item["status"] in {"pending", "watchlist", "invite"}]),
        "admitted_count": len([item for item in applications if item["status"] == "admitted"]),
        "rejected_count": len([item for item in applications if item["status"] == "rejected"]),
        "applications": applications,
        "pending_packets": packets,
    }


def _customer_gtm_snapshot(runtime_root: str, state: dict[str, Any]) -> dict[str, Any]:
    latest_conversations = _latest_records_by_key(read_log(runtime_root, "customer_conversations"), "conversation_id")
    latest_opportunities = _latest_records_by_key(read_log(runtime_root, "pipeline_opportunities"), "opportunity_id")
    conversations_by_venture: dict[str, list[dict[str, Any]]] = {}
    open_pipeline_by_venture: dict[str, list[dict[str, Any]]] = {}
    objection_counts_by_venture: dict[str, dict[str, int]] = {}
    willingness_counts_by_venture: dict[str, int] = {}
    for row in latest_conversations.values():
        venture_id = str(row.get("venture_id") or "").strip()
        if not venture_id:
            continue
        compact = {
            "conversation_id": str(row.get("conversation_id") or ""),
            "venture_id": venture_id,
            "customer_label": str(row.get("customer_label") or row.get("customer_id") or ""),
            "channel": str(row.get("channel") or ""),
            "stage": str(row.get("stage") or ""),
            "willingness_to_pay": str(row.get("willingness_to_pay") or ""),
            "objection": str(row.get("objection") or ""),
            "outcome": str(row.get("outcome") or ""),
            "next_step": str(row.get("next_step") or ""),
            "created_at": str(row.get("created_at") or ""),
        }
        conversations_by_venture.setdefault(venture_id, []).append(compact)
        objection = compact["objection"].strip()
        if objection:
            objection_counts_by_venture.setdefault(venture_id, {})
            objection_counts_by_venture[venture_id][objection] = objection_counts_by_venture[venture_id].get(objection, 0) + 1
        if compact["willingness_to_pay"] in {"yes", "strong_yes"}:
            willingness_counts_by_venture[venture_id] = willingness_counts_by_venture.get(venture_id, 0) + 1
    for row in latest_opportunities.values():
        venture_id = str(row.get("venture_id") or "").strip()
        if not venture_id:
            continue
        status = str(row.get("status") or "open")
        compact = {
            "opportunity_id": str(row.get("opportunity_id") or ""),
            "venture_id": venture_id,
            "customer_label": str(row.get("customer_label") or row.get("customer_id") or ""),
            "stage": str(row.get("stage") or ""),
            "value": float(row.get("value", 0.0) or 0.0),
            "confidence": float(row.get("confidence", 0.0) or 0.0),
            "status": status,
            "source": str(row.get("source") or ""),
            "next_step": str(row.get("next_step") or ""),
            "created_at": str(row.get("created_at") or ""),
        }
        if status not in {"lost", "closed", "archived"}:
            open_pipeline_by_venture.setdefault(venture_id, []).append(compact)
    ventures: list[dict[str, Any]] = []
    customer_signal_packets: list[dict[str, Any]] = []
    pipeline_board: list[dict[str, Any]] = []
    active_ventures = [item for item in state.get("ventures", []) if isinstance(item, dict) and str(item.get("status") or "") == "active"]
    for venture in active_ventures:
        venture_id = str(venture.get("venture_id") or "venture")
        conversations = sorted(
            conversations_by_venture.get(venture_id, []),
            key=lambda item: (str(item.get("created_at") or ""), str(item.get("conversation_id") or "")),
            reverse=True,
        )
        opportunities = sorted(
            open_pipeline_by_venture.get(venture_id, []),
            key=lambda item: (-float(item.get("confidence", 0.0) or 0.0), -float(item.get("value", 0.0) or 0.0), str(item.get("opportunity_id") or "")),
        )
        top_objections = [
            item[0]
            for item in sorted(
                objection_counts_by_venture.get(venture_id, {}).items(),
                key=lambda entry: (-entry[1], entry[0]),
            )[:3]
        ]
        willingness_signals = willingness_counts_by_venture.get(venture_id, 0)
        open_pipeline_value = round(sum(float(item.get("value", 0.0) or 0.0) for item in opportunities), 2)
        gtm_tasks: list[str] = []
        if len(conversations) < 3:
            gtm_tasks.append("run_three_customer_conversations")
        if not opportunities:
            gtm_tasks.append("build_outbound_or_referral_pipeline")
        elif open_pipeline_value < 1000.0:
            gtm_tasks.append("increase_pipeline_value_density")
        if willingness_signals <= 0 and int(venture.get("paid_signals_this_week", 0) or 0) <= 0:
            gtm_tasks.append("test_pricing_or_paid_pilot")
        if top_objections:
            gtm_tasks.append(f"address_top_objection_{_slug(top_objections[0])}")
        if not gtm_tasks:
            gtm_tasks.append("push_highest_confidence_opportunity_to_close")
        venture_summary = {
            "venture_id": venture_id,
            "label": str(venture.get("label") or venture_id),
            "conversation_count": len(conversations),
            "willingness_signal_count": willingness_signals,
            "top_objections": top_objections,
            "open_pipeline_count": len(opportunities),
            "open_pipeline_value": open_pipeline_value,
            "gtm_tasks": gtm_tasks,
            "recent_conversations": conversations[:5],
            "open_pipeline": opportunities[:5],
        }
        ventures.append(venture_summary)
        customer_signal_packets.append(
            {
                "venture_id": venture_id,
                "label": venture_summary["label"],
                "conversation_count": venture_summary["conversation_count"],
                "willingness_signal_count": venture_summary["willingness_signal_count"],
                "top_objections": list(top_objections),
                "gtm_tasks": list(gtm_tasks[:4]),
            }
        )
        pipeline_board.append(
            {
                "venture_id": venture_id,
                "label": venture_summary["label"],
                "open_pipeline_count": venture_summary["open_pipeline_count"],
                "open_pipeline_value": venture_summary["open_pipeline_value"],
                "opportunities": opportunities[:5],
            }
        )
    ventures.sort(key=lambda item: (-int(item.get("open_pipeline_count", 0) or 0), str(item.get("venture_id") or "")))
    customer_signal_packets.sort(key=lambda item: (-int(item.get("conversation_count", 0) or 0), str(item.get("venture_id") or "")))
    pipeline_board.sort(key=lambda item: (-float(item.get("open_pipeline_value", 0.0) or 0.0), str(item.get("venture_id") or "")))
    return {
        "generated_at": _now_iso(),
        "conversation_count": sum(int(item.get("conversation_count", 0) or 0) for item in ventures),
        "willingness_signal_count": sum(int(item.get("willingness_signal_count", 0) or 0) for item in ventures),
        "open_pipeline_count": sum(int(item.get("open_pipeline_count", 0) or 0) for item in ventures),
        "open_pipeline_value": round(sum(float(item.get("open_pipeline_value", 0.0) or 0.0) for item in ventures), 2),
        "ventures": ventures,
        "customer_signal_packets": customer_signal_packets,
        "pipeline_board": pipeline_board,
    }


def _trust_capital_snapshot(runtime_root: str, state: dict[str, Any]) -> dict[str, Any]:
    latest_trust_reviews = _latest_records_by_key(read_log(runtime_root, "trust_reviews"), "venture_id")
    latest_data_room_items = _latest_records_by_key(read_log(runtime_root, "data_room_items"), "item_id")
    latest_investor_targets = _latest_records_by_key(read_log(runtime_root, "investor_targets"), "target_id")
    active_ventures = [item for item in state.get("ventures", []) if isinstance(item, dict) and str(item.get("status") or "") == "active"]
    data_room_by_venture: dict[str, list[dict[str, Any]]] = {}
    investor_by_venture: dict[str, list[dict[str, Any]]] = {}
    for item in latest_data_room_items.values():
        venture_id = str(item.get("venture_id") or "").strip()
        if venture_id:
            data_room_by_venture.setdefault(venture_id, []).append(item)
    for item in latest_investor_targets.values():
        venture_id = str(item.get("venture_id") or "").strip()
        if venture_id:
            investor_by_venture.setdefault(venture_id, []).append(item)
    ventures: list[dict[str, Any]] = []
    trust_packets: list[dict[str, Any]] = []
    capital_packets: list[dict[str, Any]] = []
    for venture in active_ventures:
        venture_id = str(venture.get("venture_id") or "venture")
        trust_review = latest_trust_reviews.get(venture_id, {})
        trust_status = str(trust_review.get("status") or venture.get("trust_review_status") or "amber")
        risk_area = str(trust_review.get("risk_area") or "")
        blocking = bool(trust_review.get("blocking")) or trust_status == "red"
        data_items = data_room_by_venture.get(venture_id, [])
        ready_items = [item for item in data_items if str(item.get("status") or "") in {"ready", "approved"}]
        missing_items = [item for item in data_items if str(item.get("status") or "") in {"missing", "draft"}]
        investors = investor_by_venture.get(venture_id, [])
        open_investors = [item for item in investors if str(item.get("status") or "") not in {"passed", "archived"}]
        interested_investors = [item for item in investors if str(item.get("status") or "") in {"interested", "diligence"}]
        intro_ready = (
            trust_status == "green"
            and not blocking
            and len(ready_items) >= 2
            and (
                float(venture.get("weekly_revenue", 0.0) or 0.0) > 0.0
                or int(venture.get("paid_signals_this_week", 0) or 0) > 0
                or int(venture.get("willingness_signal_count", 0) or 0) > 0
            )
        )
        capital_tasks: list[str] = []
        if trust_status != "green" or blocking:
            capital_tasks.append("clear_trust_blockers")
        if len(ready_items) < 2:
            capital_tasks.append("complete_core_data_room_items")
        if not open_investors:
            capital_tasks.append("build_investor_target_list")
        elif not interested_investors:
            capital_tasks.append("advance_best_fit_investor_conversation")
        if intro_ready:
            capital_tasks.append("prepare_investor_brief")
        trust_packets.append(
            {
                "venture_id": venture_id,
                "label": str(venture.get("label") or venture_id),
                "trust_status": trust_status,
                "risk_area": risk_area,
                "blocking": blocking,
                "next_step": str(trust_review.get("next_step") or ""),
            }
        )
        capital_packets.append(
            {
                "venture_id": venture_id,
                "label": str(venture.get("label") or venture_id),
                "capital_readiness": intro_ready,
                "ready_data_room_count": len(ready_items),
                "total_data_room_count": len(data_items),
                "open_investor_count": len(open_investors),
                "interested_investor_count": len(interested_investors),
                "capital_tasks": capital_tasks[:4],
                "brief_claim": f"{venture.get('label') or venture_id} is {'ready' if intro_ready else 'not yet ready'} for investor-facing packaging.",
            }
        )
        ventures.append(
            {
                "venture_id": venture_id,
                "label": str(venture.get("label") or venture_id),
                "trust_status": trust_status,
                "risk_area": risk_area,
                "blocking": blocking,
                "latest_trust_scope": str(trust_review.get("scope") or ""),
                "latest_trust_review_at": str(trust_review.get("created_at") or ""),
                "ready_data_room_count": len(ready_items),
                "total_data_room_count": len(data_items),
                "missing_data_room_count": len(missing_items),
                "open_investor_count": len(open_investors),
                "interested_investor_count": len(interested_investors),
                "capital_readiness": intro_ready,
                "capital_tasks": capital_tasks,
            }
        )
    ventures.sort(key=lambda item: (not bool(item.get("blocking")), not bool(item.get("capital_readiness")), str(item.get("venture_id") or "")))
    trust_packets.sort(key=lambda item: (str(item.get("trust_status") or ""), str(item.get("venture_id") or "")))
    capital_packets.sort(key=lambda item: (not bool(item.get("capital_readiness")), str(item.get("venture_id") or "")))
    return {
        "generated_at": _now_iso(),
        "trust_review_count": len(latest_trust_reviews),
        "data_room_item_count": len(latest_data_room_items),
        "investor_target_count": len(latest_investor_targets),
        "blocking_trust_count": len([item for item in ventures if item["blocking"]]),
        "capital_ready_count": len([item for item in ventures if item["capital_readiness"]]),
        "ventures": ventures,
        "trust_packets": trust_packets,
        "capital_packets": capital_packets,
    }


def _portfolio_learning_snapshot(runtime_root: str, state: dict[str, Any]) -> dict[str, Any]:
    latest_retrospectives = _latest_records_by_key(read_log(runtime_root, "portfolio_retrospectives"), "retrospective_id")
    latest_reusable_assets = _latest_records_by_key(read_log(runtime_root, "reusable_assets"), "asset_id")
    active_ventures = [item for item in state.get("ventures", []) if isinstance(item, dict) and str(item.get("status") or "") == "active"]
    retros_by_venture: dict[str, list[dict[str, Any]]] = {}
    assets_by_venture: dict[str, list[dict[str, Any]]] = {}
    failure_counts: dict[str, int] = {}
    failure_ventures: dict[str, set[str]] = {}
    for item in latest_retrospectives.values():
        venture_id = str(item.get("venture_id") or "").strip()
        if venture_id:
            retros_by_venture.setdefault(venture_id, []).append(item)
        failure_mode = str(item.get("failure_mode") or "").strip()
        if failure_mode:
            failure_counts[failure_mode] = failure_counts.get(failure_mode, 0) + 1
            failure_ventures.setdefault(failure_mode, set()).add(venture_id or "unknown")
    for item in latest_reusable_assets.values():
        venture_id = str(item.get("venture_id") or "").strip()
        if venture_id:
            assets_by_venture.setdefault(venture_id, []).append(item)
    reusable_assets = [
        {
            "asset_id": str(item.get("asset_id") or ""),
            "venture_id": str(item.get("venture_id") or ""),
            "label": str(item.get("label") or item.get("asset_id") or "asset"),
            "kind": str(item.get("kind") or ""),
            "status": str(item.get("status") or ""),
            "reused_by_count": int(item.get("reused_by_count", 0) or 0),
            "shared_surface": str(item.get("shared_surface") or ""),
            "next_step": str(item.get("next_step") or ""),
        }
        for item in latest_reusable_assets.values()
    ]
    repeated_failures: list[dict[str, Any]] = []
    for failure_mode, count in sorted(failure_counts.items(), key=lambda item: (-int(item[1]), str(item[0]))):
        ventures_hit = sorted(name for name in failure_ventures.get(failure_mode, set()) if name and name != "unknown")
        if count < 2 and len(ventures_hit) < 2:
            continue
        repeated_failures.append(
            {
                "failure_mode": failure_mode,
                "count": count,
                "venture_count": len(ventures_hit),
                "ventures": ventures_hit,
                "recommended_boundary": f"Do not treat `{failure_mode}` as solved until the next launch packet shows a cleaner handoff or review loop.",
            }
        )
    ventures: list[dict[str, Any]] = []
    doctrine_packets: list[dict[str, Any]] = []
    playbook_packets: list[dict[str, Any]] = []
    for venture in active_ventures:
        venture_id = str(venture.get("venture_id") or "venture")
        retros = sorted(retros_by_venture.get(venture_id, []), key=lambda item: str(item.get("created_at") or ""), reverse=True)
        assets = sorted(assets_by_venture.get(venture_id, []), key=lambda item: str(item.get("created_at") or ""), reverse=True)
        promoted_rows = [
            item
            for item in retros
            if bool(item.get("promote_doctrine"))
            and str(item.get("doctrine_claim") or "").strip()
            and str(item.get("evidence_strength") or "medium") in {"medium", "high"}
        ]
        top_failures: list[str] = []
        for row in retros:
            failure_mode = str(row.get("failure_mode") or "").strip()
            if failure_mode and failure_mode not in top_failures:
                top_failures.append(failure_mode)
        repeated_failure_count = len([mode for mode in top_failures if failure_counts.get(mode, 0) >= 2 or len(failure_ventures.get(mode, set())) >= 2])
        latest_retro = retros[0] if retros else {}
        knowledge_tasks: list[str] = []
        if not retros:
            knowledge_tasks.append("log_portfolio_retrospective")
        if not assets:
            knowledge_tasks.append("capture_reusable_asset")
        if promoted_rows:
            knowledge_tasks.append("review_doctrine_promotion")
        if repeated_failure_count > 0:
            knowledge_tasks.append("write_boundary_for_repeated_failure")
        ventures.append(
            {
                "venture_id": venture_id,
                "label": str(venture.get("label") or venture_id),
                "retrospective_count": len(retros),
                "promoted_playbook_count": len(promoted_rows),
                "reusable_asset_count": len(assets),
                "repeated_failure_count": repeated_failure_count,
                "doctrine_ready": bool(promoted_rows),
                "latest_scope": str(latest_retro.get("scope") or ""),
                "latest_outcome": str(latest_retro.get("outcome") or ""),
                "latest_lesson": str(latest_retro.get("lesson") or ""),
                "top_failure_modes": top_failures[:3],
                "knowledge_tasks": knowledge_tasks[:4],
            }
        )
        if promoted_rows:
            latest_promoted = promoted_rows[0]
            playbook_packets.append(
                {
                    "venture_id": venture_id,
                    "label": str(venture.get("label") or venture_id),
                    "promoted_playbook_count": len(promoted_rows),
                    "doctrine_ready": True,
                    "top_claim": str(latest_promoted.get("doctrine_claim") or ""),
                    "boundary": str(latest_promoted.get("boundary") or ""),
                    "evidence_strength": str(latest_promoted.get("evidence_strength") or "medium"),
                    "next_step": str(latest_promoted.get("next_step") or ""),
                }
            )
        for row in promoted_rows[:3]:
            doctrine_packets.append(
                {
                    "venture_id": venture_id,
                    "label": str(venture.get("label") or venture_id),
                    "scope": str(row.get("scope") or ""),
                    "outcome": str(row.get("outcome") or ""),
                    "doctrine_claim": str(row.get("doctrine_claim") or ""),
                    "boundary": str(row.get("boundary") or ""),
                    "evidence_strength": str(row.get("evidence_strength") or "medium"),
                    "lesson": str(row.get("lesson") or ""),
                    "next_step": str(row.get("next_step") or ""),
                }
            )
    ventures.sort(key=lambda item: (-int(item.get("promoted_playbook_count", 0) or 0), -int(item.get("reusable_asset_count", 0) or 0), str(item.get("venture_id") or "")))
    playbook_packets.sort(key=lambda item: (-int(item.get("promoted_playbook_count", 0) or 0), str(item.get("venture_id") or "")))
    doctrine_packets.sort(key=lambda item: (str(item.get("evidence_strength") or ""), str(item.get("venture_id") or "")), reverse=True)
    reusable_assets.sort(key=lambda item: (-int(item.get("reused_by_count", 0) or 0), str(item.get("asset_id") or "")))
    return {
        "generated_at": _now_iso(),
        "retrospective_count": len(latest_retrospectives),
        "reusable_asset_count": len(latest_reusable_assets),
        "promoted_playbook_count": sum(int(item.get("promoted_playbook_count", 0) or 0) for item in ventures),
        "doctrine_packet_count": len(doctrine_packets),
        "repeated_failure_count": len(repeated_failures),
        "ventures": ventures,
        "doctrine_packets": doctrine_packets,
        "repeated_failures": repeated_failures,
        "reusable_assets": reusable_assets,
        "playbook_packets": playbook_packets,
    }


def _policy(mutations: dict[str, str]) -> dict[str, str]:
    policy = dict(DEFAULT_POLICY)
    for key, value in mutations.items():
        if key in policy and str(value).strip():
            policy[key] = str(value)
    return policy


def _batch_snapshot(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a snapshot of all batches with their venture health."""
    ventures_by_id = {str(v.get("venture_id")): v for v in state.get("ventures", []) if isinstance(v, dict)}
    snapshots: list[dict[str, Any]] = []
    for batch in state.get("batches", []):
        if not isinstance(batch, dict):
            continue
        batch_id = str(batch.get("batch_id") or "")
        venture_ids = batch.get("venture_ids", [])
        batch_ventures = [ventures_by_id[vid] for vid in venture_ids if vid in ventures_by_id]
        active = [v for v in batch_ventures if str(v.get("status") or "") == "active"]
        snapshots.append({
            "batch_id": batch_id,
            "label": str(batch.get("label") or batch_id),
            "status": str(batch.get("status") or "forming"),
            "sprint_week": int(batch.get("sprint_week", 0) or 0),
            "duration_weeks": int(batch.get("duration_weeks", 6) or 6),
            "venture_count": len(venture_ids),
            "active_venture_count": len(active),
            "mean_automation": _mean([_num(v.get("automation_coverage"), 0.45) for v in active], 0.0),
            "mean_paid_signals": _mean([_num(v.get("paid_signals_this_week"), 0.0) for v in active], 0.0),
            "total_weekly_revenue": sum(_num(v.get("weekly_revenue"), 0.0) for v in active),
            "ventures": [
                {
                    "venture_id": v["venture_id"],
                    "stage": v.get("stage"),
                    "bottleneck": v.get("bottleneck"),
                    "paid_signals_this_week": _num(v.get("paid_signals_this_week"), 0),
                }
                for v in batch_ventures
            ],
        })
    return snapshots


def _apply_policy(base: dict[str, float], policy: dict[str, str]) -> dict[str, float]:
    adjusted = dict(base)
    for key, value in policy.items():
        for metric, bonus in POLICY_BONUSES.get(key, {}).get(value, {}).items():
            adjusted[metric] = adjusted.get(metric, 0.0) + bonus
    return adjusted


def rebuild_queues(state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    ventures = [item for item in state.get("ventures", []) if isinstance(item, dict)]
    queues = {
        "admissions": [],
        "office_hours": [],
        "build": [],
        "validation": [],
        "capital": [],
        "trust": [],
        "doctrine": [],
    }
    for venture in ventures:
        venture_id = str(venture.get("venture_id") or "venture")
        status = str(venture.get("status") or "active")
        stage = str(venture.get("stage") or "qualification")
        trust = str(venture.get("trust_review_status") or "amber")
        bottleneck = str(venture.get("bottleneck") or "model_gap")
        backlog = int(venture.get("build_backlog_count", 0) or 0)
        paid_signals = int(venture.get("paid_signals_this_week", 0) or 0)
        reuse_assets = int(venture.get("reuse_assets_count", 0) or 0)
        capital_ready = bool(venture.get("capital_readiness") or False)
        retrospectives = int(venture.get("portfolio_retrospective_count", 0) or 0)
        promoted_playbooks = int(venture.get("promoted_playbook_count", 0) or 0)
        repeated_failures = int(venture.get("repeated_failure_count", 0) or 0)
        if status == "admissions":
            queues["admissions"].append({"venture_id": venture_id, "priority": "high"})
            continue
        if status in {"archived", "stopped"}:
            continue
        queues["office_hours"].append({"venture_id": venture_id, "priority": "high" if bottleneck in {"distribution_gap", "revenue_gap"} else "medium"})
        if backlog > 0:
            queues["build"].append({"venture_id": venture_id, "priority": "high" if backlog >= 5 else "medium"})
        if stage in {"qualification", "validation", "go_to_market"}:
            queues["validation"].append({"venture_id": venture_id, "priority": "high" if paid_signals <= 0 else "medium"})
        if (stage in {"go_to_market", "capital_readiness"} and paid_signals > 0) or capital_ready:
            queues["capital"].append({"venture_id": venture_id, "priority": "medium"})
        if trust != "green":
            queues["trust"].append({"venture_id": venture_id, "priority": "high" if trust == "red" else "medium"})
        if reuse_assets >= 4 or retrospectives > 0 or promoted_playbooks > 0 or repeated_failures > 0:
            queues["doctrine"].append({"venture_id": venture_id, "priority": "high" if promoted_playbooks > 0 or repeated_failures > 0 else "medium"})
    return queues


def _venture_priorities(state: dict[str, Any]) -> list[dict[str, Any]]:
    ventures = [item for item in state.get("ventures", []) if isinstance(item, dict) and item.get("status") == "active"]
    priorities: list[dict[str, Any]] = []
    for venture in ventures:
        bottleneck = str(venture.get("bottleneck") or "model_gap")
        trust = str(venture.get("trust_review_status") or "amber")
        priority = 3
        if trust == "red":
            priority += 4
        if bottleneck in {"revenue_gap", "distribution_gap"}:
            priority += 2
        if int(venture.get("weekly_update_freshness_days", 0) or 0) >= 5:
            priority += 1
        priorities.append(
            {
                "venture_id": str(venture.get("venture_id") or "venture"),
                "label": str(venture.get("label") or venture.get("venture_id") or "venture"),
                "priority": priority,
                "bottleneck": bottleneck,
                "trust_review_status": trust,
                "next_action": {
                    "distribution_gap": "rewrite_distribution_surface",
                    "revenue_gap": "force_paid_validation",
                    "automation_gap": "template_repeated_work",
                    "learning_gap": "capture_post_launch_review",
                    "resilience_gap": "tighten_trust_gate",
                    "model_gap": "narrow_customer_and_offer",
                }.get(bottleneck, "review_scope"),
            }
        )
    priorities.sort(key=lambda item: (-int(item["priority"]), str(item["venture_id"])))
    return priorities


def _build_office_hours_packets(state: dict[str, Any], priorities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ventures = {str(item.get("venture_id")): item for item in state.get("ventures", []) if isinstance(item, dict)}
    packets: list[dict[str, Any]] = []
    for item in priorities:
        venture = ventures.get(item["venture_id"], {})
        packets.append(
            {
                "venture_id": item["venture_id"],
                "label": item["label"],
                "priority": item["priority"],
                "agenda": [
                    f"Resolve {item['bottleneck']} before opening a new lane.",
                    f"Review build backlog `{venture.get('build_backlog_count', 0)}` and automation coverage `{venture.get('automation_coverage', 0)}`.",
                    f"Confirm paid signals this week: `{venture.get('paid_signals_this_week', 0)}`.",
                ],
                "commitment": item["next_action"],
            }
        )
    return packets


def _build_decision_packets(state: dict[str, Any], priorities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ventures = {str(item.get("venture_id")): item for item in state.get("ventures", []) if isinstance(item, dict)}
    decisions: list[dict[str, Any]] = []
    for item in priorities:
        venture = ventures.get(item["venture_id"], {})
        trust = str(venture.get("trust_review_status") or "amber")
        paid = int(venture.get("paid_signals_this_week", 0) or 0)
        decision = "continue"
        if trust == "red":
            decision = "narrow"
        elif item["bottleneck"] == "revenue_gap" and paid <= 0:
            decision = "pivot"
        decisions.append(
            {
                "venture_id": item["venture_id"],
                "decision": decision,
                "reason": item["bottleneck"],
                "required_next_step": item["next_action"],
            }
        )
    return decisions


def _score_state(state: dict[str, Any], policy: dict[str, str]) -> dict[str, Any]:
    ventures = [item for item in state.get("ventures", []) if isinstance(item, dict) and item.get("status") == "active"]
    queues = state.get("queues", {}) if isinstance(state.get("queues"), dict) else {}
    active_count = len(ventures)
    portfolio_cap = max(1, int(policy.get("portfolio_cap", "3") or 3))
    overload = max(0, active_count - portfolio_cap)
    update_freshness = _mean([max(0.0, 1.0 - (_num(item.get("weekly_update_freshness_days"), 7.0) / 7.0)) for item in ventures], 0.35)
    review_freshness = _mean([max(0.0, 1.0 - (_num(item.get("last_review_days"), 7.0) / 7.0)) for item in ventures], 0.35)
    automation_base = _mean([_num(item.get("automation_coverage"), 0.45) for item in ventures], 0.42)
    validation_base = _mean(
        [
            min(
                1.0,
                (_num(item.get("customer_conversations_this_week"), 0.0) / 4.0)
                + (_num(item.get("paid_signals_this_week"), 0.0) * 0.2)
                + (min(5.0, _num(item.get("open_pipeline_count"), 0.0)) * 0.05)
                + (min(3.0, _num(item.get("willingness_signal_count"), 0.0)) * 0.08),
            )
            for item in ventures
        ],
        0.28,
    )
    trust_base = _mean([_trust_score(str(item.get("trust_review_status") or "amber")) for item in ventures], 0.5)
    knowledge_base = _mean(
        [
            min(
                1.0,
                (min(5.0, _num(item.get("reuse_assets_count"), 0.0)) / 5.0) * 0.45
                + (min(3.0, _num(item.get("portfolio_retrospective_count"), 0.0)) / 3.0) * 0.25
                + (min(2.0, _num(item.get("promoted_playbook_count"), 0.0)) / 2.0) * 0.30,
            )
            for item in ventures
        ],
        0.25,
    )
    queue_penalty = min(0.25, (len(queues.get("build", [])) + len(queues.get("validation", []))) * 0.015)
    focus_base = max(0.0, 0.72 - overload * 0.17 - queue_penalty)
    founder_latency = _mean([max(0.0, 1.0 - (_num(item.get("founder_update_latency_hours"), 72.0) / 72.0)) for item in ventures], 0.4)
    adjusted = _apply_policy(
        {
            "focus": focus_base,
            "automation": automation_base,
            "review": (update_freshness * 0.55) + (review_freshness * 0.45),
            "validation": validation_base,
            "trust": trust_base,
            "knowledge": knowledge_base,
        },
        policy,
    )
    focus = _clamp(adjusted["focus"])
    automation = _clamp(adjusted["automation"])
    review = _clamp(adjusted["review"] + founder_latency * 0.08)
    validation = _clamp(adjusted["validation"])
    trust = _clamp(adjusted["trust"])
    knowledge = _clamp(adjusted["knowledge"])
    overall = _clamp(0.10 + focus * 0.14 + automation * 0.13 + review * 0.13 + validation * 0.16 + trust * 0.17 + knowledge * 0.12 - overload * 0.04)
    confidence = _clamp(0.40 + overall * 0.18 + trust * 0.08 + review * 0.06 - overload * 0.03)
    bottleneck, _ = min(
        [
            ("portfolio_focus_gap", focus),
            ("automation_gap", automation),
            ("review_hygiene_gap", review),
            ("validation_gap", validation),
            ("trust_gap", trust),
            ("knowledge_capture_gap", knowledge),
        ],
        key=lambda item: item[1],
    )
    return {
        "incubator_compound_score": overall,
        "ops_portfolio_focus_score": focus,
        "ops_automation_coverage_score": automation,
        "ops_review_hygiene_score": review,
        "ops_validation_velocity_score": validation,
        "ops_trust_hygiene_score": trust,
        "ops_knowledge_capture_score": knowledge,
        "verdict_confidence": confidence,
        "bottleneck": bottleneck,
        "active_portfolio_count": active_count,
        "portfolio_cap": portfolio_cap,
    }


def _latest_tick(runtime_root: str) -> dict[str, Any]:
    path = _path(runtime_root, "latest_tick.json")
    if not path.exists():
        return {}
    return _read_json(path)


def refresh_ops_artifacts(runtime_root: str, policy: dict[str, str] | None = None) -> dict[str, Any]:
    state = ensure_state(runtime_root)
    effective_policy = dict(policy or (_latest_tick(runtime_root).get("policy") if _latest_tick(runtime_root) else {}) or DEFAULT_POLICY)
    priorities = _venture_priorities(state)
    execution = _execution_snapshot(runtime_root, state, priorities)
    state = _sync_execution_state(state, execution)
    customer_gtm = _customer_gtm_snapshot(runtime_root, state)
    state = _sync_customer_gtm_state(state, customer_gtm)
    trust_capital = _trust_capital_snapshot(runtime_root, state)
    state = _sync_trust_capital_state(state, trust_capital)
    portfolio_learning = _portfolio_learning_snapshot(runtime_root, state)
    state = _sync_portfolio_learning_state(state, portfolio_learning)
    state = save_state(runtime_root, state)
    priorities = _venture_priorities(state)
    execution = _execution_snapshot(runtime_root, state, priorities)
    customer_gtm = _customer_gtm_snapshot(runtime_root, state)
    scout = _scout_snapshot(runtime_root)
    trust_capital = _trust_capital_snapshot(runtime_root, state)
    portfolio_learning = _portfolio_learning_snapshot(runtime_root, state)
    metrics = _score_state(state, effective_policy)
    office_hours = _build_office_hours_packets(state, priorities)
    decisions = _build_decision_packets(state, priorities)
    venture_tasks = _build_venture_task_packets(execution, customer_gtm, trust_capital, portfolio_learning)
    queue_snapshot = {
        "generated_at": _now_iso(),
        "portfolio_cap": metrics["portfolio_cap"],
        "active_portfolio_count": metrics["active_portfolio_count"],
        "priority_ventures": priorities[:5],
        "venture_task_count": len(venture_tasks),
        "pending_applications": int(scout.get("pending_count", 0) or 0),
        "conversation_count": int(customer_gtm.get("conversation_count", 0) or 0),
        "open_pipeline_count": int(customer_gtm.get("open_pipeline_count", 0) or 0),
        "capital_ready_count": int(trust_capital.get("capital_ready_count", 0) or 0),
        "promoted_playbook_count": int(portfolio_learning.get("promoted_playbook_count", 0) or 0),
        "repeated_failure_count": int(portfolio_learning.get("repeated_failure_count", 0) or 0),
    }
    tick = {
        "generated_at": _now_iso(),
        "policy": effective_policy,
        "metrics": metrics,
        "priority_ventures": priorities[:5],
        "office_hours_count": len(office_hours),
        "decision_count": len(decisions),
        "venture_task_count": len(venture_tasks),
        "stale_kpi_count": len(execution.get("stale_kpi_ventures", [])),
        "pending_application_count": int(scout.get("pending_count", 0) or 0),
        "conversation_count": int(customer_gtm.get("conversation_count", 0) or 0),
        "open_pipeline_count": int(customer_gtm.get("open_pipeline_count", 0) or 0),
        "capital_ready_count": int(trust_capital.get("capital_ready_count", 0) or 0),
        "blocking_trust_count": int(trust_capital.get("blocking_trust_count", 0) or 0),
        "promoted_playbook_count": int(portfolio_learning.get("promoted_playbook_count", 0) or 0),
        "repeated_failure_count": int(portfolio_learning.get("repeated_failure_count", 0) or 0),
    }
    _write_json(_path(runtime_root, "latest_tick.json"), tick)
    _write_json(_path(runtime_root, "queue_snapshot.json"), queue_snapshot)
    _write_json(_path(runtime_root, "office_hours_packets.json"), office_hours)
    _write_json(_path(runtime_root, "decision_packets.json"), decisions)
    _write_json(_path(runtime_root, "execution_snapshot.json"), execution)
    _write_json(_path(runtime_root, "venture_task_packets.json"), venture_tasks)
    _write_json(_path(runtime_root, "scout_snapshot.json"), scout)
    _write_json(_path(runtime_root, "admissions_packets.json"), scout.get("pending_packets", []))
    _write_json(_path(runtime_root, "customer_gtm_snapshot.json"), customer_gtm)
    _write_json(_path(runtime_root, "customer_signal_packets.json"), customer_gtm.get("customer_signal_packets", []))
    _write_json(_path(runtime_root, "pipeline_board.json"), customer_gtm.get("pipeline_board", []))
    _write_json(_path(runtime_root, "trust_capital_snapshot.json"), trust_capital)
    _write_json(_path(runtime_root, "trust_review_packets.json"), trust_capital.get("trust_packets", []))
    _write_json(_path(runtime_root, "capital_readiness_packets.json"), trust_capital.get("capital_packets", []))
    _write_json(_path(runtime_root, "portfolio_learning_snapshot.json"), portfolio_learning)
    _write_json(_path(runtime_root, "portfolio_doctrine_packets.json"), portfolio_learning.get("doctrine_packets", []))
    _write_json(_path(runtime_root, "portfolio_failure_registry.json"), portfolio_learning.get("repeated_failures", []))
    _write_json(_path(runtime_root, "reusable_asset_registry.json"), portfolio_learning.get("reusable_assets", []))
    _write_json(_path(runtime_root, "portfolio_playbook_packets.json"), portfolio_learning.get("playbook_packets", []))
    batch_snapshots = _batch_snapshot(state)
    _write_json(_path(runtime_root, "batch_snapshot.json"), batch_snapshots)
    return {
        "state": state,
        "metrics": metrics,
        "tick": tick,
        "queue_snapshot": queue_snapshot,
        "office_hours": office_hours,
        "decisions": decisions,
        "execution": execution,
        "venture_tasks": venture_tasks,
        "scout": scout,
        "customer_gtm": customer_gtm,
        "trust_capital": trust_capital,
        "portfolio_learning": portfolio_learning,
        "batches": batch_snapshots,
    }


def promote_learning(runtime_root: str) -> dict[str, Any]:
    """Scan retrospectives and assets for promotion-eligible items.

    Writes belief packets and trainer entries to artifacts/beliefs/
    so the Spark summary can report belief_count > 0.
    """
    beliefs_dir = Path(runtime_root) / "artifacts" / "beliefs"
    beliefs_dir.mkdir(parents=True, exist_ok=True)
    trainer_dir = Path(runtime_root) / "artifacts" / "trainer"
    trainer_dir.mkdir(parents=True, exist_ok=True)

    retrospectives = _read_jsonl(log_path(runtime_root, "portfolio_retrospectives"))
    reusable_assets = _read_jsonl(log_path(runtime_root, "reusable_assets"))

    promoted_beliefs: list[dict[str, Any]] = []
    promoted_trainers: list[dict[str, Any]] = []

    # Promote retrospectives with promote_doctrine=true and evidence >= moderate
    for retro in retrospectives:
        if not retro.get("promote_doctrine"):
            continue
        strength = str(retro.get("evidence_strength") or "low")
        if strength not in ("medium", "high"):
            continue
        claim = str(retro.get("doctrine_claim") or "").strip()
        if not claim:
            continue
        belief_id = _slug(str(retro.get("retrospective_id") or "belief"))
        belief = {
            "belief_id": belief_id,
            "belief_status": "candidate_doctrine",
            "claim": claim,
            "mechanism": str(retro.get("lesson") or ""),
            "boundary": str(retro.get("boundary") or ""),
            "evidence_strength": strength,
            "source_venture_id": str(retro.get("venture_id") or ""),
            "source_scope": str(retro.get("scope") or ""),
            "promoted_at": _now_iso(),
        }
        belief_path = beliefs_dir / f"{belief_id}.json"
        if not belief_path.exists():
            _write_json(belief_path, belief)
            promoted_beliefs.append(belief)

    # Promote reusable assets with reused_by_count >= 2 as trainer entries
    seen_assets: dict[str, dict[str, Any]] = {}
    for asset in reusable_assets:
        asset_id = str(asset.get("asset_id") or "")
        if asset_id:
            seen_assets[asset_id] = asset
    for asset_id, asset in seen_assets.items():
        if int(asset.get("reused_by_count", 0) or 0) < 2:
            continue
        trainer_id = _slug(asset_id)
        trainer = {
            "trainer_id": trainer_id,
            "label": str(asset.get("label") or asset_id),
            "kind": str(asset.get("kind") or "playbook"),
            "reused_by_count": int(asset.get("reused_by_count", 0) or 0),
            "source_venture_id": str(asset.get("venture_id") or ""),
            "promoted_at": _now_iso(),
        }
        trainer_path = trainer_dir / f"{trainer_id}.json"
        if not trainer_path.exists():
            _write_json(trainer_path, trainer)
            promoted_trainers.append(trainer)

    # Count totals
    belief_count = len(list(beliefs_dir.glob("*.json")))
    trainer_count = len(list(trainer_dir.glob("*.json")))

    summary = {
        "belief_count": belief_count,
        "trainer_count": trainer_count,
        "newly_promoted_beliefs": len(promoted_beliefs),
        "newly_promoted_trainers": len(promoted_trainers),
        "promoted_beliefs": promoted_beliefs,
        "promoted_trainers": promoted_trainers,
    }
    _write_json(_path(runtime_root, "learning_promotion_summary.json"), summary)
    return summary


def evaluate_ops(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_root = str(payload.get("runtime_root") or "")
    mutations = {
        str(key): str(value)
        for key, value in ((payload.get("candidate", {}) if isinstance(payload.get("candidate"), dict) else {}).get("mutations", {}) or {}).items()
    }
    policy = _policy(mutations)
    with ops_write_lock(runtime_root):
        refreshed = refresh_ops_artifacts(runtime_root, policy=policy)
    metrics = refreshed["metrics"]
    lesson = {
        "portfolio_focus_gap": "The incubator is carrying more active motion than the current operating loop can review honestly.",
        "automation_gap": "Repeated work is still trapped in human effort instead of templates, agents, or shared internal tools.",
        "review_hygiene_gap": "Weekly updates and office-hours rhythm are not fresh enough to support a self-running batch.",
        "validation_gap": "The program is shipping motion faster than it is creating paid or binding customer proof.",
        "trust_gap": "Trust review is too weak for the current venture mix.",
        "knowledge_capture_gap": "The program is learning, but not storing that learning in reusable portfolio form.",
    }[str(metrics["bottleneck"])]
    next_step = {
        "portfolio_focus_gap": "shrink_active_portfolio",
        "automation_gap": "template_repeated_ops",
        "review_hygiene_gap": "tighten_weekly_cadence",
        "validation_gap": "force_paid_validation",
        "trust_gap": "raise_trust_gate",
        "knowledge_capture_gap": "capture_doctrine_every_review",
    }[str(metrics["bottleneck"])]
    result = {
        **metrics,
        "verdict": "steady" if metrics["incubator_compound_score"] >= 0.76 and metrics["ops_trust_hygiene_score"] >= 0.68 else "attention",
        "promotion_status": "operational_candidate",
        "evidence_lane": "state_snapshot",
        "comparison_class": "ops_heuristic_frontier",
        "recommended_next_step": next_step,
        "claim": "The incubator becomes self-running only when portfolio focus, review hygiene, validation pressure, and trust discipline are all visible and bounded.",
        "mechanism": "This ops loop turns incubator management into explicit queues, office-hours packets, decision packets, and repeatable weekly review pressure.",
        "boundary": "This is an agentic control-plane scaffold. It improves operational visibility, not legal judgment or final founder selection authority.",
        "lesson": lesson,
        "next_probe": "Run the ops loop weekly and tighten the weakest surface before expanding the portfolio.",
        "label": "Incubator ops autoloop",
    }
    stdout = "\n".join(
        [
            f"incubator_compound_score: {result['incubator_compound_score']}",
            f"ops_portfolio_focus_score: {result['ops_portfolio_focus_score']}",
            f"ops_automation_coverage_score: {result['ops_automation_coverage_score']}",
            f"ops_review_hygiene_score: {result['ops_review_hygiene_score']}",
            f"ops_validation_velocity_score: {result['ops_validation_velocity_score']}",
            f"ops_trust_hygiene_score: {result['ops_trust_hygiene_score']}",
            f"ops_knowledge_capture_score: {result['ops_knowledge_capture_score']}",
            f"verdict_confidence: {result['verdict_confidence']}",
        ]
    )
    metrics_payload = {
        key: result[key]
        for key in (
            "incubator_compound_score",
            "ops_portfolio_focus_score",
            "ops_automation_coverage_score",
            "ops_review_hygiene_score",
            "ops_validation_velocity_score",
            "ops_trust_hygiene_score",
            "ops_knowledge_capture_score",
            "verdict_confidence",
        )
    }
    return {"returncode": 0, "stdout": stdout, "stderr": "", "metrics": metrics_payload, "result": result}


def suggest_ops(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_root = str(payload.get("runtime_root") or "")
    latest = _latest_tick(runtime_root)
    priorities = latest.get("priority_ventures", []) if isinstance(latest.get("priority_ventures"), list) else []
    limit = max(1, int(payload.get("limit", 4) or 4))
    existing = {
        _signature({str(key): str(value) for key, value in item.get("mutations", {}).items()})
        for item in payload.get("candidate_trials", [])
        if isinstance(item, dict) and isinstance(item.get("mutations"), dict)
    }
    seeds = [
        {
            "candidate_id": "ops-tight-three-lane",
            "candidate_summary": "Three-lane portfolio with weekly review, template-first build routing, strict weekly doctrine capture, and after-validation capital gating.",
            "hypothesis": "A small active portfolio with tight review rhythm compounds better than a broad, impressive-looking batch.",
            "mutations": {
                "portfolio_cap": "3",
                "review_cadence": "weekly",
                "admissions_mode": "thesis_gate",
                "build_routing": "template_first",
                "validation_pressure": "paid_every_week",
                "trust_gate": "balanced",
                "capital_mode": "after_validation",
                "knowledge_capture": "every_review",
                "founder_update_sla": "48h",
            },
        },
        {
            "candidate_id": "ops-two-lane-trust-first",
            "candidate_summary": "Two active ventures, twice-weekly review, manual admissions gate, and strict trust posture for sensitive startup operations.",
            "hypothesis": "When resilience and reputation matter, tighter capacity and stricter trust gating beat batch size.",
            "mutations": {
                "portfolio_cap": "2",
                "review_cadence": "twice_weekly",
                "admissions_mode": "manual_gate",
                "build_routing": "template_first",
                "validation_pressure": "design_partner_first",
                "trust_gate": "strict",
                "capital_mode": "after_validation",
                "knowledge_capture": "every_review",
                "founder_update_sla": "24h",
            },
        },
        {
            "candidate_id": "ops-validation-sprint",
            "candidate_summary": "Validation-first weekly cadence with agent workflows, thesis-gated admissions, and every-review knowledge capture.",
            "hypothesis": "The incubator should optimize for customer proof before investor choreography or platform expansion.",
            "mutations": {
                "portfolio_cap": "3",
                "review_cadence": "weekly",
                "admissions_mode": "thesis_gate",
                "build_routing": "agent_workflows",
                "validation_pressure": "paid_every_week",
                "trust_gate": "balanced",
                "capital_mode": "off",
                "knowledge_capture": "every_review",
                "founder_update_sla": "24h",
            },
        },
    ]
    suggestions = [item for item in seeds if _signature(item["mutations"]) not in existing]
    reasons = ["Use ops candidates to tighten the incubator's weekly operating rhythm instead of opening random new startup lanes."]
    if priorities:
        top = priorities[0]
        repair = {
            "portfolio_focus_gap": {"portfolio_cap": "2", "capital_mode": "off"},
            "automation_gap": {"build_routing": "template_first", "knowledge_capture": "every_review"},
            "review_hygiene_gap": {"review_cadence": "daily", "founder_update_sla": "24h"},
            "validation_gap": {"validation_pressure": "paid_every_week", "capital_mode": "off"},
            "trust_gap": {"trust_gate": "strict", "admissions_mode": "manual_gate"},
            "knowledge_capture_gap": {"knowledge_capture": "every_review", "review_cadence": "weekly"},
        }.get(str((latest.get("metrics") or {}).get("bottleneck", "")), {"portfolio_cap": "3"})
        suggestions.append(
            {
                "candidate_id": f"ops-repair-{_slug(str(top.get('venture_id') or 'priority'))}",
                "candidate_summary": f"Repair the current ops bottleneck around {top.get('label', top.get('venture_id', 'the top venture'))} before opening more lanes.",
                "hypothesis": "The strongest next move is usually to repair the bottleneck in the live operating loop, not widen the incubator.",
                "mutations": {**DEFAULT_POLICY, **repair},
            }
        )
        reasons.append(f"Current priority venture is `{top.get('venture_id')}` with bottleneck `{top.get('bottleneck')}`.")
    return {"baseline_metric": (latest.get("metrics") or {}).get("incubator_compound_score"), "reasons": reasons[:limit], "suggestions": suggestions[:limit]}


def ops_packet_documents(runtime_root: str) -> list[dict[str, Any]]:
    latest = _latest_tick(runtime_root)
    if not latest:
        return []
    metrics = latest.get("metrics", {}) if isinstance(latest.get("metrics"), dict) else {}
    policy = latest.get("policy", {}) if isinstance(latest.get("policy"), dict) else {}
    execution = _read_json(_path(runtime_root, "execution_snapshot.json")) if _path(runtime_root, "execution_snapshot.json").exists() else {}
    scout = _read_json(_path(runtime_root, "scout_snapshot.json")) if _path(runtime_root, "scout_snapshot.json").exists() else {}
    customer_gtm = _read_json(_path(runtime_root, "customer_gtm_snapshot.json")) if _path(runtime_root, "customer_gtm_snapshot.json").exists() else {}
    trust_capital = _read_json(_path(runtime_root, "trust_capital_snapshot.json")) if _path(runtime_root, "trust_capital_snapshot.json").exists() else {}
    portfolio_learning = _read_json(_path(runtime_root, "portfolio_learning_snapshot.json")) if _path(runtime_root, "portfolio_learning_snapshot.json").exists() else {}
    return [
        {
            "kind": "ops_snapshot",
            "memory_tier": "state_snapshot",
            "slug": "vibe-incubator-ops-latest",
            "title": "Vibe Incubator Ops Snapshot",
            "content": "\n".join(
                [
                    "# Vibe Incubator Ops Snapshot",
                    "",
                    f"- generated_at: `{latest.get('generated_at', 'n/a')}`",
                    f"- incubator_compound_score: `{metrics.get('incubator_compound_score', 'n/a')}`",
                    f"- ops_portfolio_focus_score: `{metrics.get('ops_portfolio_focus_score', 'n/a')}`",
                    f"- ops_validation_velocity_score: `{metrics.get('ops_validation_velocity_score', 'n/a')}`",
                    f"- ops_trust_hygiene_score: `{metrics.get('ops_trust_hygiene_score', 'n/a')}`",
                    f"- open_build_request_count: `{execution.get('open_build_request_count', 'n/a')}`",
                    f"- active_experiment_count: `{execution.get('active_experiment_count', 'n/a')}`",
                    f"- stale_kpi_ventures: `{len(execution.get('stale_kpi_ventures', []))}`",
                    f"- pending_application_count: `{scout.get('pending_count', 'n/a')}`",
                    f"- customer_conversation_count: `{customer_gtm.get('conversation_count', 'n/a')}`",
                    f"- open_pipeline_count: `{customer_gtm.get('open_pipeline_count', 'n/a')}`",
                    f"- open_pipeline_value: `{customer_gtm.get('open_pipeline_value', 'n/a')}`",
                    f"- blocking_trust_count: `{trust_capital.get('blocking_trust_count', 'n/a')}`",
                    f"- capital_ready_count: `{trust_capital.get('capital_ready_count', 'n/a')}`",
                    f"- investor_target_count: `{trust_capital.get('investor_target_count', 'n/a')}`",
                    f"- portfolio_retrospective_count: `{portfolio_learning.get('retrospective_count', 'n/a')}`",
                    f"- promoted_playbook_count: `{portfolio_learning.get('promoted_playbook_count', 'n/a')}`",
                    f"- reusable_asset_count: `{portfolio_learning.get('reusable_asset_count', 'n/a')}`",
                    f"- repeated_failure_count: `{portfolio_learning.get('repeated_failure_count', 'n/a')}`",
                    "",
                    "## Policy",
                    "",
                    *[f"- {key}: `{value}`" for key, value in sorted(policy.items())],
                ]
            ),
        }
    ]


def ops_watchtower_pages(runtime_root: str) -> list[dict[str, Any]]:
    latest = _latest_tick(runtime_root)
    if not latest:
        return []
    state = load_state(runtime_root)
    queue_snapshot = _read_json(_path(runtime_root, "queue_snapshot.json")) if _path(runtime_root, "queue_snapshot.json").exists() else {}
    office_hours = _read_json(_path(runtime_root, "office_hours_packets.json")) if _path(runtime_root, "office_hours_packets.json").exists() else []
    execution = _read_json(_path(runtime_root, "execution_snapshot.json")) if _path(runtime_root, "execution_snapshot.json").exists() else {}
    venture_tasks = _read_json(_path(runtime_root, "venture_task_packets.json")) if _path(runtime_root, "venture_task_packets.json").exists() else []
    scout = _read_json(_path(runtime_root, "scout_snapshot.json")) if _path(runtime_root, "scout_snapshot.json").exists() else {}
    admissions_packets = _read_json(_path(runtime_root, "admissions_packets.json")) if _path(runtime_root, "admissions_packets.json").exists() else []
    customer_gtm = _read_json(_path(runtime_root, "customer_gtm_snapshot.json")) if _path(runtime_root, "customer_gtm_snapshot.json").exists() else {}
    customer_signal_packets = _read_json(_path(runtime_root, "customer_signal_packets.json")) if _path(runtime_root, "customer_signal_packets.json").exists() else []
    pipeline_board = _read_json(_path(runtime_root, "pipeline_board.json")) if _path(runtime_root, "pipeline_board.json").exists() else []
    trust_capital = _read_json(_path(runtime_root, "trust_capital_snapshot.json")) if _path(runtime_root, "trust_capital_snapshot.json").exists() else {}
    trust_packets = _read_json(_path(runtime_root, "trust_review_packets.json")) if _path(runtime_root, "trust_review_packets.json").exists() else []
    capital_packets = _read_json(_path(runtime_root, "capital_readiness_packets.json")) if _path(runtime_root, "capital_readiness_packets.json").exists() else []
    portfolio_learning = _read_json(_path(runtime_root, "portfolio_learning_snapshot.json")) if _path(runtime_root, "portfolio_learning_snapshot.json").exists() else {}
    doctrine_packets = _read_json(_path(runtime_root, "portfolio_doctrine_packets.json")) if _path(runtime_root, "portfolio_doctrine_packets.json").exists() else []
    failure_registry = _read_json(_path(runtime_root, "portfolio_failure_registry.json")) if _path(runtime_root, "portfolio_failure_registry.json").exists() else []
    reusable_assets = _read_json(_path(runtime_root, "reusable_asset_registry.json")) if _path(runtime_root, "reusable_asset_registry.json").exists() else []
    playbook_packets = _read_json(_path(runtime_root, "portfolio_playbook_packets.json")) if _path(runtime_root, "portfolio_playbook_packets.json").exists() else []
    admissions = read_log(runtime_root, "admissions")
    reviews = read_log(runtime_root, "reviews")
    updates = read_log(runtime_root, "weekly_updates")
    experiments = read_log(runtime_root, "experiments")
    build_requests = read_log(runtime_root, "build_requests")
    kpi_snapshots = read_log(runtime_root, "kpi_snapshots")
    scout_applications = read_log(runtime_root, "scout_applications")
    admission_reviews = read_log(runtime_root, "admission_reviews")
    customer_conversations = read_log(runtime_root, "customer_conversations")
    pipeline_opportunities = read_log(runtime_root, "pipeline_opportunities")
    trust_reviews = read_log(runtime_root, "trust_reviews")
    data_room_items = read_log(runtime_root, "data_room_items")
    investor_targets = read_log(runtime_root, "investor_targets")
    portfolio_retrospectives = read_log(runtime_root, "portfolio_retrospectives")
    reusable_asset_events = read_log(runtime_root, "reusable_assets")
    metrics = latest.get("metrics", {}) if isinstance(latest.get("metrics"), dict) else {}
    policy = latest.get("policy", {}) if isinstance(latest.get("policy"), dict) else {}
    lines = [
        "# Ops Flywheel",
        "",
        f"- latest_tick: `{latest.get('generated_at', 'n/a')}`",
        f"- incubator_compound_score: `{metrics.get('incubator_compound_score', 'n/a')}`",
        f"- active_portfolio_count: `{metrics.get('active_portfolio_count', 'n/a')}`",
        f"- portfolio_cap: `{metrics.get('portfolio_cap', 'n/a')}`",
        f"- bottleneck: `{metrics.get('bottleneck', 'n/a')}`",
        "",
        "## Policy",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in sorted(policy.items()))
    queue_lines = [
        "# Ops Queue",
        "",
        f"- generated_at: `{queue_snapshot.get('generated_at', 'n/a')}`",
        "",
        "## Priority Ventures",
        "",
    ]
    for item in queue_snapshot.get("priority_ventures", [])[:5]:
        queue_lines.extend(
            [
                f"### {item.get('label', item.get('venture_id', 'venture'))}",
                "",
                f"- venture_id: `{item.get('venture_id', 'n/a')}`",
                f"- bottleneck: `{item.get('bottleneck', 'n/a')}`",
                f"- next_action: `{item.get('next_action', 'n/a')}`",
                f"- priority: `{item.get('priority', 'n/a')}`",
                "",
            ]
        )
    office_lines = ["# Office Hours Packets", ""]
    for item in office_hours[:5]:
        office_lines.extend(
            [
                f"## {item.get('label', item.get('venture_id', 'venture'))}",
                "",
                *[f"- {entry}" for entry in item.get("agenda", [])],
                f"- commitment: `{item.get('commitment', 'n/a')}`",
                "",
            ]
        )
    scout_lines = [
        "# Scout Intake",
        "",
        f"- generated_at: `{scout.get('generated_at', 'n/a')}`",
        f"- applications: `{scout.get('application_count', 0)}`",
        f"- pending: `{scout.get('pending_count', 0)}`",
        f"- admitted: `{scout.get('admitted_count', 0)}`",
        f"- rejected: `{scout.get('rejected_count', 0)}`",
        f"- scout_applications_logged: `{len(scout_applications)}`",
        f"- admission_reviews_logged: `{len(admission_reviews)}`",
        "",
        "## Latest Candidates",
        "",
    ]
    for item in scout.get("applications", [])[:5]:
        scout_lines.extend(
            [
                f"### {item.get('label', item.get('application_id', 'application'))}",
                "",
                f"- application_id: `{item.get('application_id', 'n/a')}`",
                f"- founder: `{item.get('founder_label', item.get('founder_id', 'n/a'))}`",
                f"- entry_source: `{item.get('entry_source', 'n/a')}`",
                f"- incubator_compound_score: `{item.get('incubator_compound_score', 'n/a')}`",
                f"- recommended_decision: `{item.get('recommended_decision', 'n/a')}`",
                f"- status: `{item.get('status', 'n/a')}`",
                f"- recommended_next_step: `{item.get('recommended_next_step', 'n/a')}`",
                "",
            ]
        )
    admissions_lines = ["# Admissions Queue", ""]
    for item in admissions_packets[:5]:
        admissions_lines.extend(
            [
                f"## {item.get('label', item.get('application_id', 'application'))}",
                "",
                f"- application_id: `{item.get('application_id', 'n/a')}`",
                f"- founder: `{item.get('founder_label', 'n/a')}`",
                f"- entry_source: `{item.get('entry_source', 'n/a')}`",
                f"- incubator_compound_score: `{item.get('incubator_compound_score', 'n/a')}`",
                f"- recommended_decision: `{item.get('recommended_decision', 'n/a')}`",
                f"- manual_review_required: `{item.get('manual_review_required', 'n/a')}`",
                f"- recommended_next_step: `{item.get('recommended_next_step', 'n/a')}`",
                *[f"- first_week_plan: {entry}" for entry in item.get("first_week_plan", [])],
                "",
            ]
        )
    customer_lines = [
        "# Customer Signals",
        "",
        f"- generated_at: `{customer_gtm.get('generated_at', 'n/a')}`",
        f"- conversation_count: `{customer_gtm.get('conversation_count', 0)}`",
        f"- willingness_signal_count: `{customer_gtm.get('willingness_signal_count', 0)}`",
        f"- customer_conversations_logged: `{len(customer_conversations)}`",
        "",
    ]
    for item in customer_signal_packets[:5]:
        customer_lines.extend(
            [
                f"## {item.get('label', item.get('venture_id', 'venture'))}",
                "",
                f"- venture_id: `{item.get('venture_id', 'n/a')}`",
                f"- conversation_count: `{item.get('conversation_count', 'n/a')}`",
                f"- willingness_signal_count: `{item.get('willingness_signal_count', 'n/a')}`",
                *[f"- top_objection: `{entry}`" for entry in item.get("top_objections", [])],
                *[f"- gtm_task: `{entry}`" for entry in item.get("gtm_tasks", [])],
                "",
            ]
        )
    pipeline_lines = [
        "# Pipeline Board",
        "",
        f"- generated_at: `{customer_gtm.get('generated_at', 'n/a')}`",
        f"- open_pipeline_count: `{customer_gtm.get('open_pipeline_count', 0)}`",
        f"- open_pipeline_value: `{customer_gtm.get('open_pipeline_value', 0)}`",
        f"- pipeline_opportunities_logged: `{len(pipeline_opportunities)}`",
        "",
    ]
    for item in pipeline_board[:5]:
        pipeline_lines.extend(
            [
                f"## {item.get('label', item.get('venture_id', 'venture'))}",
                "",
                f"- venture_id: `{item.get('venture_id', 'n/a')}`",
                f"- open_pipeline_count: `{item.get('open_pipeline_count', 'n/a')}`",
                f"- open_pipeline_value: `{item.get('open_pipeline_value', 'n/a')}`",
                "",
            ]
        )
        for opportunity in item.get("opportunities", [])[:3]:
            pipeline_lines.extend(
                [
                    f"- opportunity: `{opportunity.get('customer_label', opportunity.get('opportunity_id', 'opportunity'))}`",
                    f"- stage: `{opportunity.get('stage', 'n/a')}`",
                    f"- value: `{opportunity.get('value', 'n/a')}`",
                    f"- confidence: `{opportunity.get('confidence', 'n/a')}`",
                ]
        )
        pipeline_lines.append("")
    trust_lines = [
        "# Trust Board",
        "",
        f"- generated_at: `{trust_capital.get('generated_at', 'n/a')}`",
        f"- blocking_trust_count: `{trust_capital.get('blocking_trust_count', 0)}`",
        f"- trust_reviews_logged: `{len(trust_reviews)}`",
        f"- data_room_items_logged: `{len(data_room_items)}`",
        "",
    ]
    for item in trust_packets[:5]:
        trust_lines.extend(
            [
                f"## {item.get('label', item.get('venture_id', 'venture'))}",
                "",
                f"- venture_id: `{item.get('venture_id', 'n/a')}`",
                f"- trust_status: `{item.get('trust_status', 'n/a')}`",
                f"- risk_area: `{item.get('risk_area', 'n/a')}`",
                f"- blocking: `{item.get('blocking', 'n/a')}`",
                f"- next_step: `{item.get('next_step', 'n/a')}`",
                "",
            ]
        )
    capital_lines = [
        "# Capital Readiness",
        "",
        f"- generated_at: `{trust_capital.get('generated_at', 'n/a')}`",
        f"- capital_ready_count: `{trust_capital.get('capital_ready_count', 0)}`",
        f"- investor_target_count: `{trust_capital.get('investor_target_count', 0)}`",
        f"- investor_targets_logged: `{len(investor_targets)}`",
        "",
    ]
    for item in capital_packets[:5]:
        capital_lines.extend(
            [
                f"## {item.get('label', item.get('venture_id', 'venture'))}",
                "",
                f"- venture_id: `{item.get('venture_id', 'n/a')}`",
                f"- capital_readiness: `{item.get('capital_readiness', 'n/a')}`",
                f"- ready_data_room_count: `{item.get('ready_data_room_count', 'n/a')}`",
                f"- total_data_room_count: `{item.get('total_data_room_count', 'n/a')}`",
                f"- open_investor_count: `{item.get('open_investor_count', 'n/a')}`",
                f"- interested_investor_count: `{item.get('interested_investor_count', 'n/a')}`",
                f"- brief_claim: {item.get('brief_claim', 'n/a')}",
                *[f"- capital_task: `{entry}`" for entry in item.get("capital_tasks", [])],
                "",
            ]
        )
    learning_lines = [
        "# Portfolio Learning",
        "",
        f"- generated_at: `{portfolio_learning.get('generated_at', 'n/a')}`",
        f"- retrospective_count: `{portfolio_learning.get('retrospective_count', 0)}`",
        f"- promoted_playbook_count: `{portfolio_learning.get('promoted_playbook_count', 0)}`",
        f"- doctrine_packet_count: `{portfolio_learning.get('doctrine_packet_count', 0)}`",
        f"- reusable_asset_count: `{portfolio_learning.get('reusable_asset_count', 0)}`",
        f"- repeated_failure_count: `{portfolio_learning.get('repeated_failure_count', 0)}`",
        f"- portfolio_retrospectives_logged: `{len(portfolio_retrospectives)}`",
        "",
    ]
    for item in playbook_packets[:5]:
        learning_lines.extend(
            [
                f"## {item.get('label', item.get('venture_id', 'venture'))}",
                "",
                f"- venture_id: `{item.get('venture_id', 'n/a')}`",
                f"- promoted_playbook_count: `{item.get('promoted_playbook_count', 'n/a')}`",
                f"- doctrine_ready: `{item.get('doctrine_ready', 'n/a')}`",
                f"- evidence_strength: `{item.get('evidence_strength', 'n/a')}`",
                f"- top_claim: {item.get('top_claim', 'n/a')}",
                f"- boundary: {item.get('boundary', 'n/a')}",
                f"- next_step: `{item.get('next_step', 'n/a')}`",
                "",
            ]
        )
    if not playbook_packets:
        learning_lines.extend(["No doctrine-ready portfolio playbooks yet.", ""])
    elif doctrine_packets:
        learning_lines.extend(["## Doctrine Candidates", ""])
        for item in doctrine_packets[:5]:
            learning_lines.extend(
                [
                    f"### {item.get('label', item.get('venture_id', 'venture'))}",
                    "",
                    f"- doctrine_claim: {item.get('doctrine_claim', 'n/a')}",
                    f"- scope: `{item.get('scope', 'n/a')}`",
                    f"- outcome: `{item.get('outcome', 'n/a')}`",
                    f"- evidence_strength: `{item.get('evidence_strength', 'n/a')}`",
                    f"- boundary: {item.get('boundary', 'n/a')}",
                    "",
                ]
            )
    asset_lines = [
        "# Reusable Assets",
        "",
        f"- generated_at: `{portfolio_learning.get('generated_at', 'n/a')}`",
        f"- reusable_asset_count: `{portfolio_learning.get('reusable_asset_count', 0)}`",
        f"- reusable_asset_events_logged: `{len(reusable_asset_events)}`",
        "",
    ]
    for item in reusable_assets[:8]:
        asset_lines.extend(
            [
                f"## {item.get('label', item.get('asset_id', 'asset'))}",
                "",
                f"- asset_id: `{item.get('asset_id', 'n/a')}`",
                f"- venture_id: `{item.get('venture_id', 'n/a')}`",
                f"- kind: `{item.get('kind', 'n/a')}`",
                f"- status: `{item.get('status', 'n/a')}`",
                f"- reused_by_count: `{item.get('reused_by_count', 'n/a')}`",
                f"- shared_surface: `{item.get('shared_surface', 'n/a')}`",
                f"- next_step: `{item.get('next_step', 'n/a')}`",
                "",
            ]
        )
    if not reusable_assets:
        asset_lines.extend(["No reusable assets captured yet.", ""])
    failure_lines = [
        "# Failure Registry",
        "",
        f"- generated_at: `{portfolio_learning.get('generated_at', 'n/a')}`",
        f"- repeated_failure_count: `{portfolio_learning.get('repeated_failure_count', 0)}`",
        "",
    ]
    for item in failure_registry[:8]:
        failure_lines.extend(
            [
                f"## {item.get('failure_mode', 'failure')}",
                "",
                f"- count: `{item.get('count', 'n/a')}`",
                f"- venture_count: `{item.get('venture_count', 'n/a')}`",
                *[f"- venture: `{entry}`" for entry in item.get('ventures', [])],
                f"- recommended_boundary: {item.get('recommended_boundary', 'n/a')}",
                "",
            ]
        )
    if not failure_registry:
        failure_lines.extend(["No repeated failures have cleared the registry threshold yet.", ""])
    execution_lines = [
        "# Execution Board",
        "",
        f"- generated_at: `{execution.get('generated_at', 'n/a')}`",
        f"- active_experiment_count: `{execution.get('active_experiment_count', 'n/a')}`",
        f"- open_build_request_count: `{execution.get('open_build_request_count', 'n/a')}`",
        f"- stale_kpi_count: `{len(execution.get('stale_kpi_ventures', []))}`",
        f"- experiments_logged: `{len(experiments)}`",
        f"- build_requests_logged: `{len(build_requests)}`",
        f"- kpi_snapshots_logged: `{len(kpi_snapshots)}`",
        "",
        "## Venture Execution",
        "",
    ]
    for item in execution.get("ventures", [])[:5]:
        latest_kpi = item.get("latest_kpi_snapshot", {}) if isinstance(item.get("latest_kpi_snapshot"), dict) else {}
        execution_lines.extend(
            [
                f"### {item.get('label', item.get('venture_id', 'venture'))}",
                "",
                f"- venture_id: `{item.get('venture_id', 'n/a')}`",
                f"- active_experiment_count: `{item.get('active_experiment_count', 'n/a')}`",
                f"- open_build_request_count: `{item.get('open_build_request_count', 'n/a')}`",
                f"- latest_weekly_revenue: `{latest_kpi.get('weekly_revenue', 'n/a')}`",
                f"- latest_pipeline_count: `{latest_kpi.get('pipeline_count', 'n/a')}`",
                f"- latest_active_users: `{latest_kpi.get('active_users', 'n/a')}`",
                "",
            ]
        )
    task_lines = ["# Venture Task Packets", ""]
    for item in venture_tasks[:5]:
        task_lines.extend(
            [
                f"## {item.get('label', item.get('venture_id', 'venture'))}",
                "",
                f"- venture_id: `{item.get('venture_id', 'n/a')}`",
                f"- bottleneck: `{item.get('bottleneck', 'n/a')}`",
                f"- next_action: `{item.get('next_action', 'n/a')}`",
                f"- active_experiment_count: `{item.get('active_experiment_count', 'n/a')}`",
                f"- open_build_request_count: `{item.get('open_build_request_count', 'n/a')}`",
                f"- customer_signal_count: `{item.get('customer_signal_count', 'n/a')}`",
                f"- open_pipeline_count: `{item.get('open_pipeline_count', 'n/a')}`",
                f"- open_pipeline_value: `{item.get('open_pipeline_value', 'n/a')}`",
                f"- trust_status: `{item.get('trust_status', 'n/a')}`",
                f"- capital_readiness: `{item.get('capital_readiness', 'n/a')}`",
                f"- ready_data_room_count: `{item.get('ready_data_room_count', 'n/a')}`",
                f"- investor_target_count: `{item.get('investor_target_count', 'n/a')}`",
                f"- portfolio_retrospective_count: `{item.get('portfolio_retrospective_count', 'n/a')}`",
                f"- promoted_playbook_count: `{item.get('promoted_playbook_count', 'n/a')}`",
                f"- reusable_asset_count: `{item.get('reusable_asset_count', 'n/a')}`",
                f"- doctrine_ready: `{item.get('doctrine_ready', 'n/a')}`",
                f"- latest_weekly_revenue: `{item.get('latest_weekly_revenue', 'n/a')}`",
                *[f"- top_objection: `{entry}`" for entry in item.get("top_objections", [])],
                *[f"- task: `{entry}`" for entry in item.get("required_tasks", [])],
                "",
            ]
        )
    program_lines = [
        "# Program State",
        "",
        f"- updated_at: `{state.get('updated_at', state.get('generated_at', 'n/a'))}`",
        f"- founder_count: `{len(state.get('founders', []))}`",
        f"- venture_count: `{len(state.get('ventures', []))}`",
        f"- admissions_events: `{len(admissions)}`",
        f"- weekly_updates: `{len(updates)}`",
        f"- reviews: `{len(reviews)}`",
        "",
        "## Active Ventures",
        "",
    ]
    for item in state.get("ventures", []):
        if not isinstance(item, dict) or str(item.get("status") or "") in {"archived", "stopped"}:
            continue
        program_lines.extend(
            [
                f"### {item.get('label', item.get('venture_id', 'venture'))}",
                "",
                f"- venture_id: `{item.get('venture_id', 'n/a')}`",
                f"- stage: `{item.get('stage', 'n/a')}`",
                f"- bottleneck: `{item.get('bottleneck', 'n/a')}`",
                f"- trust: `{item.get('trust_review_status', 'n/a')}`",
                f"- paid_signals_this_week: `{item.get('paid_signals_this_week', 'n/a')}`",
                f"- customer_conversations_this_week: `{item.get('customer_conversations_this_week', 'n/a')}`",
                f"- build_backlog_count: `{item.get('build_backlog_count', 'n/a')}`",
                "",
            ]
        )
    decision_lines = [
        "# Decision Log",
        "",
        "## Recent Reviews",
        "",
    ]
    for item in list(reversed(reviews[-8:])):
        decision_lines.extend(
            [
                f"### {item.get('venture_id', 'venture')}",
                "",
                f"- created_at: `{item.get('created_at', 'n/a')}`",
                f"- decision: `{item.get('decision', 'n/a')}`",
                f"- bottleneck: `{item.get('bottleneck', 'n/a')}`",
                f"- next_step: `{item.get('next_step', 'n/a')}`",
                f"- note: {item.get('note', 'n/a')}",
                "",
            ]
        )
    if not reviews:
        decision_lines.append("No explicit review decisions yet.")
        decision_lines.append("")
    if admissions:
        decision_lines.extend(["## Recent Admissions", ""])
        for item in list(reversed(admissions[-5:])):
            decision_lines.extend(
                [
                    f"- `{item.get('venture_id', 'venture')}` admitted for founder `{item.get('founder_id', 'n/a')}` at `{item.get('created_at', 'n/a')}`",
                ]
            )
    return [
        {"path": "07-Domains/Vibe Incubator/Ops Flywheel.md", "content": "\n".join(lines)},
        {"path": "07-Domains/Vibe Incubator/Ops Queue.md", "content": "\n".join(queue_lines)},
        {"path": "07-Domains/Vibe Incubator/Scout Intake.md", "content": "\n".join(scout_lines)},
        {"path": "07-Domains/Vibe Incubator/Admissions Queue.md", "content": "\n".join(admissions_lines)},
        {"path": "07-Domains/Vibe Incubator/Customer Signals.md", "content": "\n".join(customer_lines)},
        {"path": "07-Domains/Vibe Incubator/Pipeline Board.md", "content": "\n".join(pipeline_lines)},
        {"path": "07-Domains/Vibe Incubator/Trust Board.md", "content": "\n".join(trust_lines)},
        {"path": "07-Domains/Vibe Incubator/Capital Readiness.md", "content": "\n".join(capital_lines)},
        {"path": "07-Domains/Vibe Incubator/Portfolio Learning.md", "content": "\n".join(learning_lines)},
        {"path": "07-Domains/Vibe Incubator/Reusable Assets.md", "content": "\n".join(asset_lines)},
        {"path": "07-Domains/Vibe Incubator/Failure Registry.md", "content": "\n".join(failure_lines)},
        {"path": "07-Domains/Vibe Incubator/Office Hours Packets.md", "content": "\n".join(office_lines)},
        {"path": "07-Domains/Vibe Incubator/Execution Board.md", "content": "\n".join(execution_lines)},
        {"path": "07-Domains/Vibe Incubator/Venture Task Packets.md", "content": "\n".join(task_lines)},
        {"path": "07-Domains/Vibe Incubator/Program State.md", "content": "\n".join(program_lines)},
        {"path": "07-Domains/Vibe Incubator/Decision Log.md", "content": "\n".join(decision_lines)},
    ]
