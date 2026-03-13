from __future__ import annotations

import argparse
import json
from typing import Any

try:
    from .cli import score_venture_candidate
except ImportError:
    from cli import score_venture_candidate

try:
    from .ops_loop import append_log, default_runtime_root, load_state, ops_write_lock, read_log, refresh_ops_artifacts, save_state
except ImportError:
    from ops_loop import append_log, default_runtime_root, load_state, ops_write_lock, read_log, refresh_ops_artifacts, save_state


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return cleaned.strip("-")[:64] or "venture"


def _venture(state: dict[str, Any], venture_id: str) -> dict[str, Any]:
    for item in state.get("ventures", []):
        if isinstance(item, dict) and str(item.get("venture_id") or "") == venture_id:
            return item
    raise RuntimeError(f"Unknown venture_id: {venture_id}")


def _founder(state: dict[str, Any], founder_id: str, founder_label: str | None = None) -> dict[str, Any]:
    founders = state.setdefault("founders", [])
    for item in founders:
        if isinstance(item, dict) and str(item.get("founder_id") or "") == founder_id:
            if founder_label:
                item["label"] = founder_label
            item.setdefault("venture_ids", [])
            return item
    created = {
        "founder_id": founder_id,
        "label": founder_label or founder_id,
        "status": "active",
        "venture_ids": [],
        "response_latency_hours": 12,
    }
    founders.append(created)
    return created


def _queue_counts(state: dict[str, Any]) -> dict[str, int]:
    queues = state.get("queues", {}) if isinstance(state.get("queues"), dict) else {}
    return {name: len(items) for name, items in sorted(queues.items()) if isinstance(items, list)}


def _execution_by_venture(refreshed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    execution = refreshed.get("execution", {}) if isinstance(refreshed.get("execution"), dict) else {}
    return {
        str(item.get("venture_id") or ""): item
        for item in execution.get("ventures", [])
        if isinstance(item, dict) and item.get("venture_id")
    }


def _latest_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = str(row.get(key) or "").strip()
        if value:
            latest[value] = row
    return latest


def _application(runtime_root: str, application_id: str) -> dict[str, Any]:
    latest = _latest_by_key(read_log(runtime_root, "scout_applications"), "application_id")
    if application_id not in latest:
        raise RuntimeError(f"Unknown application_id: {application_id}")
    return latest[application_id]


def _recommended_admission_decision(score: dict[str, Any], trust_risk: str) -> str:
    if str(trust_risk) == "high" or float(score.get("resilience_score", 0.0) or 0.0) < 0.58:
        return "watchlist"
    return {"approve": "invite", "defer": "watchlist", "reject": "reject"}.get(str(score.get("verdict") or "reject"), "watchlist")


def _first_week_plan(score: dict[str, Any]) -> list[str]:
    bottleneck = str(score.get("bottleneck") or "model_gap")
    first = {
        "model_gap": "Narrow the offer and customer pain until one operator plus agents can carry it.",
        "distribution_gap": "Choose one distribution surface and ship a founder-visible proof loop this week.",
        "automation_gap": "Move repeated work into a template, agent, or internal workflow before adding scope.",
        "learning_gap": "Set a weekly review ritual that turns customer signals into reusable doctrine.",
        "revenue_gap": "Run a paid pilot or design-partner ask before building more product surface.",
        "resilience_gap": "Tighten trust review and audit controls before widening access.",
    }[bottleneck]
    return [
        first,
        f"Run `{score.get('recommended_next_step', 'clarify_next_probe')}` as the lead operating move.",
        "Prepare an explicit admissions review with founder fit, trust risk, and the first validation commitment.",
    ]


def _status_payload(runtime_root: str) -> dict[str, Any]:
    with ops_write_lock(runtime_root):
        refreshed = refresh_ops_artifacts(runtime_root)
    state = refreshed["state"]
    tick = refreshed["tick"]
    ventures = [item for item in state.get("ventures", []) if isinstance(item, dict)]
    execution = refreshed.get("execution", {}) if isinstance(refreshed.get("execution"), dict) else {}
    execution_by_venture = _execution_by_venture(refreshed)
    scout = refreshed.get("scout", {}) if isinstance(refreshed.get("scout"), dict) else {}
    return {
        "runtime_root": runtime_root,
        "program": state.get("program", {}),
        "queue_counts": _queue_counts(state),
        "founder_count": len(state.get("founders", [])),
        "venture_count": len(ventures),
        "scouting": {
            "application_count": scout.get("application_count", 0),
            "pending_count": scout.get("pending_count", 0),
            "admitted_count": scout.get("admitted_count", 0),
            "rejected_count": scout.get("rejected_count", 0),
        },
        "execution": {
            "active_experiment_count": execution.get("active_experiment_count", 0),
            "open_build_request_count": execution.get("open_build_request_count", 0),
            "stale_kpi_ventures": execution.get("stale_kpi_ventures", []),
        },
        "active_ventures": [
            {
                "venture_id": item.get("venture_id"),
                "label": item.get("label"),
                "status": item.get("status"),
                "stage": item.get("stage"),
                "bottleneck": item.get("bottleneck"),
                "trust_review_status": item.get("trust_review_status"),
                "paid_signals_this_week": item.get("paid_signals_this_week"),
                "customer_conversations_this_week": item.get("customer_conversations_this_week"),
                "active_experiment_count": execution_by_venture.get(str(item.get("venture_id") or ""), {}).get("active_experiment_count", 0),
                "open_build_request_count": execution_by_venture.get(str(item.get("venture_id") or ""), {}).get("open_build_request_count", 0),
                "latest_weekly_revenue": (
                    execution_by_venture.get(str(item.get("venture_id") or ""), {}).get("latest_kpi_snapshot", {}) or {}
                ).get("weekly_revenue"),
            }
            for item in ventures
            if str(item.get("status") or "") not in {"archived", "stopped"}
        ],
        "latest_tick": {
            "generated_at": tick.get("generated_at"),
            "policy": tick.get("policy", {}),
            "metrics": tick.get("metrics", {}),
        },
    }


def _handle_status(args: argparse.Namespace) -> None:
    _print(_status_payload(args.runtime_root))


def _handle_admit(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture_id = str(args.venture_id)
        if any(str(item.get("venture_id") or "") == venture_id for item in state.get("ventures", []) if isinstance(item, dict)):
            raise RuntimeError(f"venture_id already exists: {venture_id}")
        founder = _founder(state, str(args.founder_id), args.founder_label)
        venture = {
            "venture_id": venture_id,
            "label": str(args.label),
            "status": "active",
            "stage": str(args.stage),
            "bottleneck": str(args.bottleneck),
            "weekly_update_freshness_days": 0,
            "last_review_days": 0,
            "automation_coverage": float(args.automation_coverage),
            "reuse_assets_count": int(args.reuse_assets_count),
            "customer_conversations_this_week": int(args.customer_conversations),
            "paid_signals_this_week": int(args.paid_signals),
            "trust_review_status": str(args.trust_review_status),
            "founder_update_latency_hours": int(args.founder_update_latency_hours),
            "build_backlog_count": int(args.build_backlog_count),
            "decision_status": "continue",
            "venture_model": str(args.venture_model or ""),
            "customer_surface": str(args.customer_surface or ""),
            "distribution_engine": str(args.distribution_engine or ""),
        }
        state.setdefault("ventures", []).append(venture)
        founder.setdefault("venture_ids", [])
        if venture_id not in founder["venture_ids"]:
            founder["venture_ids"].append(venture_id)
        save_state(args.runtime_root, state)
        event = append_log(
            args.runtime_root,
            "admissions",
            {
                "venture_id": venture_id,
                "founder_id": founder["founder_id"],
                "stage": venture["stage"],
                "label": venture["label"],
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_venture = _venture(refreshed["state"], venture_id)
    _print(
        {
            "runtime_root": args.runtime_root,
            "admitted_venture": refreshed_venture,
            "admission_event": event,
            "queue_counts": _queue_counts(refreshed["state"]),
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_scout_intake(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        founder = _founder(state, str(args.founder_id), args.founder_label)
        venture_id = str(args.venture_id or _slug(str(args.label)))
        mutations = {
            "venture_model": str(args.venture_model),
            "customer_surface": str(args.customer_surface),
            "distribution_engine": str(args.distribution_engine),
            "build_stack": str(args.build_stack),
            "validation_motion": str(args.validation_motion),
            "trust_model": str(args.trust_model),
            "operating_cadence": str(args.operating_cadence),
            "venture_theme": str(args.venture_theme),
        }
        score = score_venture_candidate(mutations)
        recommended_decision = _recommended_admission_decision(score, str(args.trust_risk))
        event = append_log(
            args.runtime_root,
            "scout_applications",
            {
                "application_id": str(args.application_id),
                "venture_id": venture_id,
                "founder_id": founder["founder_id"],
                "founder_label": founder.get("label", founder["founder_id"]),
                "label": str(args.label),
                "entry_source": str(args.entry_source),
                "thesis_summary": str(args.thesis_summary or ""),
                "trust_risk": str(args.trust_risk),
                "venture_model": mutations["venture_model"],
                "customer_surface": mutations["customer_surface"],
                "distribution_engine": mutations["distribution_engine"],
                "build_stack": mutations["build_stack"],
                "validation_motion": mutations["validation_motion"],
                "trust_model": mutations["trust_model"],
                "operating_cadence": mutations["operating_cadence"],
                "venture_theme": mutations["venture_theme"],
                "incubator_compound_score": score["incubator_compound_score"],
                "resilience_score": score["resilience_score"],
                "scout_verdict": score["verdict"],
                "bottleneck": score["bottleneck"],
                "recommended_admission_decision": recommended_decision,
                "recommended_next_step": score["recommended_next_step"],
                "manual_review_required": bool(str(args.trust_risk) == "high" or float(score["resilience_score"]) < 0.62 or recommended_decision != "invite"),
                "first_week_plan": _first_week_plan(score),
                "note": str(args.note or ""),
            },
        )
        save_state(args.runtime_root, state)
        refreshed = refresh_ops_artifacts(args.runtime_root)
        scout = refreshed.get("scout", {}) if isinstance(refreshed.get("scout"), dict) else {}
    _print(
        {
            "runtime_root": args.runtime_root,
            "application_event": event,
            "scout_summary": {
                "application_count": scout.get("application_count", 0),
                "pending_count": scout.get("pending_count", 0),
                "admitted_count": scout.get("admitted_count", 0),
                "rejected_count": scout.get("rejected_count", 0),
            },
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_admissions_review(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        application = _application(args.runtime_root, str(args.application_id))
        review_event = append_log(
            args.runtime_root,
            "admission_reviews",
            {
                "application_id": str(args.application_id),
                "decision": str(args.decision),
                "stage": str(args.stage or "qualification"),
                "note": str(args.note or ""),
            },
        )
        admission_event: dict[str, Any] | None = None
        admitted_venture: dict[str, Any] | None = None
        if str(args.decision) == "admit":
            venture_id = str(application.get("venture_id") or "")
            existing = next(
                (
                    item
                    for item in state.get("ventures", [])
                    if isinstance(item, dict) and str(item.get("venture_id") or "") == venture_id
                ),
                None,
            )
            if existing is not None:
                admitted_venture = existing
            else:
                founder = _founder(state, str(application.get("founder_id") or "owner"), str(application.get("founder_label") or "") or None)
                venture = {
                    "venture_id": venture_id or _slug(str(application.get("label") or args.application_id)),
                    "label": str(application.get("label") or application.get("venture_id") or args.application_id),
                    "status": "active",
                    "stage": str(args.stage or "qualification"),
                    "bottleneck": str(application.get("bottleneck") or "model_gap"),
                    "weekly_update_freshness_days": 0,
                    "last_review_days": 0,
                    "automation_coverage": 0.45,
                    "reuse_assets_count": 0,
                    "customer_conversations_this_week": 0,
                    "paid_signals_this_week": 0,
                    "trust_review_status": "amber" if str(application.get("trust_risk") or "medium") != "low" else "green",
                    "founder_update_latency_hours": 24,
                    "build_backlog_count": 0,
                    "decision_status": "continue",
                    "venture_model": str(application.get("venture_model") or ""),
                    "customer_surface": str(application.get("customer_surface") or ""),
                    "distribution_engine": str(application.get("distribution_engine") or ""),
                }
                state.setdefault("ventures", []).append(venture)
                founder.setdefault("venture_ids", [])
                if venture["venture_id"] not in founder["venture_ids"]:
                    founder["venture_ids"].append(venture["venture_id"])
                save_state(args.runtime_root, state)
                admission_event = append_log(
                    args.runtime_root,
                    "admissions",
                    {
                        "venture_id": venture["venture_id"],
                        "founder_id": founder["founder_id"],
                        "stage": venture["stage"],
                        "label": venture["label"],
                        "note": str(args.note or application.get("thesis_summary") or ""),
                    },
                )
                admitted_venture = venture
        refreshed = refresh_ops_artifacts(args.runtime_root)
        if admitted_venture is not None:
            admitted_venture = _venture(refreshed["state"], str(admitted_venture["venture_id"]))
        scout = refreshed.get("scout", {}) if isinstance(refreshed.get("scout"), dict) else {}
    _print(
        {
            "runtime_root": args.runtime_root,
            "application_id": str(args.application_id),
            "review_event": review_event,
            "admission_event": admission_event,
            "admitted_venture": admitted_venture,
            "scout_summary": {
                "application_count": scout.get("application_count", 0),
                "pending_count": scout.get("pending_count", 0),
                "admitted_count": scout.get("admitted_count", 0),
                "rejected_count": scout.get("rejected_count", 0),
            },
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_weekly_update(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        updates: dict[str, Any] = {}
        field_map = {
            "automation_coverage": args.automation_coverage,
            "reuse_assets_count": args.reuse_assets_count,
            "customer_conversations_this_week": args.customer_conversations,
            "paid_signals_this_week": args.paid_signals,
            "trust_review_status": args.trust_review_status,
            "founder_update_latency_hours": args.founder_update_latency_hours,
            "build_backlog_count": args.build_backlog_count,
            "bottleneck": args.bottleneck,
            "stage": args.stage,
        }
        for key, value in field_map.items():
            if value is None:
                continue
            venture[key] = value
            updates[key] = value
        venture["weekly_update_freshness_days"] = 0
        save_state(args.runtime_root, state)
        event = append_log(
            args.runtime_root,
            "weekly_updates",
            {
                "venture_id": venture["venture_id"],
                "updates": updates,
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_venture = _venture(refreshed["state"], venture["venture_id"])
    _print(
        {
            "runtime_root": args.runtime_root,
            "venture": refreshed_venture,
            "weekly_update_event": event,
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_review(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        venture["decision_status"] = str(args.decision)
        venture["last_review_days"] = 0
        if args.stage is not None:
            venture["stage"] = str(args.stage)
        if args.bottleneck is not None:
            venture["bottleneck"] = str(args.bottleneck)
        if args.trust_review_status is not None:
            venture["trust_review_status"] = str(args.trust_review_status)
        if args.reuse_assets_count is not None:
            venture["reuse_assets_count"] = int(args.reuse_assets_count)
        if str(args.decision) == "stop":
            venture["status"] = "archived"
            venture["stage"] = "archived"
        else:
            venture["status"] = "active"
        save_state(args.runtime_root, state)
        event = append_log(
            args.runtime_root,
            "reviews",
            {
                "venture_id": venture["venture_id"],
                "decision": args.decision,
                "bottleneck": venture.get("bottleneck"),
                "next_step": str(args.next_step or ""),
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_venture = _venture(refreshed["state"], venture["venture_id"])
    _print(
        {
            "runtime_root": args.runtime_root,
            "venture": refreshed_venture,
            "review_event": event,
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_experiment(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        event = append_log(
            args.runtime_root,
            "experiments",
            {
                "venture_id": venture["venture_id"],
                "experiment_id": str(args.experiment_id),
                "focus": str(args.focus or ""),
                "hypothesis": str(args.hypothesis),
                "status": str(args.status),
                "target_metric": str(args.target_metric or ""),
                "result_signal": str(args.result_signal or ""),
                "next_step": str(args.next_step or ""),
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_venture = _venture(refreshed["state"], venture["venture_id"])
    _print(
        {
            "runtime_root": args.runtime_root,
            "venture": refreshed_venture,
            "experiment_event": event,
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_build_request(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        event = append_log(
            args.runtime_root,
            "build_requests",
            {
                "venture_id": venture["venture_id"],
                "request_id": str(args.request_id),
                "title": str(args.title),
                "kind": str(args.kind),
                "priority": str(args.priority),
                "status": str(args.status),
                "linked_experiment_id": str(args.linked_experiment_id or ""),
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_venture = _venture(refreshed["state"], venture["venture_id"])
    _print(
        {
            "runtime_root": args.runtime_root,
            "venture": refreshed_venture,
            "build_request_event": event,
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_kpi_snapshot(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        snapshot = {
            "venture_id": venture["venture_id"],
            "stage": str(args.stage or venture.get("stage") or ""),
            "customer_conversations_this_week": int(args.customer_conversations),
            "paid_signals_this_week": int(args.paid_signals),
            "weekly_revenue": float(args.weekly_revenue),
            "pipeline_count": int(args.pipeline_count),
            "active_users": int(args.active_users),
            "automation_coverage": float(args.automation_coverage),
            "note": str(args.note or ""),
        }
        venture["stage"] = snapshot["stage"]
        venture["customer_conversations_this_week"] = snapshot["customer_conversations_this_week"]
        venture["paid_signals_this_week"] = snapshot["paid_signals_this_week"]
        venture["automation_coverage"] = snapshot["automation_coverage"]
        venture["weekly_revenue"] = snapshot["weekly_revenue"]
        venture["pipeline_count"] = snapshot["pipeline_count"]
        venture["active_users"] = snapshot["active_users"]
        venture["weekly_update_freshness_days"] = 0
        save_state(args.runtime_root, state)
        event = append_log(args.runtime_root, "kpi_snapshots", snapshot)
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_venture = _venture(refreshed["state"], venture["venture_id"])
    _print(
        {
            "runtime_root": args.runtime_root,
            "venture": refreshed_venture,
            "kpi_snapshot_event": event,
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_age(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        days = max(1, int(args.days))
        touched: list[str] = []
        ventures = [item for item in state.get("ventures", []) if isinstance(item, dict)]
        for venture in ventures:
            if args.venture_id and str(venture.get("venture_id") or "") != str(args.venture_id):
                continue
            if str(venture.get("status") or "") in {"archived", "stopped"}:
                continue
            venture["weekly_update_freshness_days"] = int(venture.get("weekly_update_freshness_days", 0) or 0) + days
            venture["last_review_days"] = int(venture.get("last_review_days", 0) or 0) + days
            venture["founder_update_latency_hours"] = int(venture.get("founder_update_latency_hours", 0) or 0) + (days * 6)
            touched.append(str(venture.get("venture_id") or "venture"))
        save_state(args.runtime_root, state)
        event = append_log(
            args.runtime_root,
            "time_passage",
            {
                "days": days,
                "venture_id": str(args.venture_id or ""),
                "touched_ventures": touched,
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
    _print(
        {
            "runtime_root": args.runtime_root,
            "aged_days": days,
            "touched_ventures": touched,
            "time_passage_event": event,
            "latest_tick": refreshed["tick"],
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="domain_chip_vibe_incubator.control_plane")
    parser.add_argument("--runtime-root", default=default_runtime_root())
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("status")

    scout = sub.add_parser("scout-intake")
    scout.add_argument("--application-id", required=True)
    scout.add_argument("--venture-id")
    scout.add_argument("--label", required=True)
    scout.add_argument("--founder-id", default="owner")
    scout.add_argument("--founder-label")
    scout.add_argument("--entry-source", choices=["internal", "referral", "inbound", "outbound"], default="internal")
    scout.add_argument("--thesis-summary")
    scout.add_argument("--trust-risk", choices=["low", "medium", "high"], default="medium")
    scout.add_argument("--venture-model", required=True)
    scout.add_argument("--customer-surface", required=True)
    scout.add_argument("--distribution-engine", required=True)
    scout.add_argument("--build-stack", default="template_factory")
    scout.add_argument("--validation-motion", default="design_partner")
    scout.add_argument("--trust-model", default="audit_trails")
    scout.add_argument("--operating-cadence", default="weekly_release")
    scout.add_argument("--venture-theme", required=True)
    scout.add_argument("--note")

    admissions_review = sub.add_parser("admissions-review")
    admissions_review.add_argument("--application-id", required=True)
    admissions_review.add_argument("--decision", choices=["watchlist", "invite", "admit", "reject"], required=True)
    admissions_review.add_argument("--stage")
    admissions_review.add_argument("--note")

    admit = sub.add_parser("admit")
    admit.add_argument("--venture-id", required=True)
    admit.add_argument("--label", required=True)
    admit.add_argument("--founder-id", default="owner")
    admit.add_argument("--founder-label")
    admit.add_argument("--stage", default="qualification")
    admit.add_argument("--bottleneck", default="model_gap")
    admit.add_argument("--venture-model")
    admit.add_argument("--customer-surface")
    admit.add_argument("--distribution-engine")
    admit.add_argument("--automation-coverage", type=float, default=0.45)
    admit.add_argument("--reuse-assets-count", type=int, default=0)
    admit.add_argument("--customer-conversations", type=int, default=0)
    admit.add_argument("--paid-signals", type=int, default=0)
    admit.add_argument("--trust-review-status", choices=["green", "amber", "red"], default="amber")
    admit.add_argument("--founder-update-latency-hours", type=int, default=24)
    admit.add_argument("--build-backlog-count", type=int, default=3)
    admit.add_argument("--note")

    weekly = sub.add_parser("weekly-update")
    weekly.add_argument("--venture-id", required=True)
    weekly.add_argument("--automation-coverage", type=float)
    weekly.add_argument("--reuse-assets-count", type=int)
    weekly.add_argument("--customer-conversations", type=int)
    weekly.add_argument("--paid-signals", type=int)
    weekly.add_argument("--trust-review-status", choices=["green", "amber", "red"])
    weekly.add_argument("--founder-update-latency-hours", type=int)
    weekly.add_argument("--build-backlog-count", type=int)
    weekly.add_argument("--bottleneck")
    weekly.add_argument("--stage")
    weekly.add_argument("--note")

    review = sub.add_parser("review")
    review.add_argument("--venture-id", required=True)
    review.add_argument("--decision", choices=["continue", "narrow", "pivot", "stop"], required=True)
    review.add_argument("--bottleneck")
    review.add_argument("--stage")
    review.add_argument("--trust-review-status", choices=["green", "amber", "red"])
    review.add_argument("--reuse-assets-count", type=int)
    review.add_argument("--next-step")
    review.add_argument("--note")

    experiment = sub.add_parser("experiment")
    experiment.add_argument("--venture-id", required=True)
    experiment.add_argument("--experiment-id", required=True)
    experiment.add_argument("--focus")
    experiment.add_argument("--hypothesis", required=True)
    experiment.add_argument("--status", choices=["proposed", "running", "won", "lost", "blocked", "cancelled"], default="proposed")
    experiment.add_argument("--target-metric")
    experiment.add_argument("--result-signal")
    experiment.add_argument("--next-step")
    experiment.add_argument("--note")

    build_request = sub.add_parser("build-request")
    build_request.add_argument("--venture-id", required=True)
    build_request.add_argument("--request-id", required=True)
    build_request.add_argument("--title", required=True)
    build_request.add_argument("--kind", choices=["workflow", "agent", "product", "integration", "ops", "content"], default="workflow")
    build_request.add_argument("--priority", choices=["high", "medium", "low"], default="medium")
    build_request.add_argument("--status", choices=["open", "in_progress", "blocked", "shipped", "cancelled"], default="open")
    build_request.add_argument("--linked-experiment-id")
    build_request.add_argument("--note")

    kpi = sub.add_parser("kpi-snapshot")
    kpi.add_argument("--venture-id", required=True)
    kpi.add_argument("--stage")
    kpi.add_argument("--customer-conversations", type=int, default=0)
    kpi.add_argument("--paid-signals", type=int, default=0)
    kpi.add_argument("--weekly-revenue", type=float, default=0.0)
    kpi.add_argument("--pipeline-count", type=int, default=0)
    kpi.add_argument("--active-users", type=int, default=0)
    kpi.add_argument("--automation-coverage", type=float, default=0.0)
    kpi.add_argument("--note")

    age = sub.add_parser("age")
    age.add_argument("--days", type=int, default=1)
    age.add_argument("--venture-id")
    age.add_argument("--note")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.action == "status":
        _handle_status(args)
        return
    if args.action == "scout-intake":
        _handle_scout_intake(args)
        return
    if args.action == "admissions-review":
        _handle_admissions_review(args)
        return
    if args.action == "admit":
        _handle_admit(args)
        return
    if args.action == "weekly-update":
        _handle_weekly_update(args)
        return
    if args.action == "review":
        _handle_review(args)
        return
    if args.action == "experiment":
        _handle_experiment(args)
        return
    if args.action == "build-request":
        _handle_build_request(args)
        return
    if args.action == "kpi-snapshot":
        _handle_kpi_snapshot(args)
        return
    if args.action == "age":
        _handle_age(args)
        return


if __name__ == "__main__":
    main()
