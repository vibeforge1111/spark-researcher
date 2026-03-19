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
