from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BASE = {
    "roblox_delivery_score": 0.29,
    "pipeline_coverage_score": 0.25,
    "gameplay_confidence_score": 0.22,
    "evidence_readiness_score": 0.18,
    "liveops_readiness_score": 0.07,
}

PHASES = {
    "foundation": {"delivery": 0.18, "pipeline": 0.17, "gameplay": 0.04, "evidence": 0.12, "liveops": 0.01},
    "prototype": {"delivery": 0.12, "pipeline": 0.10, "gameplay": 0.18, "evidence": 0.10, "liveops": 0.03},
    "vertical_slice": {"delivery": 0.09, "pipeline": 0.07, "gameplay": 0.16, "evidence": 0.08, "liveops": 0.05},
    "launch_prep": {"delivery": 0.04, "pipeline": 0.05, "gameplay": 0.09, "evidence": 0.07, "liveops": 0.08},
    "live_ops": {"delivery": 0.01, "pipeline": 0.03, "gameplay": 0.05, "evidence": 0.04, "liveops": 0.18},
}

AUTOMATION = {
    "design_packets": {"delivery": 0.05, "pipeline": 0.14, "gameplay": 0.04, "evidence": 0.06, "liveops": 0.00},
    "repo_scaffold": {"delivery": 0.18, "pipeline": 0.10, "gameplay": 0.03, "evidence": 0.06, "liveops": 0.00},
    "studio_sync": {"delivery": 0.16, "pipeline": 0.05, "gameplay": 0.12, "evidence": 0.05, "liveops": 0.01},
    "playtest_telemetry": {"delivery": 0.07, "pipeline": 0.04, "gameplay": 0.13, "evidence": 0.18, "liveops": 0.06},
    "economy_tuning": {"delivery": 0.03, "pipeline": 0.04, "gameplay": 0.08, "evidence": 0.12, "liveops": 0.10},
    "live_service": {"delivery": 0.02, "pipeline": 0.02, "gameplay": 0.05, "evidence": 0.09, "liveops": 0.18},
}

EVIDENCE = {
    "synthetic": {"delivery": 0.08, "pipeline": 0.02, "gameplay": 0.00, "evidence": 0.08, "liveops": -0.02},
    "bench": {"delivery": 0.04, "pipeline": 0.02, "gameplay": 0.05, "evidence": 0.14, "liveops": 0.00},
    "playtest": {"delivery": 0.02, "pipeline": 0.02, "gameplay": 0.08, "evidence": 0.16, "liveops": 0.05},
    "live": {"delivery": -0.04, "pipeline": 0.01, "gameplay": 0.04, "evidence": 0.10, "liveops": 0.16},
}

GENRES = {
    "obby": {"delivery": 0.10, "pipeline": 0.02, "gameplay": 0.10, "evidence": 0.04, "liveops": 0.01},
    "tycoon": {"delivery": 0.03, "pipeline": 0.05, "gameplay": 0.10, "evidence": 0.06, "liveops": 0.08},
    "simulator": {"delivery": 0.03, "pipeline": 0.08, "gameplay": 0.08, "evidence": 0.05, "liveops": 0.10},
    "battler": {"delivery": -0.03, "pipeline": 0.03, "gameplay": 0.12, "evidence": 0.05, "liveops": 0.04},
    "social_rp": {"delivery": -0.02, "pipeline": 0.10, "gameplay": 0.06, "evidence": 0.06, "liveops": 0.10},
}

TEAMS = {
    "solo_dev": {"delivery": 0.07, "pipeline": 0.02, "gameplay": 0.07, "evidence": 0.02, "liveops": 0.00},
    "founder_plus_ai": {"delivery": 0.10, "pipeline": 0.12, "gameplay": 0.08, "evidence": 0.05, "liveops": 0.01},
    "micro_studio": {"delivery": 0.08, "pipeline": 0.04, "gameplay": 0.09, "evidence": 0.04, "liveops": 0.06},
    "design_partner": {"delivery": 0.04, "pipeline": 0.10, "gameplay": 0.10, "evidence": 0.04, "liveops": 0.01},
}

ROADMAP = [
    {
        "candidate_id": "foundation-obby-design-packets",
        "candidate_summary": "Lock the Roblox flywheel around a single low-complexity obby build brief and asset contract.",
        "hypothesis": "The shortest path is to harden prompts, design packets, and repo conventions before any deep runtime automation.",
        "mutations": {
            "production_phase": "foundation",
            "automation_lane": "design_packets",
            "evidence_lane": "synthetic",
            "game_genre": "obby",
            "team_mode": "founder_plus_ai",
            "build_theme": "obby brief packet",
        },
    },
    {
        "candidate_id": "foundation-obby-repo-scaffold",
        "candidate_summary": "Generate a Roblox repo scaffold with Rojo-ready structure and a simple obby core loop contract.",
        "hypothesis": "Repo scaffold is the first real execution surface because it turns design intent into a working project layout.",
        "mutations": {
            "production_phase": "foundation",
            "automation_lane": "repo_scaffold",
            "evidence_lane": "bench",
            "game_genre": "obby",
            "team_mode": "founder_plus_ai",
            "build_theme": "obby repo scaffold",
        },
    },
    {
        "candidate_id": "prototype-obby-studio-sync",
        "candidate_summary": "Connect scaffolded output to Studio iteration and test a playable obby prototype.",
        "hypothesis": "Studio sync is the first point where the flywheel can verify that generated code and content actually compose into play.",
        "mutations": {
            "production_phase": "prototype",
            "automation_lane": "studio_sync",
            "evidence_lane": "playtest",
            "game_genre": "obby",
            "team_mode": "founder_plus_ai",
            "build_theme": "obby studio sync",
        },
    },
    {
        "candidate_id": "vertical-tycoon-playtest",
        "candidate_summary": "Expand into a tycoon vertical slice only after the platform can observe player flow and economy interactions.",
        "hypothesis": "Tycoon scope is the first honest step beyond an obby once playtest telemetry is working.",
        "mutations": {
            "production_phase": "vertical_slice",
            "automation_lane": "playtest_telemetry",
            "evidence_lane": "playtest",
            "game_genre": "tycoon",
            "team_mode": "micro_studio",
            "build_theme": "tycoon playtest telemetry",
        },
    },
    {
        "candidate_id": "launch-simulator-economy",
        "candidate_summary": "Prepare simulator launch gates by scoring economy balance and release-readiness requirements.",
        "hypothesis": "Economy tuning only becomes credible after telemetry, QA, and release packaging exist.",
        "mutations": {
            "production_phase": "launch_prep",
            "automation_lane": "economy_tuning",
            "evidence_lane": "playtest",
            "game_genre": "simulator",
            "team_mode": "micro_studio",
            "build_theme": "simulator economy gate",
        },
    },
    {
        "candidate_id": "live-social-rp-service",
        "candidate_summary": "Attempt live-service planning only after the lower lanes are grounded by publish and telemetry systems.",
        "hypothesis": "Live-service automation is the last lane, not the starting point, for a Roblox flywheel.",
        "mutations": {
            "production_phase": "live_ops",
            "automation_lane": "live_service",
            "evidence_lane": "live",
            "game_genre": "social_rp",
            "team_mode": "micro_studio",
            "build_theme": "social live ops",
        },
    },
]


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _write(path: str, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mutations(payload: dict[str, Any]) -> dict[str, str]:
    candidate = payload.get("candidate", {})
    raw = candidate.get("mutations", {}) if isinstance(candidate, dict) else {}
    return {str(key): str(value) for key, value in raw.items()}


def _clamp(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


def _score(mutations: dict[str, str]) -> dict[str, Any]:
    phase = mutations.get("production_phase", "foundation")
    automation = mutations.get("automation_lane", "design_packets")
    evidence = mutations.get("evidence_lane", "synthetic")
    genre = mutations.get("game_genre", "obby")
    team = mutations.get("team_mode", "founder_plus_ai")

    phase_spec = PHASES.get(phase, {})
    automation_spec = AUTOMATION.get(automation, {})
    evidence_spec = EVIDENCE.get(evidence, {})
    genre_spec = GENRES.get(genre, {})
    team_spec = TEAMS.get(team, {})

    delivery = BASE["roblox_delivery_score"]
    pipeline = BASE["pipeline_coverage_score"]
    gameplay = BASE["gameplay_confidence_score"]
    evidence_score = BASE["evidence_readiness_score"]
    liveops = BASE["liveops_readiness_score"]

    delivery += phase_spec.get("delivery", 0.0) + automation_spec.get("delivery", 0.0) + evidence_spec.get("delivery", 0.0) + genre_spec.get("delivery", 0.0) + team_spec.get("delivery", 0.0)
    pipeline += phase_spec.get("pipeline", 0.0) + automation_spec.get("pipeline", 0.0) + evidence_spec.get("pipeline", 0.0) + genre_spec.get("pipeline", 0.0) + team_spec.get("pipeline", 0.0)
    gameplay += phase_spec.get("gameplay", 0.0) + automation_spec.get("gameplay", 0.0) + evidence_spec.get("gameplay", 0.0) + genre_spec.get("gameplay", 0.0) + team_spec.get("gameplay", 0.0)
    evidence_score += phase_spec.get("evidence", 0.0) + automation_spec.get("evidence", 0.0) + evidence_spec.get("evidence", 0.0) + genre_spec.get("evidence", 0.0) + team_spec.get("evidence", 0.0)
    liveops += phase_spec.get("liveops", 0.0) + automation_spec.get("liveops", 0.0) + evidence_spec.get("liveops", 0.0) + genre_spec.get("liveops", 0.0) + team_spec.get("liveops", 0.0)

    reasons: list[str] = []

    if phase == "foundation" and automation == "repo_scaffold":
        delivery += 0.08
        pipeline += 0.06
        reasons.append("foundation plus repo scaffold is the strongest current path because the platform can already manage bounded generation and review.")
    if phase == "foundation" and automation == "design_packets":
        pipeline += 0.05
        reasons.append("design packets fit the current Spark strengths around planning, packets, and explicit task routing.")
    if phase == "prototype" and automation == "studio_sync":
        gameplay += 0.08
        delivery += 0.04
        reasons.append("prototype plus Studio sync is the first honest proof that generated output can become playable.")
    if phase in {"prototype", "vertical_slice"} and automation == "playtest_telemetry":
        evidence_score += 0.08
        gameplay += 0.04
        reasons.append("playtest telemetry is the bridge from synthetic planning into observed gameplay evidence.")
    if phase == "launch_prep" and automation == "economy_tuning":
        liveops += 0.05
        evidence_score += 0.02
        reasons.append("economy tuning belongs near launch prep after playtest instrumentation exists.")
    if phase == "live_ops" and automation == "live_service":
        liveops += 0.08
        reasons.append("live service becomes meaningful only after the lower lanes are grounded.")
    if genre == "tycoon" and automation == "economy_tuning":
        gameplay += 0.04
        liveops += 0.06
        reasons.append("tycoon games benefit directly from economy tuning once the base loop is stable.")
    if genre == "simulator" and automation == "playtest_telemetry":
        evidence_score += 0.04
        reasons.append("simulator scope needs strong telemetry because progression tuning drives retention.")
    if genre == "obby" and automation in {"design_packets", "repo_scaffold", "studio_sync"}:
        delivery += 0.04
        gameplay += 0.02
        reasons.append("obby is the smallest genre for proving the brief-to-playable pipeline.")

    if phase in {"launch_prep", "live_ops"} and evidence == "synthetic":
        delivery -= 0.12
        evidence_score -= 0.10
        liveops -= 0.08
        reasons.append("advanced release work without playtest or live evidence is not credible.")
    if automation == "live_service" and evidence != "live":
        liveops -= 0.14
        evidence_score -= 0.05
        reasons.append("live-service automation without live data would be theater.")
    if phase == "foundation" and automation in {"economy_tuning", "live_service"}:
        delivery -= 0.10
        gameplay -= 0.05
        reasons.append("economy and live-service work are premature before scaffold and gameplay foundations exist.")
    if genre in {"battler", "social_rp"} and phase == "foundation":
        delivery -= 0.06
        gameplay -= 0.03
        reasons.append("high-complexity genres are a poor first proving ground for the initial flywheel.")
    if evidence == "live" and phase != "live_ops":
        delivery -= 0.04
        reasons.append("live evidence should appear after release, not before the release surfaces exist.")

    delivery = _clamp(delivery)
    pipeline = _clamp(pipeline)
    gameplay = _clamp(gameplay)
    evidence_score = _clamp(evidence_score)
    liveops = _clamp(liveops)

    roblox_delivery = _clamp(
        delivery * 0.30
        + pipeline * 0.20
        + gameplay * 0.22
        + evidence_score * 0.18
        + liveops * 0.10
    )

    metric_map = {
        "roblox_delivery_score": roblox_delivery,
        "pipeline_coverage_score": pipeline,
        "gameplay_confidence_score": gameplay,
        "evidence_readiness_score": evidence_score,
        "liveops_readiness_score": liveops,
    }
    weakest_metric = min(metric_map, key=metric_map.get)
    if weakest_metric == "roblox_delivery_score":
        weakest_metric = "pipeline_coverage_score"

    next_steps = {
        "pipeline_coverage_score": "build_repo_scaffold_and_asset_contracts",
        "gameplay_confidence_score": "ship_playable_core_loop_in_studio",
        "evidence_readiness_score": "instrument_local_playtest_loop",
        "liveops_readiness_score": "delay_live_ops_and_build_release_gates",
    }
    bottlenecks = {
        "pipeline_coverage_score": "repo_and_asset_pipeline_gap",
        "gameplay_confidence_score": "playable_loop_gap",
        "evidence_readiness_score": "playtest_instrumentation_gap",
        "liveops_readiness_score": "release_and_liveops_gap",
    }
    mechanism = {
        "pipeline_coverage_score": "Spark already supports bounded planning and queueing, so the next leverage is turning plans into a consistent Roblox project scaffold.",
        "gameplay_confidence_score": "The system must prove it can move generated output into Roblox Studio and produce a working loop, not just clean plans.",
        "evidence_readiness_score": "Without observed playtest signals, the flywheel cannot distinguish a plausible prototype from a genuinely working game loop.",
        "liveops_readiness_score": "Publishing, retention, and live-service tuning should remain downstream until scaffold, gameplay, and telemetry lanes exist.",
    }
    boundary = {
        "pipeline_coverage_score": "Do not expand genre or live-service scope while the repo and asset pipeline is still manual.",
        "gameplay_confidence_score": "Do not trust generated code until a playable in-Studio loop exists and can be iterated repeatedly.",
        "evidence_readiness_score": "Do not promote design beliefs into doctrine without playtest instrumentation and grounded retention signals.",
        "liveops_readiness_score": "Do not claim end-to-end Roblox autonomy without publish, rollback, moderation, and live analytics surfaces.",
    }

    if roblox_delivery >= 0.74 and evidence_score >= 0.58 and liveops >= 0.34:
        verdict = "approve"
        recommended_next_step = "promote_foundation_and_begin_real_tooling"
        evidence_lane = "benchmark_grounded"
    elif roblox_delivery >= 0.58:
        verdict = "defer"
        recommended_next_step = next_steps[weakest_metric]
        evidence_lane = "exploratory_frontier"
    else:
        verdict = "reject"
        recommended_next_step = next_steps[weakest_metric]
        evidence_lane = "grounded_boundary"

    verdict_confidence = _clamp(0.42 + roblox_delivery * 0.28 + evidence_score * 0.18 + pipeline * 0.12)
    summary = " ".join(reasons[:3]) if reasons else "Current score is dominated by missing Roblox-specific services rather than planning quality."

    return {
        "roblox_delivery_score": roblox_delivery,
        "pipeline_coverage_score": pipeline,
        "gameplay_confidence_score": gameplay,
        "evidence_readiness_score": evidence_score,
        "liveops_readiness_score": liveops,
        "verdict_confidence": verdict_confidence,
        "verdict": verdict,
        "recommended_next_step": recommended_next_step,
        "bottleneck": bottlenecks[weakest_metric],
        "mechanism": mechanism[weakest_metric],
        "boundary": boundary[weakest_metric],
        "summary": summary,
        "evidence_lane": evidence_lane,
    }


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    mutations = _mutations(payload)
    metrics = _score(mutations)
    stdout = "\n".join(
        [
            f"roblox_delivery_score: {metrics['roblox_delivery_score']}",
            f"pipeline_coverage_score: {metrics['pipeline_coverage_score']}",
            f"gameplay_confidence_score: {metrics['gameplay_confidence_score']}",
            f"evidence_readiness_score: {metrics['evidence_readiness_score']}",
            f"liveops_readiness_score: {metrics['liveops_readiness_score']}",
            f"verdict_confidence: {metrics['verdict_confidence']}",
            f"summary: {metrics['summary']}",
        ]
    )
    return {
        "returncode": 0,
        "stdout": stdout,
        "stderr": "",
        "metrics": {
            key: metrics[key]
            for key in (
                "roblox_delivery_score",
                "pipeline_coverage_score",
                "gameplay_confidence_score",
                "evidence_readiness_score",
                "liveops_readiness_score",
                "verdict_confidence",
            )
        },
        "result": {
            "claim": "The Roblox flywheel should expand from planning to scaffold to Studio to playtest before it attempts release or live-service autonomy.",
            "verdict": metrics["verdict"],
            "mechanism": metrics["mechanism"],
            "boundary": metrics["boundary"],
            "recommended_next_step": metrics["recommended_next_step"],
            "bottleneck": metrics["bottleneck"],
            "summary": metrics["summary"],
            "evidence_lane": metrics["evidence_lane"],
        },
    }


def _tested_signatures(payload: dict[str, Any], command_name: str) -> set[tuple[str, str, str, str, str]]:
    tested: set[tuple[str, str, str, str, str]] = set()
    rows = payload.get("ledger_rows", [])
    rows = rows if isinstance(rows, list) else []
    for row in rows:
        if str(row.get("command_name", "")) != command_name:
            continue
        mutations = {
            str(item.get("name", "")): str(item.get("value", ""))
            for item in row.get("applied_mutations", [])
            if isinstance(item, dict)
        }
        tested.add(
            (
                mutations.get("production_phase", ""),
                mutations.get("automation_lane", ""),
                mutations.get("evidence_lane", ""),
                mutations.get("game_genre", ""),
                mutations.get("team_mode", ""),
            )
        )
    for item in payload.get("candidate_trials", []):
        if not isinstance(item, dict):
            continue
        mutations = item.get("mutations", {})
        if not isinstance(mutations, dict):
            continue
        tested.add(
            (
                str(mutations.get("production_phase", "")),
                str(mutations.get("automation_lane", "")),
                str(mutations.get("evidence_lane", "")),
                str(mutations.get("game_genre", "")),
                str(mutations.get("team_mode", "")),
            )
        )
    return tested


def suggest(payload: dict[str, Any]) -> dict[str, Any]:
    command_name = str(payload.get("command_name", "research"))
    limit = max(1, int(payload.get("limit", 3) or 3))
    tested = _tested_signatures(payload, command_name)

    rows = payload.get("ledger_rows", [])
    rows = rows if isinstance(rows, list) else []
    improved_rows = [row for row in rows if str(row.get("command_name", "")) == command_name and isinstance(row.get("metric_value"), (int, float))]
    improved_rows.sort(key=lambda item: float(item.get("metric_value", 0.0) or 0.0), reverse=True)
    release_foundation_ready = False
    for row in improved_rows:
        mutations = {
            str(item.get("name", "")): str(item.get("value", ""))
            for item in row.get("applied_mutations", [])
            if isinstance(item, dict)
        }
        if mutations.get("automation_lane") in {"playtest_telemetry", "economy_tuning"} and float(row.get("metric_value", 0.0) or 0.0) >= 0.66:
            release_foundation_ready = True
            break

    suggestions: list[dict[str, Any]] = []
    queued: set[tuple[str, str, str, str, str]] = set()
    reasons: list[str] = []

    if improved_rows:
        top = improved_rows[0]
        top_mutations = {
            str(item.get("name", "")): str(item.get("value", ""))
            for item in top.get("applied_mutations", [])
            if isinstance(item, dict)
        }
        if top_mutations.get("automation_lane") in {"design_packets", "repo_scaffold"}:
            next_candidate = ROADMAP[2]
            sig = (
                next_candidate["mutations"]["production_phase"],
                next_candidate["mutations"]["automation_lane"],
                next_candidate["mutations"]["evidence_lane"],
                next_candidate["mutations"]["game_genre"],
                next_candidate["mutations"]["team_mode"],
            )
            if sig not in tested:
                suggestions.append(next_candidate)
                queued.add(sig)
                reasons.append("The best current lane is still pre-Studio, so the next bounded probe is Studio-connected gameplay.")
        if top_mutations.get("automation_lane") == "studio_sync":
            next_candidate = ROADMAP[3]
            sig = (
                next_candidate["mutations"]["production_phase"],
                next_candidate["mutations"]["automation_lane"],
                next_candidate["mutations"]["evidence_lane"],
                next_candidate["mutations"]["game_genre"],
                next_candidate["mutations"]["team_mode"],
            )
            if sig not in tested:
                suggestions.append(next_candidate)
                queued.add(sig)
                reasons.append("Once Studio sync is in place, the next honest lane is telemetry-grounded playtesting.")
        if top_mutations.get("automation_lane") == "playtest_telemetry":
            next_candidate = ROADMAP[4]
            sig = (
                next_candidate["mutations"]["production_phase"],
                next_candidate["mutations"]["automation_lane"],
                next_candidate["mutations"]["evidence_lane"],
                next_candidate["mutations"]["game_genre"],
                next_candidate["mutations"]["team_mode"],
            )
            if sig not in tested:
                suggestions.append(next_candidate)
                queued.add(sig)
                reasons.append("After playtest telemetry, the flywheel can evaluate launch-prep and economy surfaces.")

    for candidate in ROADMAP:
        if len(suggestions) >= limit:
            break
        muts = candidate["mutations"]
        if muts["automation_lane"] == "live_service" and not release_foundation_ready:
            continue
        sig = (
            muts["production_phase"],
            muts["automation_lane"],
            muts["evidence_lane"],
            muts["game_genre"],
            muts["team_mode"],
        )
        if sig in tested or sig in queued:
            continue
        suggestions.append(candidate)
        queued.add(sig)
        reasons.append(f"Progress the implementation roadmap by testing the next missing lane `{candidate['candidate_id']}`.")

    baseline_metric = None
    for row in rows:
        if str(row.get("command_name", "")) == command_name and not row.get("applied_mutations"):
            value = row.get("metric_value")
            if isinstance(value, (int, float)):
                baseline_metric = float(value)
                break

    return {
        "baseline_metric": baseline_metric,
        "reasons": reasons[:limit],
        "suggestions": suggestions[:limit],
    }


def packets(payload: dict[str, Any]) -> dict[str, Any]:
    candidate = payload.get("candidate", {})
    candidate = candidate if isinstance(candidate, dict) else {}
    candidate_id = str(candidate.get("candidate_id", "global-baseline"))
    metrics = _score(_mutations(payload))

    documents = [
        {
            "kind": "benchmark_evidence",
            "memory_tier": "benchmark_evidence",
            "slug": f"roblox-evidence-{candidate_id}",
            "title": f"{candidate_id} Roblox Delivery Evidence",
            "content": "\n".join(
                [
                    f"# {candidate_id} Roblox Delivery Evidence",
                    "",
                    f"- evidence_lane: {metrics['evidence_lane']}",
                    f"- roblox_delivery_score: {metrics['roblox_delivery_score']}",
                    f"- pipeline_coverage_score: {metrics['pipeline_coverage_score']}",
                    f"- gameplay_confidence_score: {metrics['gameplay_confidence_score']}",
                    f"- evidence_readiness_score: {metrics['evidence_readiness_score']}",
                    f"- liveops_readiness_score: {metrics['liveops_readiness_score']}",
                    f"- verdict: {metrics['verdict']}",
                    f"- bottleneck: {metrics['bottleneck']}",
                    f"- recommended_next_step: {metrics['recommended_next_step']}",
                    "",
                    "## Claim",
                    "",
                    "The Roblox chip should only expand one lane beyond the current lowest reliable surface.",
                    "",
                    "## Mechanism",
                    "",
                    metrics["mechanism"],
                    "",
                    "## Boundary",
                    "",
                    metrics["boundary"],
                ]
            ),
        }
    ]

    if metrics["verdict"] == "approve":
        documents.append(
            {
                "kind": "grounded_doctrine",
                "memory_tier": "grounded_doctrine",
                "slug": f"roblox-doctrine-{candidate_id}",
                "title": f"{candidate_id} Roblox Doctrine Candidate",
                "content": "Promote this lane only as a narrow doctrine: foundation before Studio, Studio before playtest, playtest before launch.",
            }
        )
    elif metrics["verdict"] == "defer":
        documents.append(
            {
                "kind": "exploratory_frontier",
                "memory_tier": "exploratory_frontier",
                "slug": f"roblox-frontier-{candidate_id}",
                "title": f"{candidate_id} Roblox Frontier Note",
                "content": f"Candidate is promising but incomplete. Next step: {metrics['recommended_next_step']}.",
            }
        )
    else:
        documents.append(
            {
                "kind": "grounded_boundary",
                "memory_tier": "grounded_boundary",
                "slug": f"roblox-boundary-{candidate_id}",
                "title": f"{candidate_id} Roblox Boundary",
                "content": f"Boundary confirmed: {metrics['boundary']}",
            }
        )

    return {"documents": documents}


def watchtower(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary", {})
    summary = summary if isinstance(summary, dict) else {}
    run_count = int(summary.get("run_count", 0) or 0)
    best_by_metric = summary.get("best_by_metric", {})
    best_by_metric = best_by_metric if isinstance(best_by_metric, dict) else {}
    best_delivery = best_by_metric.get("roblox_delivery_score", {})
    best_delivery = best_delivery if isinstance(best_delivery, dict) else {}

    return {
        "pages": [
            {
                "path": "07-Domains/Roblox Development/Home.md",
                "content": "\n".join(
                    [
                        "# Roblox Development",
                        "",
                        "- chip: `domain-chip-roblox-development`",
                        "- total runs: `" + str(run_count) + "`",
                        "- best roblox_delivery_score: `" + str(best_delivery.get("value", "n/a")) + "`",
                        "",
                        "## Current Honest State",
                        "",
                        "- Spark core already has bounded autoloop, queueing, packets, and watchtower surfaces.",
                        "- Roblox-specific execution is still mostly unimplemented.",
                        "- The active flywheel should stay narrow: design packets -> repo scaffold -> Studio sync -> playtest telemetry -> release gates -> live ops.",
                        "",
                        "## Read Next",
                        "",
                        "- [[07-Domains/Roblox Development/System State]]",
                        "- [[07-Domains/Roblox Development/Remaining Work]]",
                    ]
                ),
            },
            {
                "path": "07-Domains/Roblox Development/System State.md",
                "content": "\n".join(
                    [
                        "# System State",
                        "",
                        "## Reusable Spark Core",
                        "",
                        "- bounded autoloop execution",
                        "- chip hook validation and invocation",
                        "- frontier queue generation",
                        "- packet and watchtower emission",
                        "",
                        "## Missing Roblox Services",
                        "",
                        "- project scaffold and Rojo synchronization",
                        "- Luau lint, test, and formatting pipeline",
                        "- asset import/export and content assembly",
                        "- playtest telemetry and retention metrics",
                        "- publish, rollback, moderation, and live-service rails",
                    ]
                ),
            },
            {
                "path": "07-Domains/Roblox Development/Remaining Work.md",
                "content": "\n".join(
                    [
                        "# Remaining Work",
                        "",
                        "1. Scaffold a Roblox project from a Spark brief.",
                        "2. Add Studio and Rojo sync so generated code becomes playable.",
                        "3. Add local Luau quality gates and smoke tests.",
                        "4. Capture playtest evidence before launch-prep work.",
                        "5. Add publish, rollback, and live-ops instrumentation last.",
                    ]
                ),
            },
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="domain_chip_roblox_development")
    parser.add_argument("hook", choices=["evaluate", "suggest", "packets", "watchtower"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = _load(args.input)
    dispatch = {
        "evaluate": evaluate,
        "suggest": suggest,
        "packets": packets,
        "watchtower": watchtower,
    }
    result = dispatch[args.hook](payload)
    _write(args.output, result)


if __name__ == "__main__":
    main()
