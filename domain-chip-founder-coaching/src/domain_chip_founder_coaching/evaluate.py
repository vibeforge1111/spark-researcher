"""Domain-specific scoring for founder coaching interventions."""
from __future__ import annotations


def _c(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


# ── Base scores ──────────────────────────────────────────────────────
BASE = {
    "coaching_effectiveness_score": 0.12,
    "style_fit_score": 0.15,
    "timing_quality_score": 0.14,
    "question_depth_score": 0.16,
    "blocker_resolution_potential": 0.13,
    "founder_trust_score": 0.17,
    "adaptability_score": 0.14,
}

# ── Coaching style scoring ───────────────────────────────────────────
# Keys: sf=style_fit, qd=question_depth, br=blocker_resolution, ft=founder_trust, ad=adaptability
STYLE = {
    "socratic": {"sf": 0.18, "qd": 0.22, "br": 0.10, "ft": 0.14, "ad": 0.12, "label": "Socratic"},
    "directive": {"sf": 0.14, "qd": 0.08, "br": 0.20, "ft": 0.09, "ad": 0.07, "label": "Directive"},
    "accountability": {"sf": 0.16, "qd": 0.12, "br": 0.17, "ft": 0.16, "ad": 0.10, "label": "Accountability"},
    "peer_mirror": {"sf": 0.13, "qd": 0.16, "br": 0.09, "ft": 0.19, "ad": 0.15, "label": "Peer mirror"},
}

# ── Session format scoring ───────────────────────────────────────────
# Keys: tq=timing_quality, sf=style_fit, ft=founder_trust, ad=adaptability
FORMAT = {
    "weekly_1on1": {"tq": 0.18, "sf": 0.12, "ft": 0.14, "ad": 0.10, "label": "Weekly 1-on-1"},
    "async_written": {"tq": 0.11, "sf": 0.09, "ft": 0.10, "ad": 0.16, "label": "Async written"},
    "crisis_intervention": {"tq": 0.22, "sf": 0.08, "ft": 0.06, "ad": 0.05, "label": "Crisis intervention"},
    "milestone_review": {"tq": 0.15, "sf": 0.14, "ft": 0.16, "ad": 0.13, "label": "Milestone review"},
}

# ── Focus area scoring ───────────────────────────────────────────────
# Keys: br=blocker_resolution, qd=question_depth, ft=founder_trust, sf=style_fit
FOCUS = {
    "growth_blockers": {"br": 0.19, "qd": 0.14, "ft": 0.08, "sf": 0.10, "label": "Growth blockers"},
    "founder_wellbeing": {"br": 0.07, "qd": 0.11, "ft": 0.20, "sf": 0.12, "label": "Founder wellbeing"},
    "team_dynamics": {"br": 0.12, "qd": 0.16, "ft": 0.14, "sf": 0.09, "label": "Team dynamics"},
    "market_repositioning": {"br": 0.16, "qd": 0.18, "ft": 0.06, "sf": 0.11, "label": "Market repositioning"},
}

# ── Stage context scoring ────────────────────────────────────────────
# Keys: tq=timing_quality, br=blocker_resolution, ad=adaptability, ft=founder_trust
STAGE = {
    "pre_product": {"tq": 0.10, "br": 0.08, "ad": 0.14, "ft": 0.12, "label": "Pre-product"},
    "validation": {"tq": 0.16, "br": 0.15, "ad": 0.12, "ft": 0.10, "label": "Validation"},
    "growth": {"tq": 0.14, "br": 0.18, "ad": 0.10, "ft": 0.13, "label": "Growth"},
    "scale": {"tq": 0.12, "br": 0.12, "ad": 0.08, "ft": 0.16, "label": "Scale"},
}

# ── Urgency level scoring ───────────────────────────────────────────
# Keys: tq=timing_quality, br=blocker_resolution, sf=style_fit
URGENCY = {
    "routine": {"tq": 0.08, "br": 0.06, "sf": 0.10, "label": "Routine"},
    "attention_needed": {"tq": 0.14, "br": 0.12, "sf": 0.08, "label": "Attention needed"},
    "critical": {"tq": 0.20, "br": 0.18, "sf": 0.05, "label": "Critical"},
}

# ── Synergy tables ───────────────────────────────────────────────────
# coaching_style x urgency_level
STYLE_URGENCY = {
    "socratic|routine": 0.10,
    "socratic|attention_needed": 0.06,
    "socratic|critical": -0.05,
    "directive|routine": -0.03,
    "directive|attention_needed": 0.08,
    "directive|critical": 0.14,
    "accountability|routine": 0.07,
    "accountability|attention_needed": 0.11,
    "accountability|critical": 0.04,
    "peer_mirror|routine": 0.09,
    "peer_mirror|attention_needed": 0.05,
    "peer_mirror|critical": -0.04,
}

# stage_context x focus_area
STAGE_FOCUS = {
    "pre_product|growth_blockers": 0.06,
    "pre_product|founder_wellbeing": 0.10,
    "pre_product|team_dynamics": 0.03,
    "pre_product|market_repositioning": 0.12,
    "validation|growth_blockers": 0.11,
    "validation|founder_wellbeing": 0.05,
    "validation|team_dynamics": 0.04,
    "validation|market_repositioning": 0.13,
    "growth|growth_blockers": 0.14,
    "growth|founder_wellbeing": 0.07,
    "growth|team_dynamics": 0.10,
    "growth|market_repositioning": 0.06,
    "scale|growth_blockers": 0.08,
    "scale|founder_wellbeing": 0.09,
    "scale|team_dynamics": 0.13,
    "scale|market_repositioning": 0.05,
}


def score(mutations: dict) -> dict:
    """Score a founder coaching candidate. Returns metrics + verdict."""
    if not mutations:
        return {
            **BASE,
            "verdict": "baseline",
            "mechanism": "No coaching configuration specified.",
            "boundary": "Baseline only. Cannot evaluate coaching effectiveness without style and stage.",
            "recommended_next_step": "define_coaching_style_and_stage",
            "evidence_lane": "exploratory_frontier",
            "label": "Global baseline",
        }

    style = STYLE.get(mutations.get("coaching_style", ""), {})
    fmt = FORMAT.get(mutations.get("session_format", ""), {})
    focus = FOCUS.get(mutations.get("focus_area", ""), {})
    stage = STAGE.get(mutations.get("stage_context", ""), {})
    urgency = URGENCY.get(mutations.get("urgency_level", ""), {})

    # Synergy lookups
    su_key = f"{mutations.get('coaching_style', '')}|{mutations.get('urgency_level', '')}"
    sf_key = f"{mutations.get('stage_context', '')}|{mutations.get('focus_area', '')}"
    su_bonus = STYLE_URGENCY.get(su_key, -0.02)
    sf_bonus = STAGE_FOCUS.get(sf_key, -0.01)

    # Compute sub-metrics
    style_fit = _c(
        BASE["style_fit_score"]
        + style.get("sf", 0)
        + fmt.get("sf", 0)
        + focus.get("sf", 0)
        + urgency.get("sf", 0)
        + su_bonus * 0.3
    )

    timing_quality = _c(
        BASE["timing_quality_score"]
        + fmt.get("tq", 0)
        + stage.get("tq", 0)
        + urgency.get("tq", 0)
        + su_bonus * 0.2
    )

    question_depth = _c(
        BASE["question_depth_score"]
        + style.get("qd", 0)
        + focus.get("qd", 0)
        + fmt.get("qd", 0) if "qd" in fmt else 0
        + sf_bonus * 0.4
    )
    # Recompute correctly since ternary above is tricky
    question_depth = _c(
        BASE["question_depth_score"]
        + style.get("qd", 0)
        + focus.get("qd", 0)
        + sf_bonus * 0.4
    )

    blocker_resolution = _c(
        BASE["blocker_resolution_potential"]
        + style.get("br", 0)
        + focus.get("br", 0)
        + stage.get("br", 0)
        + urgency.get("br", 0)
        + sf_bonus * 0.3
    )

    founder_trust = _c(
        BASE["founder_trust_score"]
        + style.get("ft", 0)
        + fmt.get("ft", 0)
        + focus.get("ft", 0)
        + stage.get("ft", 0)
        + su_bonus * 0.25
    )

    adaptability = _c(
        BASE["adaptability_score"]
        + style.get("ad", 0)
        + fmt.get("ad", 0)
        + stage.get("ad", 0)
        + su_bonus * 0.15
    )

    # Composite
    overall = _c(
        BASE["coaching_effectiveness_score"]
        + style_fit * 0.16
        + timing_quality * 0.17
        + question_depth * 0.18
        + blocker_resolution * 0.20
        + founder_trust * 0.16
        + adaptability * 0.13
        + su_bonus * 0.10
        + sf_bonus * 0.10
    )

    # Bottleneck detection
    sub_metrics = [
        ("style_gap", style_fit),
        ("timing_gap", timing_quality),
        ("depth_gap", question_depth),
        ("resolution_gap", blocker_resolution),
        ("trust_gap", founder_trust),
        ("adaptability_gap", adaptability),
    ]
    bottleneck, _ = min(sub_metrics, key=lambda x: x[1])

    next_step_map = {
        "style_gap": "adjust_coaching_style_to_founder_personality",
        "timing_gap": "realign_session_cadence_to_urgency",
        "depth_gap": "deepen_question_framework",
        "resolution_gap": "focus_on_concrete_blocker_resolution",
        "trust_gap": "invest_in_relationship_building",
        "adaptability_gap": "build_flexible_session_toolkit",
    }

    lesson_map = {
        "style_gap": "The coaching approach does not match the founder's current needs or personality.",
        "timing_gap": "Sessions are not timed to the founder's decision rhythm or urgency window.",
        "depth_gap": "Questions are not probing deeply enough to surface root causes.",
        "resolution_gap": "Coaching is not converting insights into concrete blocker-clearing actions.",
        "trust_gap": "The founder does not yet trust the coaching relationship enough to be vulnerable.",
        "adaptability_gap": "The coaching format is too rigid for the founder's changing context.",
    }

    # Verdict
    if overall >= 0.78 and blocker_resolution >= 0.60 and founder_trust >= 0.58:
        verdict = "approve"
    elif overall >= 0.60 and (style_fit >= 0.50 or timing_quality >= 0.50):
        verdict = "defer"
    else:
        verdict = "reject"

    label = " | ".join(
        part for part in [
            style.get("label", ""),
            fmt.get("label", ""),
            focus.get("label", ""),
            stage.get("label", ""),
        ] if part
    )

    return {
        "coaching_effectiveness_score": overall,
        "style_fit_score": style_fit,
        "timing_quality_score": timing_quality,
        "question_depth_score": question_depth,
        "blocker_resolution_potential": blocker_resolution,
        "founder_trust_score": founder_trust,
        "adaptability_score": adaptability,
        "verdict": verdict,
        "mechanism": f"Coaching effectiveness emerges from matching {style.get('label', 'style')} to {stage.get('label', 'stage')} context with appropriate urgency calibration.",
        "boundary": "Fixed evaluator scaffold. Does not replace real founder feedback or session outcome tracking.",
        "recommended_next_step": next_step_map.get(bottleneck, "hold_for_more_evidence"),
        "evidence_lane": "exploratory_frontier",
        "bottleneck": bottleneck,
        "lesson": lesson_map.get(bottleneck, ""),
        "label": label or "Unnamed coaching intervention",
    }
