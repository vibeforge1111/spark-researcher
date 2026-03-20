from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from domain_chip_roblox_development.cli import evaluate, packets, suggest


def test_evaluate_prefers_foundation_repo_scaffold() -> None:
    baseline = evaluate({"candidate": {"mutations": {}}})
    focused = evaluate(
        {
            "candidate": {
                "mutations": {
                    "production_phase": "foundation",
                    "automation_lane": "repo_scaffold",
                    "evidence_lane": "bench",
                    "game_genre": "obby",
                    "team_mode": "founder_plus_ai",
                }
            }
        }
    )
    assert focused["metrics"]["roblox_delivery_score"] > baseline["metrics"]["roblox_delivery_score"]
    assert focused["result"]["recommended_next_step"] in {
        "build_repo_scaffold_and_asset_contracts",
        "ship_playable_core_loop_in_studio",
        "instrument_local_playtest_loop",
        "delay_live_ops_and_build_release_gates",
        "promote_foundation_and_begin_real_tooling",
    }


def test_suggest_advances_from_scaffold_to_studio_sync() -> None:
    packet = suggest(
        {
            "command_name": "research",
            "limit": 3,
            "ledger_rows": [
                {
                    "command_name": "research",
                    "metric_value": 0.61,
                    "applied_mutations": [
                        {"name": "production_phase", "value": "foundation"},
                        {"name": "automation_lane", "value": "repo_scaffold"},
                        {"name": "evidence_lane", "value": "bench"},
                        {"name": "game_genre", "value": "obby"},
                        {"name": "team_mode", "value": "founder_plus_ai"},
                    ],
                }
            ],
            "candidate_trials": [],
        }
    )
    assert packet["suggestions"]
    assert packet["suggestions"][0]["mutations"]["automation_lane"] == "studio_sync"


def test_packets_emit_boundary_or_frontier_documents() -> None:
    packet = packets(
        {
            "candidate": {
                "candidate_id": "launch-too-early",
                "mutations": {
                    "production_phase": "launch_prep",
                    "automation_lane": "live_service",
                    "evidence_lane": "synthetic",
                    "game_genre": "social_rp",
                    "team_mode": "micro_studio",
                },
            }
        }
    )
    kinds = {doc["kind"] for doc in packet["documents"]}
    assert "benchmark_evidence" in kinds
    assert "grounded_boundary" in kinds or "exploratory_frontier" in kinds


def test_suggest_does_not_jump_to_live_service_without_release_foundation() -> None:
    packet = suggest(
        {
            "command_name": "research",
            "limit": 5,
            "ledger_rows": [
                {
                    "command_name": "research",
                    "metric_value": 0.68,
                    "applied_mutations": [
                        {"name": "production_phase", "value": "prototype"},
                        {"name": "automation_lane", "value": "studio_sync"},
                        {"name": "evidence_lane", "value": "playtest"},
                        {"name": "game_genre", "value": "obby"},
                        {"name": "team_mode", "value": "founder_plus_ai"},
                    ],
                }
            ],
            "candidate_trials": [],
        }
    )
    automation_lanes = [item["mutations"]["automation_lane"] for item in packet["suggestions"]]
    assert "live_service" not in automation_lanes
    assert len(automation_lanes) == len(set(automation_lanes))
