"""Vibe Incubator API — FastAPI version with auth and validation.

Run:
    uvicorn domain_chip_vibe_incubator.api_fastapi:app --port 4177 --reload

Or:
    python -m domain_chip_vibe_incubator.api_fastapi
"""

from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

try:
    from .ops_loop import (
        append_log,
        default_runtime_root,
        load_state,
        ops_write_lock,
        read_log,
        refresh_ops_artifacts,
        save_state,
    )
except ImportError:
    from ops_loop import (  # type: ignore[no-redef]
        append_log,
        default_runtime_root,
        load_state,
        ops_write_lock,
        read_log,
        refresh_ops_artifacts,
        save_state,
    )

# Re-use dashboard builder from stdlib API
try:
    from .api import build_dashboard_snapshot, build_status, _venture, _slug
except ImportError:
    from api import build_dashboard_snapshot, build_status, _venture, _slug  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RUNTIME_ROOT = default_runtime_root()
API_TOKEN = os.environ.get("VIBE_API_TOKEN", "")  # empty = auth disabled

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

security = HTTPBearer(auto_error=False)


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> None:
    """If VIBE_API_TOKEN is set, require a matching Bearer token."""
    if not API_TOKEN:
        return  # auth disabled
    if credentials is None or credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"


class AdmissionsReviewRequest(BaseModel):
    application_id: str
    decision: str = Field(pattern=r"^(invite|waitlist|reject)$")
    note: str = ""


class BuildRequestUpdate(BaseModel):
    venture_id: str
    request_id: str
    status: str
    title: str = ""
    kind: str = "workflow"
    priority: str = "medium"


class WeeklyUpdateRequest(BaseModel):
    venture_id: str
    stage: Optional[str] = None
    note: str = ""


class KpiSnapshotRequest(BaseModel):
    venture_id: str
    stage: Optional[str] = None
    customer_conversations: int = 0
    paid_signals: int = 0
    weekly_revenue: float = 0.0
    pipeline_count: int = 0
    active_users: int = 0
    automation_coverage: float = 0.0
    returning_customers: int = 0
    churned_customers: int = 0
    note: str = ""


class GovernanceProposeRequest(BaseModel):
    proposal_id: str
    proposal_type: str = Field(
        pattern=r"^(token_readiness|support_reserve|curriculum|contributor_reward|treasury_support|spotlight)$"
    )
    venture_id: str = ""
    description: str
    note: str = ""


class GovernanceVoteRequest(BaseModel):
    proposal_id: str
    decision: str = Field(pattern=r"^(for|against|abstain)$")
    weight: float = 1.0
    note: str = ""


class GovernanceTallyRequest(BaseModel):
    quorum: float = 1.0


class VentureExitRequest(BaseModel):
    venture_id: str
    reason: str
    outcome: str = Field(pattern=r"^(win|mixed|loss|blocked)$")
    lesson: str
    failure_mode: str = ""
    reusable_assets: str = ""


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Vibe Incubator API",
    version="2.0.0",
    description="Live API boundary between the dashboard and the incubator chip.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Read endpoints (no auth required)
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    return build_status()


@app.get("/api/dashboard")
def dashboard():
    return build_dashboard_snapshot()


@app.get("/api/alerts")
def alerts():
    """Return current health alerts from latest tick."""
    refreshed = refresh_ops_artifacts(RUNTIME_ROOT)
    tick = refreshed.get("tick", {})
    return {
        "alerts": tick.get("health_alerts", []),
        "critical_count": tick.get("critical_alert_count", 0),
        "warning_count": tick.get("warning_alert_count", 0),
    }


# ---------------------------------------------------------------------------
# Write endpoints (auth required when VIBE_API_TOKEN is set)
# ---------------------------------------------------------------------------

@app.post("/api/admissions-review")
def admissions_review(body: AdmissionsReviewRequest, _=Depends(verify_token)):
    from .api import action_admissions_review
    return action_admissions_review(body.model_dump())


@app.post("/api/build-request")
def build_request(body: BuildRequestUpdate, _=Depends(verify_token)):
    from .api import action_build_request_update
    return action_build_request_update(body.model_dump())


@app.post("/api/weekly-update")
def weekly_update(body: WeeklyUpdateRequest, _=Depends(verify_token)):
    from .api import action_weekly_update
    return action_weekly_update(body.model_dump())


@app.post("/api/kpi-snapshot")
def kpi_snapshot(body: KpiSnapshotRequest, _=Depends(verify_token)):
    venture_id = body.venture_id
    with ops_write_lock(RUNTIME_ROOT):
        state = load_state(RUNTIME_ROOT)
        venture = _venture(state, venture_id)

        previous_revenue = float(venture.get("weekly_revenue") or 0)
        current_revenue = body.weekly_revenue
        if previous_revenue > 0:
            revenue_trend = round((current_revenue - previous_revenue) / previous_revenue, 4)
        elif current_revenue > 0:
            revenue_trend = 1.0
        else:
            revenue_trend = 0.0

        returning = body.returning_customers
        churned = body.churned_customers
        retention_signal = round(returning / max(1, returning + churned), 4) if (returning + churned) > 0 else 0.0

        venture["customer_conversations_this_week"] = body.customer_conversations
        venture["paid_signals_this_week"] = body.paid_signals
        venture["weekly_revenue"] = current_revenue
        venture["open_pipeline_count"] = body.pipeline_count
        venture["active_users"] = body.active_users
        venture["automation_coverage"] = body.automation_coverage
        venture["returning_customers"] = returning
        venture["churned_customers"] = churned
        venture["revenue_trend"] = revenue_trend
        venture["retention_signal"] = retention_signal
        venture["weekly_update_freshness_days"] = 0
        if body.stage:
            venture["stage"] = body.stage

        event = append_log(RUNTIME_ROOT, "kpi_snapshots", {
            "venture_id": venture_id,
            "weekly_revenue": current_revenue,
            "revenue_trend": revenue_trend,
            "retention_signal": retention_signal,
            "returning_customers": returning,
            "churned_customers": churned,
        })
        save_state(RUNTIME_ROOT, state)
        refreshed = refresh_ops_artifacts(RUNTIME_ROOT)

    return {"event": event, "tick": refreshed.get("tick", {})}


@app.post("/api/governance-propose")
def governance_propose(body: GovernanceProposeRequest, _=Depends(verify_token)):
    with ops_write_lock(RUNTIME_ROOT):
        event = append_log(RUNTIME_ROOT, "governance_proposals", {
            "proposal_id": body.proposal_id,
            "proposal_type": body.proposal_type,
            "venture_id": body.venture_id,
            "description": body.description,
            "status": "open",
            "votes_for": 0,
            "votes_against": 0,
            "note": body.note,
        })
        refreshed = refresh_ops_artifacts(RUNTIME_ROOT)
    return {"event": event, "tick": refreshed.get("tick", {})}


@app.post("/api/governance-vote")
def governance_vote(body: GovernanceVoteRequest, _=Depends(verify_token)):
    with ops_write_lock(RUNTIME_ROOT):
        event = append_log(RUNTIME_ROOT, "governance_votes", {
            "proposal_id": body.proposal_id,
            "decision": body.decision,
            "weight": body.weight,
            "note": body.note,
        })
        refreshed = refresh_ops_artifacts(RUNTIME_ROOT)
    return {"event": event, "tick": refreshed.get("tick", {})}


@app.post("/api/governance-tally")
def governance_tally(body: GovernanceTallyRequest, _=Depends(verify_token)):
    with ops_write_lock(RUNTIME_ROOT):
        proposals = read_log(RUNTIME_ROOT, "governance_proposals")
        votes = read_log(RUNTIME_ROOT, "governance_votes")
        quorum = body.quorum

        open_proposals: dict[str, dict] = {}
        for p in proposals:
            pid = str(p.get("proposal_id", ""))
            if pid:
                open_proposals[pid] = p

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
                continue
            outcome = "passed" if tally["for"] > tally["against"] else "rejected"
            resolution = {
                "proposal_id": pid,
                "outcome": outcome,
                "votes_for": tally["for"],
                "votes_against": tally["against"],
                "quorum_met": tally["total"],
            }
            resolved.append(resolution)
            append_log(RUNTIME_ROOT, "governance_resolutions", resolution)

        state = load_state(RUNTIME_ROOT)
        passed_count = sum(1 for r in resolved if r["outcome"] == "passed")
        state.setdefault("governance", {})
        state["governance"]["total_resolved"] = int(state["governance"].get("total_resolved") or 0) + len(resolved)
        state["governance"]["total_passed"] = int(state["governance"].get("total_passed") or 0) + passed_count
        save_state(RUNTIME_ROOT, state)
        refreshed = refresh_ops_artifacts(RUNTIME_ROOT)

    return {
        "resolved_count": len(resolved),
        "resolutions": resolved,
        "governance": state["governance"],
        "tick": refreshed.get("tick", {}),
    }


@app.post("/api/venture-exit")
def venture_exit(body: VentureExitRequest, _=Depends(verify_token)):
    with ops_write_lock(RUNTIME_ROOT):
        state = load_state(RUNTIME_ROOT)
        venture = _venture(state, body.venture_id)
        venture["status"] = "archived"
        venture["stage"] = "archived"
        venture["exit_reason"] = body.reason
        venture["exit_lesson"] = body.lesson

        retro = {
            "venture_id": venture["venture_id"],
            "retrospective_id": f"exit-{venture['venture_id']}",
            "scope": "shutdown",
            "outcome": body.outcome,
            "lesson": body.lesson,
            "failure_mode": body.failure_mode,
        }
        append_log(RUNTIME_ROOT, "retrospectives", retro)

        exit_event = {
            "venture_id": venture["venture_id"],
            "reason": body.reason,
            "outcome": body.outcome,
            "lesson": body.lesson,
            "final_revenue": float(venture.get("weekly_revenue") or 0),
            "final_active_users": int(venture.get("active_users") or 0),
        }
        event = append_log(RUNTIME_ROOT, "venture_exits", exit_event)
        save_state(RUNTIME_ROOT, state)
        refreshed = refresh_ops_artifacts(RUNTIME_ROOT)

    return {
        "venture": venture,
        "exit_event": event,
        "retrospective": retro,
        "tick": refreshed.get("tick", {}),
    }


# ---------------------------------------------------------------------------
# Scheduler & Events
# ---------------------------------------------------------------------------

_scheduler_instance = None


class SchedulerStartRequest(BaseModel):
    interval: int = Field(300, ge=10, le=86400, description="Tick interval in seconds")


@app.get("/api/events")
def get_events(
    event_type: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    events = read_log(RUNTIME_ROOT, "events")
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]
    events.sort(key=lambda e: e.get("timestamp") or e.get("created_at") or "", reverse=True)
    return events[:limit]


@app.get("/api/scheduler/status")
def get_scheduler_status() -> dict[str, Any]:
    global _scheduler_instance
    if _scheduler_instance is None:
        return {"running": False, "tick_count": 0, "last_tick_at": None}
    return _scheduler_instance.status


@app.post("/api/scheduler/start", dependencies=[Depends(verify_token)])
async def start_scheduler(body: SchedulerStartRequest) -> dict[str, Any]:
    global _scheduler_instance
    if _scheduler_instance is not None and _scheduler_instance._running:
        raise HTTPException(400, "Scheduler already running")

    from .scheduler import IncubatorScheduler
    import asyncio

    _scheduler_instance = IncubatorScheduler(
        runtime_root=RUNTIME_ROOT,
        tick_interval_seconds=body.interval,
    )
    asyncio.create_task(_scheduler_instance.run())
    return {"status": "started", "interval": body.interval}


@app.post("/api/scheduler/stop", dependencies=[Depends(verify_token)])
def stop_scheduler() -> dict[str, Any]:
    global _scheduler_instance
    if _scheduler_instance is None or not _scheduler_instance._running:
        raise HTTPException(400, "Scheduler not running")
    _scheduler_instance.stop()
    return {"status": "stopping"}


# ---------------------------------------------------------------------------
# LLM Agent Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/agents/status")
def get_agents_status() -> dict[str, Any]:
    """Return which LLM agents are available and last evaluation info."""
    try:
        from .llm_client import get_client
        client = get_client()
        llm_available = client.available
    except Exception:
        llm_available = False

    agents_info = {
        "llm_available": llm_available,
        "agents": [
            {"name": "VentureAnalystAgent", "type": "evaluation", "available": llm_available},
            {"name": "ReviewAgent", "type": "review", "available": llm_available},
            {"name": "AdmissionsAgent", "type": "admissions", "available": llm_available},
            {"name": "BottleneckDiagnosticAgent", "type": "diagnostic", "available": llm_available},
        ],
    }
    # Include last LLM results from scheduler if available
    global _scheduler_instance
    if _scheduler_instance is not None:
        agents_info["last_llm_results"] = _scheduler_instance._last_llm_results
    return agents_info


@app.post("/api/evaluate/{venture_id}", dependencies=[Depends(verify_token)])
async def evaluate_venture(venture_id: str) -> dict[str, Any]:
    """Trigger on-demand LLM evaluation of a specific venture."""
    try:
        from .agents import VentureAnalystAgent
    except ImportError:
        raise HTTPException(501, "Agent module not available")

    agent = VentureAnalystAgent()
    if not agent.available:
        raise HTTPException(503, "LLM not available — set ANTHROPIC_API_KEY")

    state = load_state(RUNTIME_ROOT)
    ventures = [v for v in state.get("ventures", []) if isinstance(v, dict) and str(v.get("venture_id", "")) == venture_id]
    if not ventures:
        raise HTTPException(404, f"Venture {venture_id} not found")

    venture = ventures[0]
    result = await agent.evaluate(venture)
    if result is None:
        raise HTTPException(502, "LLM evaluation failed")

    # Persist the assessment
    with ops_write_lock(RUNTIME_ROOT):
        state = load_state(RUNTIME_ROOT)
        for v in state.get("ventures", []):
            if isinstance(v, dict) and str(v.get("venture_id", "")) == venture_id:
                v["llm_assessment"] = {
                    "scores": result.scores,
                    "reasoning": result.reasoning,
                    "recommendation": result.recommendation,
                    "confidence": result.confidence,
                    "evaluated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).replace(microsecond=0).isoformat(),
                }
                break
        save_state(RUNTIME_ROOT, state)

    return {
        "venture_id": venture_id,
        "llm": {
            "scores": result.scores,
            "reasoning": result.reasoning,
            "recommendation": result.recommendation,
            "confidence": result.confidence,
        },
        "heuristic": {
            "compound_score": venture.get("compound_score"),
            "bottleneck": venture.get("bottleneck"),
        },
    }


# ---------------------------------------------------------------------------
# Notification Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/notifications")
def get_notifications(limit: int = 50) -> list[dict[str, Any]]:
    """Return recent notification history."""
    records = read_log(RUNTIME_ROOT, "notifications")
    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records[:limit]


@app.get("/api/notifications/channels")
def get_notification_channels() -> dict[str, Any]:
    """Return available notification channels and current routing rules."""
    global _scheduler_instance
    if _scheduler_instance is not None and _scheduler_instance._notification_router is not None:
        router = _scheduler_instance._notification_router
        return {
            "channels": router.available_channels,
            "rule_count": len(router.rules),
            "rules": [
                {"event_type": r.event_type, "channels": r.channels, "min_severity": r.min_severity}
                for r in router.rules
            ],
        }
    # Standalone check
    try:
        from .notification_router import NotificationRouter
        router = NotificationRouter(RUNTIME_ROOT)
        return {
            "channels": router.available_channels,
            "rule_count": len(router.rules),
            "rules": [
                {"event_type": r.event_type, "channels": r.channels, "min_severity": r.min_severity}
                for r in router.rules
            ],
        }
    except Exception:
        return {"channels": [], "rule_count": 0, "rules": []}


# ---------------------------------------------------------------------------
# Enrichment Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/enrichment/status")
def get_enrichment_status() -> dict[str, Any]:
    """Return enrichment source availability and recent activity."""
    try:
        from .enrichment import VentureEnricher
        enricher = VentureEnricher()
        available = enricher.available
        sources = enricher.source_names
    except Exception:
        available = False
        sources = []

    recent = read_log(RUNTIME_ROOT, "enrichment")
    recent.sort(key=lambda r: r.get("enriched_at", ""), reverse=True)

    return {
        "available": available,
        "sources": sources,
        "recent_enrichments": recent[:10],
    }


@app.post("/api/enrichment/run", dependencies=[Depends(verify_token)])
async def run_enrichment() -> dict[str, Any]:
    """Trigger manual enrichment of all due ventures."""
    try:
        from .enrichment import VentureEnricher
        enricher = VentureEnricher()
    except ImportError:
        raise HTTPException(501, "Enrichment module not available")

    if not enricher.available:
        raise HTTPException(503, "No enrichment sources configured")

    records = await enricher.enrich_portfolio(RUNTIME_ROOT)
    return {
        "enriched_count": len(records),
        "records": [r.to_dict() for r in records],
    }


@app.post("/api/enrichment/venture/{venture_id}", dependencies=[Depends(verify_token)])
async def enrich_single_venture(venture_id: str) -> dict[str, Any]:
    """Trigger enrichment for a specific venture."""
    try:
        from .enrichment import VentureEnricher
        enricher = VentureEnricher()
    except ImportError:
        raise HTTPException(501, "Enrichment module not available")

    if not enricher.available:
        raise HTTPException(503, "No enrichment sources configured")

    state = load_state(RUNTIME_ROOT)
    ventures = [v for v in state.get("ventures", []) if isinstance(v, dict) and str(v.get("venture_id", "")) == venture_id]
    if not ventures:
        raise HTTPException(404, f"Venture {venture_id} not found")

    record = await enricher.enrich_venture(ventures[0])
    if record is None:
        return {"venture_id": venture_id, "enriched": False, "reason": "No results from sources"}

    # Persist
    with ops_write_lock(RUNTIME_ROOT):
        state = load_state(RUNTIME_ROOT)
        for v in state.get("ventures", []):
            if isinstance(v, dict) and str(v.get("venture_id", "")) == venture_id:
                v["enrichment_data"] = record.to_dict()
                break
        save_state(RUNTIME_ROOT, state)

    return {"venture_id": venture_id, "enriched": True, "record": record.to_dict()}


# ---------------------------------------------------------------------------
# Feedback Loop Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/feedback/status")
def get_feedback_status() -> dict[str, Any]:
    """Return feedback loop status and last cycle results."""
    recent = read_log(RUNTIME_ROOT, "feedback_cycles")
    recent.sort(key=lambda r: r.get("cycle_at", ""), reverse=True)

    state = load_state(RUNTIME_ROOT)
    return {
        "scoring_weights": state.get("scoring_weights", {}),
        "last_cycle": state.get("last_feedback_cycle"),
        "total_cycles": len(recent),
        "recent_cycles": recent[:5],
    }


@app.post("/api/feedback/run", dependencies=[Depends(verify_token)])
async def run_feedback() -> dict[str, Any]:
    """Trigger a manual feedback cycle."""
    try:
        from .feedback_loop import run_feedback_cycle
    except ImportError:
        raise HTTPException(501, "Feedback module not available")

    result = await run_feedback_cycle(RUNTIME_ROOT)
    return result


@app.get("/api/feedback/accuracy")
def get_accuracy() -> dict[str, Any]:
    """Compute and return current prediction accuracy."""
    try:
        from .outcome_tracker import compute_accuracy
    except ImportError:
        raise HTTPException(501, "Outcome tracker not available")

    report = compute_accuracy(RUNTIME_ROOT)
    return report.to_dict()


# ---------------------------------------------------------------------------
# Agent Orchestration Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/orchestration/status")
def get_orchestration_status() -> dict[str, Any]:
    """Return agent orchestration status."""
    try:
        from .orchestrator import AgentOrchestrator, QUEUE_TO_AGENT
        orchestrator = AgentOrchestrator()
        agents = orchestrator.available_agents
        llm = orchestrator.llm_available
    except Exception:
        agents = []
        llm = False

    recent_actions = read_log(RUNTIME_ROOT, "agent_actions")
    recent_actions.sort(key=lambda r: r.get("created_at", ""), reverse=True)

    human_queue = read_log(RUNTIME_ROOT, "human_review_queue")

    return {
        "agents": agents,
        "llm_available": llm,
        "queue_mapping": dict(QUEUE_TO_AGENT) if agents else {},
        "recent_actions": recent_actions[:20],
        "human_review_pending": len(human_queue),
        "human_review_items": human_queue[-10:],
    }


@app.post("/api/orchestration/run", dependencies=[Depends(verify_token)])
async def run_orchestration() -> dict[str, Any]:
    """Trigger a manual orchestration cycle."""
    try:
        from .orchestrator import AgentOrchestrator
    except ImportError:
        raise HTTPException(501, "Orchestrator module not available")

    orchestrator = AgentOrchestrator()
    result = await orchestrator.process_queues(RUNTIME_ROOT)
    return result.to_dict()


@app.get("/api/orchestration/human-queue")
def get_human_queue() -> list[dict[str, Any]]:
    """Return items waiting for human review."""
    items = read_log(RUNTIME_ROOT, "human_review_queue")
    items.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return items


class NotificationTestRequest(BaseModel):
    channel: str = "console"


@app.post("/api/notifications/test", dependencies=[Depends(verify_token)])
async def test_notification(body: NotificationTestRequest) -> dict[str, Any]:
    """Send a test notification to verify channel connectivity."""
    try:
        from .notification_router import NotificationRouter
        router = NotificationRouter(RUNTIME_ROOT)
        record = await router.send_test(body.channel)
        return record.to_dict()
    except Exception as exc:
        raise HTTPException(500, f"Notification test failed: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import uvicorn
    port = int(os.environ.get("VIBE_API_PORT", "4177"))
    print(f"[vibe-api] FastAPI serving on http://127.0.0.1:{port}")
    print(f"[vibe-api] runtime_root = {RUNTIME_ROOT}")
    print(f"[vibe-api] auth = {'enabled' if API_TOKEN else 'disabled (set VIBE_API_TOKEN)'}")
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
