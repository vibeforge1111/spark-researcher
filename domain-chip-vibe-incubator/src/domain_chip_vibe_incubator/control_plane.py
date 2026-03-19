from __future__ import annotations

import argparse
import json
from typing import Any

try:
    from .cli import score_venture_candidate
except ImportError:
    from cli import score_venture_candidate

try:
    from .ops_loop import append_log, default_runtime_root, load_state, ops_write_lock, promote_learning, read_log, refresh_ops_artifacts, save_state
except ImportError:
    from ops_loop import append_log, default_runtime_root, load_state, ops_write_lock, promote_learning, read_log, refresh_ops_artifacts, save_state


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


def _customer_gtm_by_venture(refreshed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    customer_gtm = refreshed.get("customer_gtm", {}) if isinstance(refreshed.get("customer_gtm"), dict) else {}
    return {
        str(item.get("venture_id") or ""): item
        for item in customer_gtm.get("ventures", [])
        if isinstance(item, dict) and item.get("venture_id")
    }


def _trust_capital_by_venture(refreshed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    trust_capital = refreshed.get("trust_capital", {}) if isinstance(refreshed.get("trust_capital"), dict) else {}
    return {
        str(item.get("venture_id") or ""): item
        for item in trust_capital.get("ventures", [])
        if isinstance(item, dict) and item.get("venture_id")
    }


def _portfolio_learning_by_venture(refreshed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    portfolio_learning = refreshed.get("portfolio_learning", {}) if isinstance(refreshed.get("portfolio_learning"), dict) else {}
    return {
        str(item.get("venture_id") or ""): item
        for item in portfolio_learning.get("ventures", [])
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
    customer_gtm = refreshed.get("customer_gtm", {}) if isinstance(refreshed.get("customer_gtm"), dict) else {}
    customer_gtm_by_venture = _customer_gtm_by_venture(refreshed)
    trust_capital = refreshed.get("trust_capital", {}) if isinstance(refreshed.get("trust_capital"), dict) else {}
    trust_capital_by_venture = _trust_capital_by_venture(refreshed)
    portfolio_learning = refreshed.get("portfolio_learning", {}) if isinstance(refreshed.get("portfolio_learning"), dict) else {}
    portfolio_learning_by_venture = _portfolio_learning_by_venture(refreshed)
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
        "customer_gtm": {
            "conversation_count": customer_gtm.get("conversation_count", 0),
            "willingness_signal_count": customer_gtm.get("willingness_signal_count", 0),
            "open_pipeline_count": customer_gtm.get("open_pipeline_count", 0),
            "open_pipeline_value": customer_gtm.get("open_pipeline_value", 0.0),
        },
        "trust_capital": {
            "blocking_trust_count": trust_capital.get("blocking_trust_count", 0),
            "capital_ready_count": trust_capital.get("capital_ready_count", 0),
            "investor_target_count": trust_capital.get("investor_target_count", 0),
        },
        "portfolio_learning": {
            "retrospective_count": portfolio_learning.get("retrospective_count", 0),
            "promoted_playbook_count": portfolio_learning.get("promoted_playbook_count", 0),
            "reusable_asset_count": portfolio_learning.get("reusable_asset_count", 0),
            "repeated_failure_count": portfolio_learning.get("repeated_failure_count", 0),
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
                "customer_signal_count": customer_gtm_by_venture.get(str(item.get("venture_id") or ""), {}).get("conversation_count", 0),
                "open_pipeline_count": customer_gtm_by_venture.get(str(item.get("venture_id") or ""), {}).get("open_pipeline_count", 0),
                "open_pipeline_value": customer_gtm_by_venture.get(str(item.get("venture_id") or ""), {}).get("open_pipeline_value", 0.0),
                "capital_readiness": trust_capital_by_venture.get(str(item.get("venture_id") or ""), {}).get("capital_readiness", False),
                "trust_blocking": trust_capital_by_venture.get(str(item.get("venture_id") or ""), {}).get("blocking", False),
                "investor_target_count": trust_capital_by_venture.get(str(item.get("venture_id") or ""), {}).get("open_investor_count", 0),
                "portfolio_retrospective_count": portfolio_learning_by_venture.get(str(item.get("venture_id") or ""), {}).get("retrospective_count", 0),
                "promoted_playbook_count": portfolio_learning_by_venture.get(str(item.get("venture_id") or ""), {}).get("promoted_playbook_count", 0),
                "reusable_asset_count": portfolio_learning_by_venture.get(str(item.get("venture_id") or ""), {}).get("reusable_asset_count", 0),
                "repeated_failure_count": portfolio_learning_by_venture.get(str(item.get("venture_id") or ""), {}).get("repeated_failure_count", 0),
                "doctrine_ready": portfolio_learning_by_venture.get(str(item.get("venture_id") or ""), {}).get("doctrine_ready", False),
                "latest_weekly_revenue": (
                    execution_by_venture.get(str(item.get("venture_id") or ""), {}).get("latest_kpi_snapshot", {}) or {}
                ).get("weekly_revenue"),
            }
            for item in ventures
            if str(item.get("status") or "") not in {"archived", "stopped"}
        ],
        "batches": refreshed.get("batches", []),
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
        evidence = str(args.evidence or "") if hasattr(args, "evidence") else ""
        if evidence:
            venture["last_review_evidence"] = evidence
            venture["evidence_backed_reviews"] = int(venture.get("evidence_backed_reviews") or 0) + 1
        venture["total_reviews"] = int(venture.get("total_reviews") or 0) + 1
        save_state(args.runtime_root, state)
        event = append_log(
            args.runtime_root,
            "reviews",
            {
                "venture_id": venture["venture_id"],
                "decision": args.decision,
                "bottleneck": venture.get("bottleneck"),
                "evidence": evidence,
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

        # compute revenue trend from previous snapshot
        previous_revenue = float(venture.get("weekly_revenue") or 0)
        current_revenue = float(args.weekly_revenue)
        if previous_revenue > 0:
            revenue_trend = round((current_revenue - previous_revenue) / previous_revenue, 4)
        elif current_revenue > 0:
            revenue_trend = 1.0  # first revenue ever
        else:
            revenue_trend = 0.0

        # retention signal: returning / (returning + churned), default 0
        returning = int(args.returning_customers)
        churned = int(args.churned_customers)
        retention_signal = round(returning / max(1, returning + churned), 4) if (returning + churned) > 0 else 0.0

        snapshot = {
            "venture_id": venture["venture_id"],
            "stage": str(args.stage or venture.get("stage") or ""),
            "customer_conversations_this_week": int(args.customer_conversations),
            "paid_signals_this_week": int(args.paid_signals),
            "weekly_revenue": current_revenue,
            "pipeline_count": int(args.pipeline_count),
            "active_users": int(args.active_users),
            "automation_coverage": float(args.automation_coverage),
            "returning_customers": returning,
            "churned_customers": churned,
            "revenue_trend": revenue_trend,
            "retention_signal": retention_signal,
            "note": str(args.note or ""),
        }
        venture["stage"] = snapshot["stage"]
        venture["customer_conversations_this_week"] = snapshot["customer_conversations_this_week"]
        venture["paid_signals_this_week"] = snapshot["paid_signals_this_week"]
        venture["automation_coverage"] = snapshot["automation_coverage"]
        venture["weekly_revenue"] = snapshot["weekly_revenue"]
        venture["pipeline_count"] = snapshot["pipeline_count"]
        venture["active_users"] = snapshot["active_users"]
        venture["returning_customers"] = returning
        venture["churned_customers"] = churned
        venture["revenue_trend"] = revenue_trend
        venture["retention_signal"] = retention_signal
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


def _handle_customer_conversation(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        impact = str(getattr(args, "impact", "none") or "none")
        event = append_log(
            args.runtime_root,
            "customer_conversations",
            {
                "venture_id": venture["venture_id"],
                "conversation_id": str(args.conversation_id),
                "customer_id": str(args.customer_id or ""),
                "customer_label": str(args.customer_label or args.customer_id or ""),
                "channel": str(args.channel),
                "stage": str(args.stage),
                "willingness_to_pay": str(args.willingness_to_pay),
                "objection": str(args.objection or ""),
                "outcome": str(args.outcome or ""),
                "impact": impact,
                "next_step": str(args.next_step or ""),
                "note": str(args.note or ""),
            },
        )
        # Track impact on venture state
        if impact in ("commitment", "payment"):
            venture["conversations_with_commitment"] = int(venture.get("conversations_with_commitment") or 0) + 1
        if impact == "payment":
            venture["conversations_with_payment"] = int(venture.get("conversations_with_payment") or 0) + 1
        save_state(args.runtime_root, state)
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_venture = _venture(refreshed["state"], venture["venture_id"])
    _print(
        {
            "runtime_root": args.runtime_root,
            "venture": refreshed_venture,
            "customer_conversation_event": event,
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_pipeline_opportunity(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        event = append_log(
            args.runtime_root,
            "pipeline_opportunities",
            {
                "venture_id": venture["venture_id"],
                "opportunity_id": str(args.opportunity_id),
                "customer_id": str(args.customer_id or ""),
                "customer_label": str(args.customer_label or args.customer_id or ""),
                "source": str(args.source),
                "stage": str(args.stage),
                "status": str(args.status),
                "value": float(args.value),
                "confidence": float(args.confidence),
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
            "pipeline_opportunity_event": event,
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_trust_review(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        event = append_log(
            args.runtime_root,
            "trust_reviews",
            {
                "venture_id": venture["venture_id"],
                "review_id": str(args.review_id),
                "scope": str(args.scope),
                "status": str(args.status),
                "risk_area": str(args.risk_area or ""),
                "blocking": bool(args.blocking),
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
            "trust_review_event": event,
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_data_room_item(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        event = append_log(
            args.runtime_root,
            "data_room_items",
            {
                "venture_id": venture["venture_id"],
                "item_id": str(args.item_id),
                "category": str(args.category),
                "label": str(args.label),
                "status": str(args.status),
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_venture = _venture(refreshed["state"], venture["venture_id"])
    _print(
        {
            "runtime_root": args.runtime_root,
            "venture": refreshed_venture,
            "data_room_item_event": event,
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_investor_target(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        event = append_log(
            args.runtime_root,
            "investor_targets",
            {
                "venture_id": venture["venture_id"],
                "target_id": str(args.target_id),
                "investor_label": str(args.investor_label),
                "thesis_fit": str(args.thesis_fit),
                "stage": str(args.stage),
                "status": str(args.status),
                "check_size": str(args.check_size or ""),
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
            "investor_target_event": event,
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_portfolio_retrospective(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        event = append_log(
            args.runtime_root,
            "portfolio_retrospectives",
            {
                "venture_id": venture["venture_id"],
                "retrospective_id": str(args.retrospective_id),
                "scope": str(args.scope),
                "outcome": str(args.outcome),
                "lesson": str(args.lesson),
                "failure_mode": str(args.failure_mode or ""),
                "doctrine_claim": str(args.doctrine_claim or ""),
                "boundary": str(args.boundary or ""),
                "promote_doctrine": bool(args.promote_doctrine),
                "evidence_strength": str(args.evidence_strength),
                "reusable_asset_id": str(args.reusable_asset_id or ""),
                "next_step": str(args.next_step or ""),
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_venture = _venture(refreshed["state"], venture["venture_id"])
        learning = refreshed.get("portfolio_learning", {}) if isinstance(refreshed.get("portfolio_learning"), dict) else {}
    _print(
        {
            "runtime_root": args.runtime_root,
            "venture": refreshed_venture,
            "portfolio_retrospective_event": event,
            "portfolio_learning": {
                "retrospective_count": learning.get("retrospective_count", 0),
                "promoted_playbook_count": learning.get("promoted_playbook_count", 0),
                "repeated_failure_count": learning.get("repeated_failure_count", 0),
            },
            "latest_tick": refreshed["tick"],
        }
    )


def _handle_reusable_asset(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        event = append_log(
            args.runtime_root,
            "reusable_assets",
            {
                "venture_id": venture["venture_id"],
                "asset_id": str(args.asset_id),
                "label": str(args.label),
                "kind": str(args.kind),
                "status": str(args.status),
                "reused_by_count": int(args.reused_by_count),
                "shared_surface": str(args.shared_surface or ""),
                "next_step": str(args.next_step or ""),
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_venture = _venture(refreshed["state"], venture["venture_id"])
        learning = refreshed.get("portfolio_learning", {}) if isinstance(refreshed.get("portfolio_learning"), dict) else {}
    _print(
        {
            "runtime_root": args.runtime_root,
            "venture": refreshed_venture,
            "reusable_asset_event": event,
            "portfolio_learning": {
                "reusable_asset_count": learning.get("reusable_asset_count", 0),
                "promoted_playbook_count": learning.get("promoted_playbook_count", 0),
            },
            "latest_tick": refreshed["tick"],
        }
    )


def _batch(state: dict[str, Any], batch_id: str) -> dict[str, Any]:
    for item in state.get("batches", []):
        if isinstance(item, dict) and str(item.get("batch_id") or "") == batch_id:
            return item
    raise RuntimeError(f"Unknown batch_id: {batch_id}")


def _handle_batch_create(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        batch_id = str(args.batch_id)
        if any(str(b.get("batch_id") or "") == batch_id for b in state.get("batches", []) if isinstance(b, dict)):
            raise RuntimeError(f"batch_id already exists: {batch_id}")
        batch = {
            "batch_id": batch_id,
            "label": str(args.label),
            "status": "forming",
            "sprint_week": 0,
            "duration_weeks": int(args.duration_weeks),
            "venture_ids": [],
            "created_at": __import__("datetime").datetime.now(__import__("datetime").UTC).replace(microsecond=0).isoformat(),
        }
        state.setdefault("batches", []).append(batch)
        # Update program batch style
        program = state.setdefault("program", {})
        program["batch_style"] = "cohort"
        save_state(args.runtime_root, state)
        event = append_log(args.runtime_root, "batches", {"batch_id": batch_id, "action": "create", "label": batch["label"], "note": str(args.note or "")})
        refreshed = refresh_ops_artifacts(args.runtime_root)
    _print({"runtime_root": args.runtime_root, "batch": batch, "batch_event": event, "latest_tick": refreshed["tick"]})


def _handle_batch_admit(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        batch = _batch(state, str(args.batch_id))
        venture = _venture(state, str(args.venture_id))
        venture_id = str(venture["venture_id"])
        if venture_id not in batch.get("venture_ids", []):
            batch.setdefault("venture_ids", []).append(venture_id)
        venture["batch_id"] = str(args.batch_id)
        if batch["status"] == "forming":
            batch["status"] = "active"
            batch["sprint_week"] = 1
        save_state(args.runtime_root, state)
        event = append_log(args.runtime_root, "batches", {"batch_id": str(args.batch_id), "action": "admit", "venture_id": venture_id, "note": str(args.note or "")})
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_batch = _batch(refreshed["state"], str(args.batch_id))
    _print({"runtime_root": args.runtime_root, "batch": refreshed_batch, "venture": _venture(refreshed["state"], venture_id), "batch_event": event, "latest_tick": refreshed["tick"]})


def _handle_batch_status(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        refreshed = refresh_ops_artifacts(args.runtime_root)
    batches = refreshed.get("batches", [])
    if args.batch_id:
        batches = [b for b in batches if b.get("batch_id") == str(args.batch_id)]
    _print({"runtime_root": args.runtime_root, "batches": batches, "latest_tick": refreshed["tick"]})


def _handle_batch_advance(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        batch = _batch(state, str(args.batch_id))
        current_week = int(batch.get("sprint_week", 0) or 0)
        duration = int(batch.get("duration_weeks", 6) or 6)
        batch["sprint_week"] = current_week + 1
        if batch["sprint_week"] > duration:
            batch["status"] = "graduated"
        save_state(args.runtime_root, state)
        event = append_log(args.runtime_root, "batches", {"batch_id": str(args.batch_id), "action": "advance", "sprint_week": batch["sprint_week"], "status": batch["status"], "note": str(args.note or "")})
        refreshed = refresh_ops_artifacts(args.runtime_root)
        refreshed_batch = _batch(refreshed["state"], str(args.batch_id))
    _print({"runtime_root": args.runtime_root, "batch": refreshed_batch, "batch_event": event, "latest_tick": refreshed["tick"]})


def _handle_promote_learning(args: argparse.Namespace) -> None:
    summary = promote_learning(args.runtime_root)
    _print({"runtime_root": args.runtime_root, "learning_promotion": summary})


def _handle_log_contribution(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        venture = _venture(state, str(args.venture_id))
        event = append_log(
            args.runtime_root,
            "contributions",
            {
                "venture_id": venture["venture_id"],
                "contributor_id": str(args.contributor_id),
                "quest_type": str(args.quest_type),
                "evidence": str(args.evidence),
                "genesis_credits": int(args.genesis_credits),
                "status": str(args.status),
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
    _print({"runtime_root": args.runtime_root, "contribution_event": event, "latest_tick": refreshed["tick"]})


def _token_readiness_checklist(runtime_root: str, venture_id: str) -> dict[str, Any]:
    """Check token readiness gates for a venture."""
    state = load_state(runtime_root)
    venture = _venture(state, venture_id)
    trust_reviews = [r for r in read_log(runtime_root, "trust_reviews") if r.get("venture_id") == venture_id]
    governance_proposals = [p for p in read_log(runtime_root, "governance_proposals") if p.get("venture_id") == venture_id]
    security_passed = any(r.get("scope") == "security" and r.get("status") == "green" for r in trust_reviews)
    governance_approved = any(p.get("status") == "approved" and p.get("proposal_type") == "token_readiness" for p in governance_proposals)
    has_revenue = float(venture.get("weekly_revenue", 0) or 0) > 0
    has_paid_signals = int(venture.get("paid_signals_this_week", 0) or 0) > 0
    checklist = {
        "venture_id": venture_id,
        "utility_demonstrated": has_revenue and has_paid_signals,
        "security_review_passed": security_passed,
        "governance_proposal_approved": governance_approved,
        "community_threshold_met": int(venture.get("active_users", 0) or 0) >= 5,
        "all_gates_passed": False,
    }
    checklist["all_gates_passed"] = all(checklist[k] for k in ("utility_demonstrated", "security_review_passed", "governance_proposal_approved", "community_threshold_met"))
    return checklist


def _handle_token_readiness(args: argparse.Namespace) -> None:
    checklist = _token_readiness_checklist(args.runtime_root, str(args.venture_id))
    _print({"runtime_root": args.runtime_root, "token_readiness": checklist})


def _handle_governance_propose(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        state = load_state(args.runtime_root)
        event = append_log(
            args.runtime_root,
            "governance_proposals",
            {
                "proposal_id": str(args.proposal_id),
                "proposal_type": str(args.proposal_type),
                "venture_id": str(args.venture_id or ""),
                "description": str(args.description),
                "status": "open",
                "votes_for": 0,
                "votes_against": 0,
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
    _print({"runtime_root": args.runtime_root, "governance_event": event, "latest_tick": refreshed["tick"]})


def _handle_governance_vote(args: argparse.Namespace) -> None:
    with ops_write_lock(args.runtime_root):
        event = append_log(
            args.runtime_root,
            "governance_votes",
            {
                "proposal_id": str(args.proposal_id),
                "decision": str(args.decision),
                "weight": float(args.weight),
                "note": str(args.note or ""),
            },
        )
        refreshed = refresh_ops_artifacts(args.runtime_root)
    _print({"runtime_root": args.runtime_root, "vote_event": event, "latest_tick": refreshed["tick"]})


def _handle_governance_tally(args: argparse.Namespace) -> None:
    """Tally votes on open proposals, resolve those that meet quorum."""
    with ops_write_lock(args.runtime_root):
        proposals = read_log(args.runtime_root, "governance_proposals")
        votes = read_log(args.runtime_root, "governance_votes")
        quorum = float(args.quorum)

        # Build map: proposal_id → latest proposal record
        open_proposals: dict[str, dict] = {}
        for p in proposals:
            pid = str(p.get("proposal_id", ""))
            if pid:
                open_proposals[pid] = p

        # Tally votes per proposal
        tallies: dict[str, dict] = {}
        for v in votes:
            pid = str(v.get("proposal_id", ""))
            if pid not in tallies:
                tallies[pid] = {"for": 0.0, "against": 0.0, "abstain": 0.0, "total": 0.0}
            decision = str(v.get("decision", "abstain"))
            weight = float(v.get("weight", 1.0))
            if decision in tallies[pid]:
                tallies[pid][decision] += weight
            tallies[pid]["total"] += weight

        resolved: list[dict] = []
        for pid, proposal in open_proposals.items():
            if str(proposal.get("status", "")) != "open":
                continue
            tally = tallies.get(pid, {"for": 0.0, "against": 0.0, "abstain": 0.0, "total": 0.0})
            if tally["total"] < quorum:
                continue  # not enough votes yet
            outcome = "passed" if tally["for"] > tally["against"] else "rejected"
            resolution = {
                "proposal_id": pid,
                "proposal_type": str(proposal.get("proposal_type", "")),
                "venture_id": str(proposal.get("venture_id", "")),
                "outcome": outcome,
                "votes_for": tally["for"],
                "votes_against": tally["against"],
                "votes_abstain": tally["abstain"],
                "quorum_met": tally["total"],
            }
            resolved.append(resolution)
            append_log(args.runtime_root, "governance_resolutions", resolution)

        # Update state with resolved governance counts
        state = load_state(args.runtime_root)
        passed_count = sum(1 for r in resolved if r["outcome"] == "passed")
        state.setdefault("governance", {})
        state["governance"]["total_resolved"] = int(state["governance"].get("total_resolved") or 0) + len(resolved)
        state["governance"]["total_passed"] = int(state["governance"].get("total_passed") or 0) + passed_count
        save_state(args.runtime_root, state)
        refreshed = refresh_ops_artifacts(args.runtime_root)
    _print({
        "runtime_root": args.runtime_root,
        "resolved_count": len(resolved),
        "resolutions": resolved,
        "governance": state["governance"],
        "latest_tick": refreshed["tick"],
    })


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
    review.add_argument("--evidence", help="Concrete outcome evidence supporting this decision")
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

    conversation = sub.add_parser("customer-conversation")
    conversation.add_argument("--venture-id", required=True)
    conversation.add_argument("--conversation-id", required=True)
    conversation.add_argument("--customer-id")
    conversation.add_argument("--customer-label")
    conversation.add_argument("--channel", choices=["call", "email", "chat", "demo", "meeting"], default="call")
    conversation.add_argument("--stage", choices=["discovery", "demo", "proposal", "followup", "close"], default="discovery")
    conversation.add_argument("--willingness-to-pay", choices=["unknown", "no", "maybe", "yes", "strong_yes"], default="unknown")
    conversation.add_argument("--objection")
    conversation.add_argument("--outcome")
    conversation.add_argument("--impact", choices=["none", "interest", "commitment", "payment"], default="none")
    conversation.add_argument("--next-step")
    conversation.add_argument("--note")

    pipeline = sub.add_parser("pipeline-opportunity")
    pipeline.add_argument("--venture-id", required=True)
    pipeline.add_argument("--opportunity-id", required=True)
    pipeline.add_argument("--customer-id")
    pipeline.add_argument("--customer-label")
    pipeline.add_argument("--source", choices=["outbound", "referral", "inbound", "content", "community"], default="outbound")
    pipeline.add_argument("--stage", choices=["new", "qualified", "proposal", "verbal", "won", "lost"], default="new")
    pipeline.add_argument("--status", choices=["open", "active", "won", "lost", "closed"], default="open")
    pipeline.add_argument("--value", type=float, default=0.0)
    pipeline.add_argument("--confidence", type=float, default=0.5)
    pipeline.add_argument("--next-step")
    pipeline.add_argument("--note")

    trust = sub.add_parser("trust-review")
    trust.add_argument("--venture-id", required=True)
    trust.add_argument("--review-id", required=True)
    trust.add_argument("--scope", choices=["security", "data_access", "automation_release", "customer_delivery", "capital_readiness"], default="security")
    trust.add_argument("--status", choices=["green", "amber", "red"], required=True)
    trust.add_argument("--risk-area")
    trust.add_argument("--blocking", action="store_true")
    trust.add_argument("--next-step")
    trust.add_argument("--note")

    data_room = sub.add_parser("data-room-item")
    data_room.add_argument("--venture-id", required=True)
    data_room.add_argument("--item-id", required=True)
    data_room.add_argument("--category", choices=["deck", "kpi", "customer_evidence", "legal", "security", "financial", "product"], default="deck")
    data_room.add_argument("--label", required=True)
    data_room.add_argument("--status", choices=["missing", "draft", "ready", "approved"], required=True)
    data_room.add_argument("--note")

    investor = sub.add_parser("investor-target")
    investor.add_argument("--venture-id", required=True)
    investor.add_argument("--target-id", required=True)
    investor.add_argument("--investor-label", required=True)
    investor.add_argument("--thesis-fit", choices=["low", "medium", "high"], default="medium")
    investor.add_argument("--stage", choices=["targeted", "drafting", "introduced", "followup", "diligence", "passed"], default="targeted")
    investor.add_argument("--status", choices=["open", "interested", "passed", "archived"], default="open")
    investor.add_argument("--check-size")
    investor.add_argument("--next-step")
    investor.add_argument("--note")

    retrospective = sub.add_parser("portfolio-retrospective")
    retrospective.add_argument("--venture-id", required=True)
    retrospective.add_argument("--retrospective-id", required=True)
    retrospective.add_argument("--scope", choices=["weekly_review", "launch", "customer", "build", "trust", "capital", "shutdown"], default="weekly_review")
    retrospective.add_argument("--outcome", choices=["win", "mixed", "loss", "blocked"], required=True)
    retrospective.add_argument("--lesson", required=True)
    retrospective.add_argument("--failure-mode")
    retrospective.add_argument("--doctrine-claim")
    retrospective.add_argument("--boundary")
    retrospective.add_argument("--promote-doctrine", action="store_true")
    retrospective.add_argument("--evidence-strength", choices=["low", "medium", "high"], default="medium")
    retrospective.add_argument("--reusable-asset-id")
    retrospective.add_argument("--next-step")
    retrospective.add_argument("--note")

    reusable_asset = sub.add_parser("reusable-asset")
    reusable_asset.add_argument("--venture-id", required=True)
    reusable_asset.add_argument("--asset-id", required=True)
    reusable_asset.add_argument("--label", required=True)
    reusable_asset.add_argument("--kind", choices=["template", "agent", "workflow", "playbook", "dataset", "content", "ops"], default="playbook")
    reusable_asset.add_argument("--status", choices=["draft", "in_use", "shared", "retired"], required=True)
    reusable_asset.add_argument("--reused-by-count", type=int, default=0)
    reusable_asset.add_argument("--shared-surface")
    reusable_asset.add_argument("--next-step")
    reusable_asset.add_argument("--note")

    kpi = sub.add_parser("kpi-snapshot")
    kpi.add_argument("--venture-id", required=True)
    kpi.add_argument("--stage")
    kpi.add_argument("--customer-conversations", type=int, default=0)
    kpi.add_argument("--paid-signals", type=int, default=0)
    kpi.add_argument("--weekly-revenue", type=float, default=0.0)
    kpi.add_argument("--pipeline-count", type=int, default=0)
    kpi.add_argument("--active-users", type=int, default=0)
    kpi.add_argument("--automation-coverage", type=float, default=0.0)
    kpi.add_argument("--returning-customers", type=int, default=0)
    kpi.add_argument("--churned-customers", type=int, default=0)
    kpi.add_argument("--note")

    age = sub.add_parser("age")
    age.add_argument("--days", type=int, default=1)
    age.add_argument("--venture-id")
    age.add_argument("--note")

    batch_create = sub.add_parser("batch-create")
    batch_create.add_argument("--batch-id", required=True)
    batch_create.add_argument("--label", required=True)
    batch_create.add_argument("--duration-weeks", type=int, default=6)
    batch_create.add_argument("--note")

    batch_admit = sub.add_parser("batch-admit")
    batch_admit.add_argument("--batch-id", required=True)
    batch_admit.add_argument("--venture-id", required=True)
    batch_admit.add_argument("--note")

    batch_status = sub.add_parser("batch-status")
    batch_status.add_argument("--batch-id")

    batch_advance = sub.add_parser("batch-advance")
    batch_advance.add_argument("--batch-id", required=True)
    batch_advance.add_argument("--note")

    sub.add_parser("promote-learning")

    contribution = sub.add_parser("log-contribution")
    contribution.add_argument("--venture-id", required=True)
    contribution.add_argument("--contributor-id", required=True)
    contribution.add_argument("--quest-type", choices=["growth", "product", "research", "trust"], required=True)
    contribution.add_argument("--evidence", required=True)
    contribution.add_argument("--genesis-credits", type=int, default=1)
    contribution.add_argument("--status", choices=["pending", "verified", "rejected"], default="pending")
    contribution.add_argument("--note")

    token_readiness = sub.add_parser("token-readiness")
    token_readiness.add_argument("--venture-id", required=True)

    governance_propose = sub.add_parser("governance-propose")
    governance_propose.add_argument("--proposal-id", required=True)
    governance_propose.add_argument("--proposal-type", choices=["token_readiness", "support_reserve", "curriculum", "contributor_reward", "treasury_support", "spotlight"], required=True)
    governance_propose.add_argument("--venture-id")
    governance_propose.add_argument("--description", required=True)
    governance_propose.add_argument("--note")

    governance_vote = sub.add_parser("governance-vote")
    governance_vote.add_argument("--proposal-id", required=True)
    governance_vote.add_argument("--decision", choices=["for", "against", "abstain"], required=True)
    governance_vote.add_argument("--weight", type=float, default=1.0)
    governance_vote.add_argument("--note")

    governance_tally = sub.add_parser("governance-tally")
    governance_tally.add_argument("--quorum", type=float, default=1.0, help="Minimum total vote weight to resolve")

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
    if args.action == "customer-conversation":
        _handle_customer_conversation(args)
        return
    if args.action == "pipeline-opportunity":
        _handle_pipeline_opportunity(args)
        return
    if args.action == "trust-review":
        _handle_trust_review(args)
        return
    if args.action == "data-room-item":
        _handle_data_room_item(args)
        return
    if args.action == "investor-target":
        _handle_investor_target(args)
        return
    if args.action == "portfolio-retrospective":
        _handle_portfolio_retrospective(args)
        return
    if args.action == "reusable-asset":
        _handle_reusable_asset(args)
        return
    if args.action == "kpi-snapshot":
        _handle_kpi_snapshot(args)
        return
    if args.action == "age":
        _handle_age(args)
        return
    if args.action == "batch-create":
        _handle_batch_create(args)
        return
    if args.action == "batch-admit":
        _handle_batch_admit(args)
        return
    if args.action == "batch-status":
        _handle_batch_status(args)
        return
    if args.action == "batch-advance":
        _handle_batch_advance(args)
        return
    if args.action == "promote-learning":
        _handle_promote_learning(args)
        return
    if args.action == "log-contribution":
        _handle_log_contribution(args)
        return
    if args.action == "token-readiness":
        _handle_token_readiness(args)
        return
    if args.action == "governance-propose":
        _handle_governance_propose(args)
        return
    if args.action == "governance-vote":
        _handle_governance_vote(args)
        return
    if args.action == "governance-tally":
        _handle_governance_tally(args)
        return


if __name__ == "__main__":
    main()
