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
            "micro_batch_style": "rolling",
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


def _build_venture_task_packets(execution: dict[str, Any]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for item in execution.get("ventures", []):
        if not isinstance(item, dict):
            continue
        latest_kpi = item.get("latest_kpi_snapshot", {}) if isinstance(item.get("latest_kpi_snapshot"), dict) else {}
        packets.append(
            {
                "venture_id": str(item.get("venture_id") or "venture"),
                "label": str(item.get("label") or item.get("venture_id") or "venture"),
                "priority": int(item.get("priority", 0) or 0),
                "bottleneck": str(item.get("bottleneck") or "model_gap"),
                "next_action": str(item.get("next_action") or "ship_next_validation_commitment"),
                "required_tasks": [str(task) for task in item.get("required_tasks", [])[:5]],
                "active_experiment_count": int(item.get("active_experiment_count", 0) or 0),
                "open_build_request_count": int(item.get("open_build_request_count", 0) or 0),
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


def _policy(mutations: dict[str, str]) -> dict[str, str]:
    policy = dict(DEFAULT_POLICY)
    for key, value in mutations.items():
        if key in policy and str(value).strip():
            policy[key] = str(value)
    return policy


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
        if stage in {"go_to_market", "capital_readiness"} and paid_signals > 0:
            queues["capital"].append({"venture_id": venture_id, "priority": "medium"})
        if trust != "green":
            queues["trust"].append({"venture_id": venture_id, "priority": "high" if trust == "red" else "medium"})
        if reuse_assets >= 4:
            queues["doctrine"].append({"venture_id": venture_id, "priority": "medium"})
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
    update_freshness = _mean([max(0.0, 1.0 - (float(item.get("weekly_update_freshness_days", 7) or 7) / 7.0)) for item in ventures], 0.35)
    review_freshness = _mean([max(0.0, 1.0 - (float(item.get("last_review_days", 7) or 7) / 7.0)) for item in ventures], 0.35)
    automation_base = _mean([float(item.get("automation_coverage", 0.45) or 0.45) for item in ventures], 0.42)
    validation_base = _mean([min(1.0, (float(item.get("customer_conversations_this_week", 0) or 0) / 4.0) + (float(item.get("paid_signals_this_week", 0) or 0) * 0.2)) for item in ventures], 0.28)
    trust_base = _mean([_trust_score(str(item.get("trust_review_status") or "amber")) for item in ventures], 0.5)
    knowledge_base = _mean([min(1.0, (float(item.get("reuse_assets_count", 0) or 0) / 5.0)) for item in ventures], 0.25)
    queue_penalty = min(0.25, (len(queues.get("build", [])) + len(queues.get("validation", []))) * 0.015)
    focus_base = max(0.0, 0.72 - overload * 0.17 - queue_penalty)
    founder_latency = _mean([max(0.0, 1.0 - (float(item.get("founder_update_latency_hours", 72) or 72) / 72.0)) for item in ventures], 0.4)
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
    state = save_state(runtime_root, state)
    priorities = _venture_priorities(state)
    execution = _execution_snapshot(runtime_root, state, priorities)
    scout = _scout_snapshot(runtime_root)
    metrics = _score_state(state, effective_policy)
    office_hours = _build_office_hours_packets(state, priorities)
    decisions = _build_decision_packets(state, priorities)
    venture_tasks = _build_venture_task_packets(execution)
    queue_snapshot = {
        "generated_at": _now_iso(),
        "portfolio_cap": metrics["portfolio_cap"],
        "active_portfolio_count": metrics["active_portfolio_count"],
        "priority_ventures": priorities[:5],
        "venture_task_count": len(venture_tasks),
        "pending_applications": int(scout.get("pending_count", 0) or 0),
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
    }
    _write_json(_path(runtime_root, "latest_tick.json"), tick)
    _write_json(_path(runtime_root, "queue_snapshot.json"), queue_snapshot)
    _write_json(_path(runtime_root, "office_hours_packets.json"), office_hours)
    _write_json(_path(runtime_root, "decision_packets.json"), decisions)
    _write_json(_path(runtime_root, "execution_snapshot.json"), execution)
    _write_json(_path(runtime_root, "venture_task_packets.json"), venture_tasks)
    _write_json(_path(runtime_root, "scout_snapshot.json"), scout)
    _write_json(_path(runtime_root, "admissions_packets.json"), scout.get("pending_packets", []))
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
    }


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
    admissions = read_log(runtime_root, "admissions")
    reviews = read_log(runtime_root, "reviews")
    updates = read_log(runtime_root, "weekly_updates")
    experiments = read_log(runtime_root, "experiments")
    build_requests = read_log(runtime_root, "build_requests")
    kpi_snapshots = read_log(runtime_root, "kpi_snapshots")
    scout_applications = read_log(runtime_root, "scout_applications")
    admission_reviews = read_log(runtime_root, "admission_reviews")
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
                f"- latest_weekly_revenue: `{item.get('latest_weekly_revenue', 'n/a')}`",
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
        {"path": "07-Domains/Vibe Incubator/Office Hours Packets.md", "content": "\n".join(office_lines)},
        {"path": "07-Domains/Vibe Incubator/Execution Board.md", "content": "\n".join(execution_lines)},
        {"path": "07-Domains/Vibe Incubator/Venture Task Packets.md", "content": "\n".join(task_lines)},
        {"path": "07-Domains/Vibe Incubator/Program State.md", "content": "\n".join(program_lines)},
        {"path": "07-Domains/Vibe Incubator/Decision Log.md", "content": "\n".join(decision_lines)},
    ]
