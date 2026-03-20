"""Domain-specific scoring for portfolio knowledge extraction and compounding."""
from __future__ import annotations


def _c(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


# ── Base scores ──────────────────────────────────────────────────────
BASE = {
    "knowledge_utility_score": 0.11,
    "pattern_depth_score": 0.14,
    "scope_coverage_score": 0.13,
    "extraction_quality_score": 0.14,
    "shareability_score": 0.13,
    "compounding_value_score": 0.15,
    "freshness_score": 0.14,
}

# ── Pattern type scoring ─────────────────────────────────────────────
# Keys: pd=pattern_depth, cv=compounding_value, sh=shareability, eq=extraction_quality
PATTERN = {
    "growth_playbook": {"pd": 0.18, "cv": 0.20, "sh": 0.16, "eq": 0.14, "label": "Growth playbook"},
    "failure_postmortem": {"pd": 0.20, "cv": 0.16, "sh": 0.12, "eq": 0.18, "label": "Failure postmortem"},
    "pivot_case_study": {"pd": 0.16, "cv": 0.14, "sh": 0.18, "eq": 0.16, "label": "Pivot case study"},
    "operational_template": {"pd": 0.12, "cv": 0.18, "sh": 0.14, "eq": 0.12, "label": "Operational template"},
    "market_insight": {"pd": 0.14, "cv": 0.12, "sh": 0.15, "eq": 0.15, "label": "Market insight"},
}

# ── Knowledge scope scoring ──────────────────────────────────────────
# Keys: sc=scope_coverage, cv=compounding_value, pd=pattern_depth, eq=extraction_quality
SCOPE = {
    "single_venture": {"sc": 0.08, "cv": 0.06, "pd": 0.16, "eq": 0.14, "label": "Single venture"},
    "cross_portfolio": {"sc": 0.18, "cv": 0.20, "pd": 0.12, "eq": 0.12, "label": "Cross-portfolio"},
    "industry_wide": {"sc": 0.16, "cv": 0.14, "pd": 0.10, "eq": 0.10, "label": "Industry-wide"},
    "historical": {"sc": 0.14, "cv": 0.10, "pd": 0.14, "eq": 0.08, "label": "Historical"},
}

# ── Extraction method scoring ────────────────────────────────────────
# Keys: eq=extraction_quality, pd=pattern_depth, cv=compounding_value, sc=scope_coverage
EXTRACTION = {
    "kpi_trend_analysis": {"eq": 0.18, "pd": 0.14, "cv": 0.16, "sc": 0.12, "label": "KPI trend analysis"},
    "founder_interview_synthesis": {"eq": 0.16, "pd": 0.20, "cv": 0.10, "sc": 0.08, "label": "Founder interview synthesis"},
    "agent_observation": {"eq": 0.14, "pd": 0.12, "cv": 0.18, "sc": 0.14, "label": "Agent observation"},
    "benchmark_comparison": {"eq": 0.17, "pd": 0.10, "cv": 0.12, "sc": 0.16, "label": "Benchmark comparison"},
}

# ── Sharing format scoring ───────────────────────────────────────────
# Keys: sh=shareability, cv=compounding_value, fr=freshness
SHARING = {
    "doctrine_card": {"sh": 0.18, "cv": 0.16, "fr": 0.10, "label": "Doctrine card"},
    "playbook_chapter": {"sh": 0.16, "cv": 0.18, "fr": 0.12, "label": "Playbook chapter"},
    "mentor_brief": {"sh": 0.14, "cv": 0.10, "fr": 0.14, "label": "Mentor brief"},
    "founder_digest": {"sh": 0.12, "cv": 0.12, "fr": 0.16, "label": "Founder digest"},
}

# ── Relevance decay scoring ──────────────────────────────────────────
# Keys: fr=freshness, cv=compounding_value, sh=shareability
DECAY = {
    "evergreen": {"fr": 0.18, "cv": 0.16, "sh": 0.12, "label": "Evergreen"},
    "seasonal": {"fr": 0.12, "cv": 0.10, "sh": 0.10, "label": "Seasonal"},
    "time_sensitive": {"fr": 0.06, "cv": 0.05, "sh": 0.08, "label": "Time-sensitive"},
}

# ── Synergy: pattern_type x knowledge_scope ──────────────────────────
PATTERN_SCOPE = {
    "growth_playbook|cross_portfolio": 0.15,
    "growth_playbook|industry_wide": 0.11,
    "failure_postmortem|single_venture": 0.14,
    "failure_postmortem|cross_portfolio": 0.12,
    "pivot_case_study|industry_wide": 0.13,
    "pivot_case_study|historical": 0.10,
    "operational_template|cross_portfolio": 0.14,
    "operational_template|single_venture": 0.09,
    "market_insight|industry_wide": 0.13,
    "market_insight|historical": 0.11,
}

# ── Synergy: extraction_method x sharing_format ─────────────────────
EXTRACTION_SHARING = {
    "kpi_trend_analysis|doctrine_card": 0.13,
    "kpi_trend_analysis|playbook_chapter": 0.11,
    "founder_interview_synthesis|mentor_brief": 0.14,
    "founder_interview_synthesis|founder_digest": 0.10,
    "agent_observation|doctrine_card": 0.11,
    "agent_observation|founder_digest": 0.12,
    "benchmark_comparison|playbook_chapter": 0.13,
    "benchmark_comparison|doctrine_card": 0.09,
}

# ── Anti-synergy: decay mismatches ───────────────────────────────────
DECAY_PENALTY = {
    "time_sensitive|growth_playbook": 0.06,
    "time_sensitive|operational_template": 0.05,
}


def score(mutations: dict) -> dict:
    """Score a portfolio knowledge candidate. Returns metrics + verdict."""
    if not mutations:
        return {
            **BASE,
            "verdict": "baseline",
            "mechanism": "No knowledge configuration specified.",
            "boundary": "Baseline only. Cannot evaluate knowledge utility without pattern type and scope.",
            "recommended_next_step": "define_pattern_type_and_knowledge_scope",
            "evidence_lane": "exploratory_frontier",
            "label": "Global baseline",
        }

    pattern = PATTERN.get(mutations.get("pattern_type", ""), {})
    scope = SCOPE.get(mutations.get("knowledge_scope", ""), {})
    extraction = EXTRACTION.get(mutations.get("extraction_method", ""), {})
    sharing = SHARING.get(mutations.get("sharing_format", ""), {})
    decay = DECAY.get(mutations.get("relevance_decay", ""), {})

    # Synergy lookups
    ps_key = f"{mutations.get('pattern_type', '')}|{mutations.get('knowledge_scope', '')}"
    es_key = f"{mutations.get('extraction_method', '')}|{mutations.get('sharing_format', '')}"
    dp_key = f"{mutations.get('relevance_decay', '')}|{mutations.get('pattern_type', '')}"
    ps_bonus = PATTERN_SCOPE.get(ps_key, -0.02)
    es_bonus = EXTRACTION_SHARING.get(es_key, -0.01)
    dp_penalty = DECAY_PENALTY.get(dp_key, 0.0)

    # Compute sub-metrics
    pattern_depth = _c(
        BASE["pattern_depth_score"]
        + pattern.get("pd", 0)
        + scope.get("pd", 0)
        + extraction.get("pd", 0)
        + ps_bonus * 0.3
    )

    scope_coverage = _c(
        BASE["scope_coverage_score"]
        + scope.get("sc", 0)
        + extraction.get("sc", 0)
        + ps_bonus * 0.25
    )

    extraction_quality = _c(
        BASE["extraction_quality_score"]
        + pattern.get("eq", 0)
        + scope.get("eq", 0)
        + extraction.get("eq", 0)
        + es_bonus * 0.2
    )

    shareability = _c(
        BASE["shareability_score"]
        + pattern.get("sh", 0)
        + sharing.get("sh", 0)
        + decay.get("sh", 0)
        + es_bonus * 0.3
    )

    compounding_value = _c(
        BASE["compounding_value_score"]
        + pattern.get("cv", 0)
        + scope.get("cv", 0)
        + extraction.get("cv", 0)
        + sharing.get("cv", 0)
        + decay.get("cv", 0)
        + ps_bonus * 0.2
        - dp_penalty
    )

    freshness = _c(
        BASE["freshness_score"]
        + sharing.get("fr", 0)
        + decay.get("fr", 0)
        - dp_penalty * 0.5
    )

    # Composite
    overall = _c(
        BASE["knowledge_utility_score"]
        + pattern_depth * 0.17
        + scope_coverage * 0.14
        + extraction_quality * 0.18
        + shareability * 0.16
        + compounding_value * 0.20
        + freshness * 0.15
        + ps_bonus * 0.06
        + es_bonus * 0.06
        - dp_penalty * 0.08
    )

    # Bottleneck detection
    sub_metrics = [
        ("depth_gap", pattern_depth),
        ("coverage_gap", scope_coverage),
        ("extraction_gap", extraction_quality),
        ("sharing_gap", shareability),
        ("compounding_gap", compounding_value),
        ("freshness_gap", freshness),
    ]
    bottleneck, _ = min(sub_metrics, key=lambda x: x[1])

    next_step_map = {
        "depth_gap": "deepen_pattern_analysis_with_more_data",
        "coverage_gap": "expand_knowledge_scope_across_portfolio",
        "extraction_gap": "improve_extraction_method_rigor",
        "sharing_gap": "optimize_sharing_format_for_audience",
        "compounding_gap": "link_insights_to_reusable_doctrine",
        "freshness_gap": "update_knowledge_with_recent_signals",
    }

    lesson_map = {
        "depth_gap": "Pattern analysis is too shallow. Need deeper investigation to extract actionable knowledge.",
        "coverage_gap": "Knowledge scope is too narrow. Cross-portfolio patterns would be more useful.",
        "extraction_gap": "Extraction method is not producing reliable or rigorous insights.",
        "sharing_gap": "Knowledge is not reaching the right people in the right format.",
        "compounding_gap": "Insights are not building on each other. Knowledge stays isolated instead of compounding.",
        "freshness_gap": "Knowledge is stale. Relevance decay is eroding the value of stored insights.",
    }

    # Verdict
    if overall >= 0.77 and compounding_value >= 0.58 and extraction_quality >= 0.55:
        verdict = "approve"
    elif overall >= 0.58 and (pattern_depth >= 0.48 or scope_coverage >= 0.45):
        verdict = "defer"
    else:
        verdict = "reject"

    label = " | ".join(
        part for part in [
            pattern.get("label", ""),
            scope.get("label", ""),
            extraction.get("label", ""),
            sharing.get("label", ""),
        ] if part
    )

    return {
        "knowledge_utility_score": overall,
        "pattern_depth_score": pattern_depth,
        "scope_coverage_score": scope_coverage,
        "extraction_quality_score": extraction_quality,
        "shareability_score": shareability,
        "compounding_value_score": compounding_value,
        "freshness_score": freshness,
        "verdict": verdict,
        "mechanism": f"Knowledge utility compounds when {pattern.get('label', 'pattern')} at {scope.get('label', 'scope')} is extracted via {extraction.get('label', 'method')} and shared as {sharing.get('label', 'format')}.",
        "boundary": "Fixed evaluator scaffold. Does not replace real portfolio review outcomes or founder feedback.",
        "recommended_next_step": next_step_map.get(bottleneck, "hold_for_more_evidence"),
        "evidence_lane": "exploratory_frontier",
        "bottleneck": bottleneck,
        "lesson": lesson_map.get(bottleneck, ""),
        "label": label or "Unnamed knowledge play",
    }
