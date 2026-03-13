from __future__ import annotations

import argparse
import json
from typing import Any

try:
    from .ops_loop import append_log, default_runtime_root, load_state, ops_write_lock, refresh_ops_artifacts, save_state
except ImportError:
    from ops_loop import append_log, default_runtime_root, load_state, ops_write_lock, refresh_ops_artifacts, save_state


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


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


def _status_payload(runtime_root: str) -> dict[str, Any]:
    with ops_write_lock(runtime_root):
        refreshed = refresh_ops_artifacts(runtime_root)
    state = refreshed["state"]
    tick = refreshed["tick"]
    ventures = [item for item in state.get("ventures", []) if isinstance(item, dict)]
    return {
        "runtime_root": runtime_root,
        "program": state.get("program", {}),
        "queue_counts": _queue_counts(state),
        "founder_count": len(state.get("founders", [])),
        "venture_count": len(ventures),
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
    _print(
        {
            "runtime_root": args.runtime_root,
            "admitted_venture": venture,
            "admission_event": event,
            "queue_counts": _queue_counts(refreshed["state"]),
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
    _print(
        {
            "runtime_root": args.runtime_root,
            "venture": venture,
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
    _print(
        {
            "runtime_root": args.runtime_root,
            "venture": venture,
            "review_event": event,
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
    if args.action == "admit":
        _handle_admit(args)
        return
    if args.action == "weekly-update":
        _handle_weekly_update(args)
        return
    if args.action == "review":
        _handle_review(args)
        return
    if args.action == "age":
        _handle_age(args)
        return


if __name__ == "__main__":
    main()
