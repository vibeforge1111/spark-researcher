"""Tests for the Vibe Vibe API server and snapshot builder."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import pytest

# Make the chip package importable
SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from domain_chip_vibe_incubator.ops_loop import (
    append_log,
    load_state,
    ops_write_lock,
    refresh_ops_artifacts,
    save_state,
)


@pytest.fixture()
def runtime_root(tmp_path: Path):
    """Create a minimal runtime root with seed state for testing."""
    artifacts = tmp_path / "artifacts" / "incubator_os"
    artifacts.mkdir(parents=True)

    state = {
        "ventures": [
            {
                "venture_id": "test-venture",
                "label": "Test Venture",
                "venture_model": "agentic_saas",
                "customer_surface": "founder_backoffice",
                "distribution_engine": "operator_content",
                "build_stack": "template_factory",
                "validation_motion": "paid_pilot",
                "trust_model": "manual_review_first",
                "operating_cadence": "daily_ship",
                "venture_theme": "test theme",
                "stage": "validation",
                "status": "active",
                "automation_coverage": 0.75,
                "weekly_revenue": 500,
                "customer_conversations_this_week": 3,
                "paid_signals_this_week": 2,
                "active_users": 5,
                "weekly_update_freshness_days": 1,
                "last_review_days": 2,
                "trust_review_status": "green",
                "open_pipeline_count": 3,
                "open_pipeline_value": 3600,
            }
        ],
        "applications": [
            {
                "application_id": "pending-app",
                "label": "Pending App",
                "founder_id": "f-001",
                "status": "pending",
                "venture_model": "agentic_saas",
                "customer_surface": "creators",
                "distribution_engine": "community_loops",
                "venture_theme": "test pending",
            }
        ],
        "founders": [
            {"founder_id": "f-001", "label": "Test Founder", "status": "active", "venture_ids": ["test-venture"]},
        ],
        "queues": {"build": [], "validation": [], "doctrine": []},
        "batches": [
            {
                "batch_id": "batch-test",
                "label": "Test Batch",
                "status": "active",
                "venture_ids": ["test-venture"],
                "sprint_week": 1,
                "duration_weeks": 8,
            }
        ],
        "program": {
            "name": "Vibe Incubator",
            "operator_mode": "solo_plus_agents",
            "batch_style": "cohort",
            "active_portfolio_cap": 3,
        },
    }
    (artifacts / "state.json").write_text(json.dumps(state), encoding="utf-8")

    return tmp_path


def _refresh(root: str | Path) -> None:
    """Generate all artifacts from state."""
    refresh_ops_artifacts(str(root))


class TestSnapshotBuilder:
    def test_artifacts_created(self, runtime_root: Path) -> None:
        _refresh(runtime_root)
        artifacts = runtime_root / "artifacts" / "incubator_os"
        assert (artifacts / "latest_tick.json").exists()
        assert (artifacts / "queue_snapshot.json").exists()
        assert (artifacts / "execution_snapshot.json").exists()

    def test_latest_tick_has_metrics(self, runtime_root: Path) -> None:
        _refresh(runtime_root)
        tick = json.loads((runtime_root / "artifacts" / "incubator_os" / "latest_tick.json").read_text("utf-8"))
        assert "metrics" in tick
        metrics = tick["metrics"]
        assert "incubator_compound_score" in metrics
        assert 0 <= metrics["incubator_compound_score"] <= 1

    def test_queue_snapshot_counts(self, runtime_root: Path) -> None:
        _refresh(runtime_root)
        qs = json.loads((runtime_root / "artifacts" / "incubator_os" / "queue_snapshot.json").read_text("utf-8"))
        assert qs["active_portfolio_count"] == 1

    def test_score_with_zero_values(self, runtime_root: Path) -> None:
        """Ensure zero-valued fields are treated as 0, not as defaults (falsy-zero bug)."""
        state = load_state(str(runtime_root))
        venture = state["ventures"][0]
        venture["weekly_update_freshness_days"] = 0
        venture["last_review_days"] = 0
        venture["automation_coverage"] = 0
        save_state(str(runtime_root), state)
        _refresh(runtime_root)
        tick = json.loads((runtime_root / "artifacts" / "incubator_os" / "latest_tick.json").read_text("utf-8"))
        # review_hygiene should be high when freshness is 0 days (just updated)
        assert tick["metrics"]["ops_review_hygiene_score"] >= 0.85


class TestAdmissionsReviewRoundTrip:
    def test_invite_creates_venture(self, runtime_root: Path) -> None:
        root = str(runtime_root)
        _refresh(runtime_root)

        with ops_write_lock(root):
            state = load_state(root)
            app = next(a for a in state["applications"] if a["application_id"] == "pending-app")
            app["venture_id"] = "new-from-invite"
            state.setdefault("ventures", []).append({
                "venture_id": "new-from-invite",
                "label": app["label"],
                "venture_model": app["venture_model"],
                "customer_surface": app["customer_surface"],
                "distribution_engine": app["distribution_engine"],
                "stage": "proof",
                "status": "active",
                "automation_coverage": 0.5,
            })
            app["status"] = "admitted"
            app["decision"] = "invite"
            save_state(root, state)
            refresh_ops_artifacts(root)

        state2 = load_state(root)
        venture_ids = [v["venture_id"] for v in state2["ventures"]]
        assert "new-from-invite" in venture_ids
        admitted = next(a for a in state2["applications"] if a["application_id"] == "pending-app")
        assert admitted["status"] == "admitted"

    def test_waitlist_does_not_create_venture(self, runtime_root: Path) -> None:
        root = str(runtime_root)
        _refresh(runtime_root)

        with ops_write_lock(root):
            state = load_state(root)
            app = next(a for a in state["applications"] if a["application_id"] == "pending-app")
            app["status"] = "waitlisted"
            app["decision"] = "waitlist"
            save_state(root, state)

        state2 = load_state(root)
        venture_ids = [v["venture_id"] for v in state2["ventures"]]
        assert len(venture_ids) == 1  # only the original


class TestApiServer:
    """Tests that start the API server against a temp runtime root."""

    @pytest.fixture(autouse=True)
    def _start_server(self, runtime_root: Path, monkeypatch: pytest.MonkeyPatch):
        _refresh(runtime_root)

        # Monkeypatch the module-level constants
        import domain_chip_vibe_incubator.api as api_mod
        monkeypatch.setattr(api_mod, "RUNTIME_ROOT", str(runtime_root))
        monkeypatch.setattr(api_mod, "ARTIFACTS", runtime_root / "artifacts" / "incubator_os")

        server = HTTPServer(("127.0.0.1", 0), api_mod.ApiHandler)
        self.port = server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield
        server.shutdown()

    def _get(self, path: str) -> dict:
        resp = urllib.request.urlopen(f"{self.base}{path}")
        return json.loads(resp.read())

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())

    def test_health(self) -> None:
        result = self._get("/api/health")
        assert result["status"] == "ok"

    def test_status(self) -> None:
        result = self._get("/api/status")
        assert result["active_ventures"] == 1

    def test_dashboard_snapshot(self) -> None:
        result = self._get("/api/dashboard")
        assert "generatedAt" in result
        assert len(result["ventures"]) == 1

    def test_admissions_review_via_api(self) -> None:
        result = self._post("/api/admissions-review", {
            "application_id": "pending-app",
            "decision": "waitlist",
            "note": "Test via API",
        })
        assert result["event"]["decision"] == "waitlist"

    def test_404_on_unknown_route(self) -> None:
        try:
            self._get("/api/nonexistent")
            assert False, "Should have raised"
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
