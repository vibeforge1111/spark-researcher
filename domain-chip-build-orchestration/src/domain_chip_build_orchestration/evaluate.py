"""Domain-specific scoring for build orchestration and development velocity."""
from __future__ import annotations


def _c(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


# ── Base scores ──────────────────────────────────────────────────────
BASE = {
    "build_velocity_score": 0.11,
    "approach_leverage_score": 0.14,
    "priority_clarity_score": 0.13,
    "quality_confidence_score": 0.15,
    "team_efficiency_score": 0.14,
    "iteration_throughput_score": 0.12,
    "reusability_score": 0.13,
}

# ── Build approach scoring ───────────────────────────────────────────
# Keys: al=approach_leverage, re=reusability, it=iteration_throughput, qc=quality_confidence
APPROACH = {
    "template_factory": {"al": 0.18, "re": 0.20, "it": 0.16, "qc": 0.10, "label": "Template factory"},
    "agent_workflow": {"al": 0.20, "re": 0.16, "it": 0.18, "qc": 0.12, "label": "Agent workflow"},
    "custom_development": {"al": 0.12, "re": 0.08, "it": 0.08, "qc": 0.19, "label": "Custom development"},
    "low_code": {"al": 0.15, "re": 0.12, "it": 0.19, "qc": 0.08, "label": "Low-code"},
    "api_integration": {"al": 0.16, "re": 0.17, "it": 0.14, "qc": 0.14, "label": "API integration"},
}

# ── Priority method scoring ──────────────────────────────────────────
# Keys: pc=priority_clarity, it=iteration_throughput, te=team_efficiency, qc=quality_confidence
PRIORITY = {
    "impact_effort_matrix": {"pc": 0.18, "it": 0.14, "te": 0.12, "qc": 0.10, "label": "Impact-effort matrix"},
    "user_request": {"pc": 0.12, "it": 0.16, "te": 0.10, "qc": 0.08, "label": "User request"},
    "revenue_impact": {"pc": 0.16, "it": 0.12, "te": 0.14, "qc": 0.12, "label": "Revenue impact"},
    "technical_debt": {"pc": 0.14, "it": 0.08, "te": 0.08, "qc": 0.16, "label": "Technical debt"},
    "security_first": {"pc": 0.15, "it": 0.06, "te": 0.09, "qc": 0.20, "label": "Security first"},
}

# ── Quality gate scoring ─────────────────────────────────────────────
# Keys: qc=quality_confidence, it=iteration_throughput, re=reusability, al=approach_leverage
QUALITY = {
    "minimal_viable": {"qc": 0.08, "it": 0.18, "re": 0.06, "al": 0.10, "label": "Minimal viable"},
    "production_grade": {"qc": 0.16, "it": 0.12, "re": 0.14, "al": 0.14, "label": "Production grade"},
    "enterprise_ready": {"qc": 0.22, "it": 0.06, "re": 0.18, "al": 0.12, "label": "Enterprise ready"},
}

# ── Team composition scoring ─────────────────────────────────────────
# Keys: te=team_efficiency, it=iteration_throughput, al=approach_leverage, re=reusability
TEAM = {
    "solo_founder": {"te": 0.16, "it": 0.14, "al": 0.08, "re": 0.06, "label": "Solo founder"},
    "founder_plus_ai": {"te": 0.19, "it": 0.18, "al": 0.16, "re": 0.14, "label": "Founder + AI"},
    "small_team": {"te": 0.14, "it": 0.12, "al": 0.14, "re": 0.16, "label": "Small team"},
    "contractor_augmented": {"te": 0.12, "it": 0.15, "al": 0.10, "re": 0.10, "label": "Contractor-augmented"},
}

# ── Iteration speed scoring ──────────────────────────────────────────
# Keys: it=iteration_throughput, te=team_efficiency, qc=quality_confidence
SPEED = {
    "daily_ship": {"it": 0.18, "te": 0.10, "qc": 0.05, "label": "Daily ship"},
    "weekly_release": {"it": 0.14, "te": 0.13, "qc": 0.11, "label": "Weekly release"},
    "biweekly_sprint": {"it": 0.10, "te": 0.14, "qc": 0.15, "label": "Biweekly sprint"},
}

# ── Synergy: build_approach x team_composition ───────────────────────
APPROACH_TEAM = {
    "template_factory|solo_founder": 0.12,
    "template_factory|founder_plus_ai": 0.14,
    "agent_workflow|founder_plus_ai": 0.16,
    "agent_workflow|small_team": 0.10,
    "custom_development|small_team": 0.12,
    "custom_development|contractor_augmented": 0.09,
    "low_code|solo_founder": 0.11,
    "low_code|contractor_augmented": 0.10,
    "api_integration|founder_plus_ai": 0.13,
    "api_integration|small_team": 0.11,
}

# ── Synergy: quality_gate x iteration_speed ──────────────────────────
QUALITY_SPEED = {
    "minimal_viable|daily_ship": 0.14,
    "minimal_viable|weekly_release": 0.10,
    "production_grade|weekly_release": 0.12,
    "production_grade|biweekly_sprint": 0.11,
    "enterprise_ready|biweekly_sprint": 0.13,
    "enterprise_ready|weekly_release": 0.06,
}

# ── Anti-synergy: speed-quality mismatch penalty ─────────────────────
SPEED_QUALITY_PENALTY = {
    "enterprise_ready|daily_ship": 0.10,
    "minimal_viable|biweekly_sprint": 0.06,
}


def score(mutations: dict) -> dict:
    """Score a build orchestration candidate. Returns metrics + verdict."""
    if not mutations:
        return {
            **BASE,
            "verdict": "baseline",
            "mechanism": "No build configuration specified.",
            "boundary": "Baseline only. Cannot evaluate build velocity without approach and quality gate.",
            "recommended_next_step": "define_build_approach_and_quality_gate",
            "evidence_lane": "exploratory_frontier",
            "label": "Global baseline",
        }

    approach = APPROACH.get(mutations.get("build_approach", ""), {})
    priority = PRIORITY.get(mutations.get("priority_method", ""), {})
    quality = QUALITY.get(mutations.get("quality_gate", ""), {})
    team = TEAM.get(mutations.get("team_composition", ""), {})
    speed = SPEED.get(mutations.get("iteration_speed", ""), {})

    # Synergy lookups
    at_key = f"{mutations.get('build_approach', '')}|{mutations.get('team_composition', '')}"
    qs_key = f"{mutations.get('quality_gate', '')}|{mutations.get('iteration_speed', '')}"
    at_bonus = APPROACH_TEAM.get(at_key, -0.02)
    qs_bonus = QUALITY_SPEED.get(qs_key, -0.01)
    sq_penalty = SPEED_QUALITY_PENALTY.get(qs_key, 0.0)

    # Compute sub-metrics
    approach_leverage = _c(
        BASE["approach_leverage_score"]
        + approach.get("al", 0)
        + quality.get("al", 0)
        + team.get("al", 0)
        + at_bonus * 0.3
    )

    priority_clarity = _c(
        BASE["priority_clarity_score"]
        + priority.get("pc", 0)
        + qs_bonus * 0.2
    )

    quality_confidence = _c(
        BASE["quality_confidence_score"]
        + approach.get("qc", 0)
        + priority.get("qc", 0)
        + quality.get("qc", 0)
        + speed.get("qc", 0)
        - sq_penalty
    )

    team_efficiency = _c(
        BASE["team_efficiency_score"]
        + team.get("te", 0)
        + priority.get("te", 0)
        + speed.get("te", 0)
        + at_bonus * 0.25
    )

    iteration_throughput = _c(
        BASE["iteration_throughput_score"]
        + approach.get("it", 0)
        + priority.get("it", 0)
        + quality.get("it", 0)
        + team.get("it", 0)
        + speed.get("it", 0)
        + qs_bonus * 0.3
        - sq_penalty * 0.5
    )

    reusability = _c(
        BASE["reusability_score"]
        + approach.get("re", 0)
        + quality.get("re", 0)
        + team.get("re", 0)
        + at_bonus * 0.2
    )

    # Composite
    overall = _c(
        BASE["build_velocity_score"]
        + approach_leverage * 0.17
        + priority_clarity * 0.13
        + quality_confidence * 0.16
        + team_efficiency * 0.18
        + iteration_throughput * 0.20
        + reusability * 0.16
        + at_bonus * 0.08
        + qs_bonus * 0.06
        - sq_penalty * 0.15
    )

    # Bottleneck detection
    sub_metrics = [
        ("approach_gap", approach_leverage),
        ("priority_gap", priority_clarity),
        ("quality_gap", quality_confidence),
        ("team_gap", team_efficiency),
        ("throughput_gap", iteration_throughput),
        ("reusability_gap", reusability),
    ]
    bottleneck, _ = min(sub_metrics, key=lambda x: x[1])

    next_step_map = {
        "approach_gap": "evaluate_alternative_build_approach",
        "priority_gap": "sharpen_prioritization_framework",
        "quality_gap": "adjust_quality_gate_to_stage",
        "team_gap": "optimize_team_composition_for_velocity",
        "throughput_gap": "reduce_iteration_cycle_time",
        "reusability_gap": "invest_in_reusable_components",
    }

    lesson_map = {
        "approach_gap": "The build approach is not generating enough leverage for the current team and quality requirements.",
        "priority_gap": "Prioritization is unclear. The team is building the wrong things or in the wrong order.",
        "quality_gap": "Quality confidence is low. Either the gate is too ambitious or the approach cannot sustain it.",
        "team_gap": "Team composition does not match the build approach. Consider AI augmentation or restructuring.",
        "throughput_gap": "Iteration speed is too slow for the current stage. Reduce scope or change the cadence.",
        "reusability_gap": "Build outputs are not reusable. Each feature is a one-off cost instead of compounding leverage.",
    }

    # Verdict
    if overall >= 0.77 and iteration_throughput >= 0.58 and quality_confidence >= 0.55:
        verdict = "approve"
    elif overall >= 0.58 and (approach_leverage >= 0.48 or team_efficiency >= 0.50):
        verdict = "defer"
    else:
        verdict = "reject"

    label = " | ".join(
        part for part in [
            approach.get("label", ""),
            priority.get("label", ""),
            quality.get("label", ""),
            team.get("label", ""),
        ] if part
    )

    return {
        "build_velocity_score": overall,
        "approach_leverage_score": approach_leverage,
        "priority_clarity_score": priority_clarity,
        "quality_confidence_score": quality_confidence,
        "team_efficiency_score": team_efficiency,
        "iteration_throughput_score": iteration_throughput,
        "reusability_score": reusability,
        "verdict": verdict,
        "mechanism": f"Build velocity compounds when {approach.get('label', 'approach')} with {team.get('label', 'team')} hits {quality.get('label', 'quality')} at {speed.get('label', 'speed')} cadence.",
        "boundary": "Fixed evaluator scaffold. Does not replace real sprint velocity data or deployment success rates.",
        "recommended_next_step": next_step_map.get(bottleneck, "hold_for_more_evidence"),
        "evidence_lane": "exploratory_frontier",
        "bottleneck": bottleneck,
        "lesson": lesson_map.get(bottleneck, ""),
        "label": label or "Unnamed build play",
    }
