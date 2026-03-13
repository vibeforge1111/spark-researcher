from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from .benchmarks import list_speedrun_tasks, resolve_speedrun_task, resolve_task_state_path
from .emulator import (
    DEFAULT_POLICY,
    DEFAULT_PROFILE,
    DEFAULT_TASK,
    EmulatorConfig,
    configured_bootrom_path,
    configured_rom_path,
    configured_state_path,
    deterministic_scaffold,
    emulator_status,
    run_policy_session,
)

DEFAULT_STEPS = 18
DEFAULT_TICKS = 24


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _write(path: str, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mutations(payload: dict[str, Any]) -> dict[str, str]:
    candidate = payload.get("candidate", {})
    raw = candidate.get("mutations", {}) if isinstance(candidate, dict) else {}
    return {str(key): str(value) for key, value in raw.items()}


def _row_metrics(row: dict[str, Any]) -> dict[str, Any]:
    metrics = row.get("metrics", {})
    return metrics if isinstance(metrics, dict) else {}


def _row_result(row: dict[str, Any]) -> dict[str, Any]:
    result = row.get("chip_result", {})
    return result if isinstance(result, dict) else {}


def _row_mutations(row: dict[str, Any]) -> dict[str, str]:
    return {
        str(item.get("name", "")): str(item.get("value", ""))
        for item in row.get("applied_mutations", [])
        if isinstance(item, dict)
    }


def _score_from_environment(mutations: dict[str, str]) -> dict[str, Any]:
    rom_path = configured_rom_path()
    task_id = mutations.get("task_id", DEFAULT_TASK)
    task_spec = resolve_speedrun_task(task_id)
    policy_id = mutations.get("policy_id", task_spec.default_policy_id or DEFAULT_POLICY)
    startup_action = mutations.get("startup_action", task_spec.startup_action)
    ticks_per_action = int(mutations.get("tick_stride", str(task_spec.tick_stride or DEFAULT_TICKS)) or DEFAULT_TICKS)
    benchmark_profile = mutations.get("benchmark_profile", task_spec.benchmark_profile or DEFAULT_PROFILE)
    if rom_path is None:
        return deterministic_scaffold(policy_id, startup_action, ticks_per_action, task_id, benchmark_profile)
    generic_state_path = configured_state_path()
    task_state_path, task_state_source = resolve_task_state_path(task_id, generic_path=generic_state_path)
    config = EmulatorConfig(
        rom_path=rom_path,
        window="null",
        ticks_per_action=max(1, ticks_per_action),
        startup_ticks=max(0, int(os.environ.get("POKEMON_EVAL_STARTUP_TICKS", str(task_spec.startup_ticks)) or str(task_spec.startup_ticks))),
        action_hold=max(1, int(os.environ.get("POKEMON_EVAL_ACTION_HOLD", str(task_spec.action_hold)) or str(task_spec.action_hold))),
        bootrom_path=configured_bootrom_path(),
        load_state_path=task_state_path,
        load_state_source=task_state_source,
        save_state_out=None,
    )
    steps = max(1, int(os.environ.get("POKEMON_EVAL_STEPS", str(task_spec.steps or DEFAULT_STEPS)) or str(task_spec.steps or DEFAULT_STEPS)))
    return run_policy_session(
        config,
        policy_id=policy_id,
        steps=steps,
        startup_action=startup_action,
        task_id=task_id,
        benchmark_profile=benchmark_profile,
    )


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    mutations = _mutations(payload)
    score = _score_from_environment(mutations)
    stdout = "\n".join(
        [
            f"pokemon_progress_score: {score['pokemon_progress_score']}",
            f"exploration_score: {score['exploration_score']}",
            f"interaction_score: {score['interaction_score']}",
            f"screen_novelty: {score['screen_novelty']}",
            f"emulator_connected: {score['emulator_connected']}",
            f"verdict_confidence: {score['verdict_confidence']}",
        ]
    )
    result = {
        "claim": "Pokemon play quality should be judged on real emulator-connected state change, not only policy rhetoric.",
        "verdict": score["verdict"],
        "mechanism": score["mechanism"],
        "boundary": score["boundary"],
        "recommended_next_step": score["recommended_next_step"],
        "evidence_lane": score["evidence_lane"],
        "comparison_class": score["comparison_class"],
        "lesson": score["mechanism"],
        "next_probe": "Prefer save-state-backed runs after the emulator is connected and a stable early-game scene is available.",
        "task_id": score.get("task_id", DEFAULT_TASK),
        "benchmark_profile": score.get("benchmark_profile", DEFAULT_PROFILE),
        "task_state_loaded": bool(score.get("task_state_loaded", False)),
        "task_state_path": str(score.get("task_state_path", "")),
        "task_state_source": str(score.get("task_state_source", "missing")),
    }
    return {
        "returncode": 0,
        "stdout": stdout,
        "stderr": "",
        "metrics": {
            "pokemon_progress_score": score["pokemon_progress_score"],
            "exploration_score": score["exploration_score"],
            "interaction_score": score["interaction_score"],
            "screen_novelty": score["screen_novelty"],
            "emulator_connected": score["emulator_connected"],
            "verdict_confidence": score["verdict_confidence"],
        },
        "result": result,
    }


def suggest(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in payload.get("ledger_rows", []) if isinstance(row, dict)]
    tested = {str(row.get("candidate_id", "")) for row in rows}
    seeds = [
        {
            "candidate_id": "speedrun-intro-boot",
            "candidate_summary": "Boot into a speedrun intro policy that mashes through opening text and movement setup.",
            "hypothesis": "A start-assisted wander opener should create the strongest intro baseline for later route tasks.",
            "mutations": {"policy_id": "wander", "startup_action": "start", "tick_stride": "24", "task_id": "intro_boot", "benchmark_profile": "speedrun_intro"},
        },
        {
            "candidate_id": "speedrun-leave-bedroom",
            "candidate_summary": "Bias toward fast room exit movement for the first route fragment.",
            "hypothesis": "A right-biased route policy should outperform symmetric wandering on the leave-bedroom task.",
            "mutations": {"policy_id": "right_scout", "startup_action": "none", "tick_stride": "24", "task_id": "leave_bedroom", "benchmark_profile": "speedrun_route"},
        },
        {
            "candidate_id": "speedrun-text-mash",
            "candidate_summary": "Stress the text-mashing lane for intro dialogue speed.",
            "hypothesis": "A shorter stride plus menu mashing should improve intro dialogue throughput.",
            "mutations": {"policy_id": "menu_mash", "startup_action": "start", "tick_stride": "12", "task_id": "text_mash", "benchmark_profile": "speedrun_menuing"},
        },
        {
            "candidate_id": "speedrun-oak-lab-entry",
            "candidate_summary": "Probe a stable movement pattern for entering Oak's lab route cleanly.",
            "hypothesis": "A slower edge scan may create more stable opening-route positioning for Oak's lab entry.",
            "mutations": {"policy_id": "edge_scan", "startup_action": "none", "tick_stride": "36", "task_id": "oak_lab_entry", "benchmark_profile": "speedrun_route"},
        },
        {
            "candidate_id": "speedrun-menu-fastpath",
            "candidate_summary": "Probe whether a start-then-wander policy improves menu fastpath consistency.",
            "hypothesis": "A startup A press followed by movement should improve menu-fastpath readiness for speedrun control.",
            "mutations": {"policy_id": "start_then_wander", "startup_action": "a", "tick_stride": "24", "task_id": "menu_fastpath", "benchmark_profile": "speedrun_menuing"},
        },
    ]
    suggestions = [item for item in seeds if item["candidate_id"] not in tested]
    reasons = [
        "Pokemon speedrun work should start with emulator-connected policies tied to named route or menu tasks.",
        "Prefer tasks that can later be re-run from a save state instead of treating cold boot randomness as doctrine.",
    ]
    if not emulator_status()["rom_configured"]:
        reasons.insert(0, "No ROM is configured yet, so frontier work should focus on getting the emulator connected first.")
    limit = max(1, int(payload.get("limit", 3) or 3))
    return {
        "baseline_metric": None,
        "reasons": reasons[:limit],
        "suggestions": suggestions[:limit],
    }


def _best_row(rows: list[dict[str, Any]], comparison_class: str | None = None) -> dict[str, Any] | None:
    scored = [
        row
        for row in rows
        if isinstance(_row_metrics(row).get("pokemon_progress_score"), (int, float))
        and (comparison_class is None or str(_row_result(row).get("comparison_class", "")) == comparison_class)
    ]
    if not scored:
        return None
    return max(scored, key=lambda row: float(_row_metrics(row).get("pokemon_progress_score", 0.0) or 0.0))


def packets(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in payload.get("ledger_rows", []) if isinstance(row, dict)]
    best = _best_row(rows, "benchmark_grounded") or _best_row(rows)
    status = emulator_status()
    documents: list[dict[str, str]] = []
    if best is None:
        documents.append(
            {
                "kind": "exploratory_frontier",
                "memory_tier": "exploratory_frontier",
                "slug": "pokemon-emulator-bootstrap",
                "title": "Pokemon Emulator Bootstrap",
                "content": "\n".join(
                    [
                        "# Pokemon Emulator Bootstrap",
                        "",
                        f"- pyboy_available: `{status['pyboy_available']}`",
                        f"- rom_configured: `{status['rom_configured']}`",
                        "- next_step: connect a legal ROM and run the baseline policy.",
                    ]
                ),
            }
        )
        documents.append(
            {
                "kind": "grounded_boundary",
                "memory_tier": "grounded_boundary",
                "slug": "pokemon-no-rom-boundary",
                "title": "Pokemon No ROM Boundary",
                "content": "Do not treat the Pokemon player as benchmark-grounded until a legal ROM is configured and real emulator sessions are running.",
            }
        )
        return {"documents": documents}

    metrics = _row_metrics(best)
    result = _row_result(best)
    mutations = _row_mutations(best)
    comparison_class = str(result.get("comparison_class", "heuristic_frontier"))
    evidence_tier = "benchmark_evidence" if comparison_class == "benchmark_grounded" else "exploratory_frontier"
    documents.append(
        {
            "kind": "benchmark_evidence" if comparison_class == "benchmark_grounded" else "exploratory_frontier",
            "memory_tier": evidence_tier,
            "slug": "pokemon-best-run-" + str(best.get("candidate_id", "baseline")),
            "title": "Pokemon Best Run Evidence",
            "content": "\n".join(
                [
                    "# Pokemon Best Run Evidence",
                    "",
                    f"- candidate_id: `{best.get('candidate_id', 'baseline')}`",
                    f"- pokemon_progress_score: `{metrics.get('pokemon_progress_score', 'n/a')}`",
                    f"- exploration_score: `{metrics.get('exploration_score', 'n/a')}`",
                    f"- interaction_score: `{metrics.get('interaction_score', 'n/a')}`",
                    f"- screen_novelty: `{metrics.get('screen_novelty', 'n/a')}`",
                    f"- comparison_class: `{comparison_class}`",
                    f"- recommended_next_step: `{result.get('recommended_next_step', 'n/a')}`",
                    f"- task_id: `{result.get('task_id', mutations.get('task_id', DEFAULT_TASK))}`",
                    f"- benchmark_profile: `{result.get('benchmark_profile', mutations.get('benchmark_profile', DEFAULT_PROFILE))}`",
                    f"- task_state_loaded: `{result.get('task_state_loaded', 'n/a')}`",
                    f"- task_state_source: `{result.get('task_state_source', 'n/a')}`",
                    f"- mutations: `{json.dumps(mutations, sort_keys=True)}`",
                ]
            ),
        }
    )
    if comparison_class == "benchmark_grounded":
        documents.append(
            {
                "kind": "grounded_doctrine",
                "memory_tier": "grounded_doctrine",
                "slug": "pokemon-doctrine-best-policy",
                "title": "Pokemon Best Policy Doctrine",
                "content": "\n".join(
                    [
                        "# Pokemon Best Policy Doctrine",
                        "",
                        "Use emulator-connected policy evaluation as the inner truth surface.",
                        f"The current leading policy is `{mutations.get('policy_id', DEFAULT_POLICY)}` on task `{mutations.get('task_id', DEFAULT_TASK)}` under profile `{mutations.get('benchmark_profile', DEFAULT_PROFILE)}`.",
                        f"Task state loaded: `{result.get('task_state_loaded', False)}` via `{result.get('task_state_source', 'missing')}`.",
                        "Promotion beyond this requires save-state-backed route and menu benchmarks, not just raw wandering.",
                    ]
                ),
            }
        )
    else:
        documents.append(
            {
                "kind": "grounded_boundary",
                "memory_tier": "grounded_boundary",
                "slug": "pokemon-heuristic-boundary",
                "title": "Pokemon Heuristic Boundary",
                "content": "A disconnected or scaffold-only Pokemon run is exploratory only. Do not treat it as benchmark-grounded play skill.",
            }
        )
    documents.append(
        {
            "kind": "exploratory_frontier",
            "memory_tier": "exploratory_frontier",
            "slug": "pokemon-next-probe",
            "title": "Pokemon Next Probe",
            "content": "Next strong move: load a save state near a stable gameplay scene and evaluate route quality, menu quality, and battle quality separately.",
        }
    )
    return {"documents": documents}


def _render_rows(rows: list[dict[str, Any]], predicate: Any) -> list[str]:
    lines: list[str] = []
    for row in rows:
        if not predicate(row):
            continue
        metrics = _row_metrics(row)
        result = _row_result(row)
        lines.extend(
            [
                f"## {row.get('candidate_id', 'unknown')}",
                "",
                f"- pokemon_progress_score: `{metrics.get('pokemon_progress_score', 'n/a')}`",
                f"- verdict: `{row.get('verdict', 'n/a')}`",
                f"- comparison_class: `{result.get('comparison_class', 'n/a')}`",
                f"- recommended_next_step: `{result.get('recommended_next_step', 'n/a')}`",
                "",
            ]
        )
    return lines


def _task_coverage_lines(task_registry: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for task in task_registry:
        lines.extend(
            [
                f"## {task['task_id']}",
                "",
                f"- display_name: `{task['display_name']}`",
                f"- benchmark_profile: `{task['benchmark_profile']}`",
                f"- default_policy_id: `{task['default_policy_id']}`",
                f"- state_available: `{task['state_available']}`",
                f"- state_path: `{task['state_path'] or 'missing'}`",
                f"- preview_available: `{task['preview_available']}`",
                f"- preview_path: `{task['preview_path']}`",
                f"- env_override: `{task['task_state_env_var']}`",
                f"- notes: {task['notes']}",
                "",
            ]
        )
    return lines


def watchtower(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in payload.get("ledger_rows", []) if isinstance(row, dict)]
    status = emulator_status()
    best = _best_row(rows, "benchmark_grounded") or _best_row(rows)
    best_any = _best_row(rows)
    policy_counts = Counter(_row_mutations(row).get("policy_id", "baseline") for row in rows)
    suggestion_packet = suggest({"ledger_rows": rows, "limit": 5})
    best_id = str(best.get("candidate_id", "none")) if best else "none"
    best_score = _row_metrics(best).get("pokemon_progress_score", "n/a") if best else "n/a"
    best_result = _row_result(best) if best else {}
    best_any_score = _row_metrics(best_any).get("pokemon_progress_score", "n/a") if best_any else "n/a"
    task_registry = list_speedrun_tasks()
    available_states = sum(1 for task in task_registry if task.get("state_available"))
    pages = [
        {
            "path": "07-Domains/Pokemon Player/Home.md",
            "content": "\n".join(
                [
                    "# Pokemon Player",
                    "",
                    f"- runs: `{len(rows)}`",
                    f"- best_candidate: `{best_id}`",
                    f"- best_benchmark_score: `{best_score}`",
                    f"- best_overall_score: `{best_any_score}`",
                    f"- pyboy_available: `{status['pyboy_available']}`",
                    f"- rom_configured: `{status['rom_configured']}`",
                    f"- speedrun_task_states_available: `{available_states}/{len(task_registry)}`",
                    f"- best_task_id: `{best_result.get('task_id', 'none')}`",
                    f"- best_task_state_loaded: `{best_result.get('task_state_loaded', False)}`",
                    "",
                    "## Pages",
                    "",
                    "- [[07-Domains/Pokemon Player/Doctrine]]",
                    "- [[07-Domains/Pokemon Player/Boundaries]]",
                    "- [[07-Domains/Pokemon Player/Benchmark Evidence]]",
                    "- [[07-Domains/Pokemon Player/Frontier Probes]]",
                    "- [[07-Domains/Pokemon Player/Why It Lost]]",
                    "- [[07-Domains/Pokemon Player/Coverage Map]]",
                    "- [[07-Domains/Pokemon Player/Real-World Validation]]",
                ]
            ),
        },
        {
            "path": "07-Domains/Pokemon Player/Doctrine.md",
            "content": "\n".join(
                [
                    "# Doctrine",
                    "",
                    "The current inner truth surface is emulator-connected state change, not subjective gameplay vibes.",
                    "",
                    f"- best_candidate: `{best_id}`",
                    f"- best_benchmark_score: `{best_score}`",
                    f"- best_task_id: `{best_result.get('task_id', 'none')}`",
                    f"- best_task_state_loaded: `{best_result.get('task_state_loaded', False)}`",
                    f"- best_task_state_source: `{best_result.get('task_state_source', 'missing')}`",
                    "",
                    "Long-horizon doctrine should only be promoted once save-state-backed route, text, menu, and battle tasks exist.",
                ]
            ),
        },
        {
            "path": "07-Domains/Pokemon Player/Boundaries.md",
            "content": "\n".join(
                [
                    "# Boundaries",
                    "",
                    "- No legal ROM configured means the chip is exploratory only.",
                    "- Cold-boot movement novelty is not enough to claim strong Pokemon speedrun skill.",
                    "- Route completion, text speed, menu speed, and battle speed still need richer benchmarks.",
                ]
            ),
        },
        {
            "path": "07-Domains/Pokemon Player/Benchmark Evidence.md",
            "content": "\n".join(
                [
                    "# Benchmark Evidence",
                    "",
                    f"- benchmark_ready_tasks: `{available_states}/{len(task_registry)}`",
                    "",
                    *(
                        _render_rows(
                            rows,
                            lambda row: str(_row_result(row).get("comparison_class", "")) == "benchmark_grounded",
                        )
                        or ["- No benchmark-grounded emulator runs recorded yet."]
                    ),
                ]
            ),
        },
        {
            "path": "07-Domains/Pokemon Player/Frontier Probes.md",
            "content": "\n".join(
                [
                    "# Frontier Probes",
                    "",
                    *(
                        [
                            f"## {item['candidate_id']}\n\n- summary: {item['candidate_summary']}\n- hypothesis: {item['hypothesis']}\n- mutations: `{json.dumps(item['mutations'], sort_keys=True)}`\n"
                            for item in suggestion_packet.get("suggestions", [])
                        ]
                        or ["- No frontier probes suggested yet."]
                    ),
                ]
            ),
        },
        {
            "path": "07-Domains/Pokemon Player/Why It Lost.md",
            "content": "\n".join(
                [
                    "# Why It Lost",
                    "",
                    *(
                        _render_rows(
                            rows,
                            lambda row: str(row.get("verdict", "")) == "regressed" or str(_row_result(row).get("verdict", "")) == "reject",
                        )
                        or ["- No losing candidates recorded yet."]
                    ),
                ]
            ),
        },
        {
            "path": "07-Domains/Pokemon Player/Coverage Map.md",
            "content": "\n".join(
                [
                    "# Coverage Map",
                    "",
                    f"- task_count: `{len(task_registry)}`",
                    f"- state_backed_task_count: `{available_states}`",
                    "",
                    "## Task Registry",
                    "",
                    *(_task_coverage_lines(task_registry) or ["- No speedrun tasks registered."]),
                    "",
                    "## Policy Counts",
                    "",
                    *[f"- {policy}: `{count}` runs" for policy, count in sorted(policy_counts.items())],
                    "",
                    f"- emulator_connected: `{status['rom_configured'] and status['pyboy_available']}`",
                ]
            ),
        },
        {
            "path": "07-Domains/Pokemon Player/Real-World Validation.md",
            "content": "\n".join(
                [
                    "# Real-World Validation",
                    "",
                    "Current task readiness in Obsidian should track which tasks are truly save-state-backed and which are still cold-boot probes.",
                    "",
                    "To treat this chip as a serious speedrun learner, add save-state-backed tasks such as:",
                    "",
                    "- leave the opening room cleanly",
                    "- navigate the first town without menu stalls",
                    "- talk to required NPCs",
                    "- win early scripted battles",
                    "- recover from menu or collision errors",
                    "",
                    "The current scaffold is connected to the emulator, but it is not yet a world-class Pokemon speedrun benchmark system.",
                ]
            ),
        },
    ]
    return {"pages": pages}


def main() -> None:
    parser = argparse.ArgumentParser(prog="domain_chip_pokemon_player")
    parser.add_argument("hook", choices=["evaluate", "suggest", "packets", "watchtower"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = _load(args.input)
    response = {
        "evaluate": evaluate,
        "suggest": suggest,
        "packets": packets,
        "watchtower": watchtower,
    }[args.hook](payload)
    _write(args.output, response)


if __name__ == "__main__":
    main()
