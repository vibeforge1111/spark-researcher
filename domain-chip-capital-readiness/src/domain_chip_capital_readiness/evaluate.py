"""Domain-specific scoring for capital readiness and fundraising strategy."""
from __future__ import annotations


def _c(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


# ── Base scores ──────────────────────────────────────────────────────
BASE = {
    "capital_readiness_score": 0.11,
    "round_fit_score": 0.14,
    "investor_alignment_score": 0.13,
    "traction_evidence_score": 0.12,
    "pitch_effectiveness_score": 0.14,
    "timing_calibration_score": 0.15,
    "narrative_coherence_score": 0.13,
}

# ── Round type scoring ───────────────────────────────────────────────
# Keys: rf=round_fit, nc=narrative_coherence, tc=timing_calibration, te=traction_evidence
ROUND = {
    "pre_seed": {"rf": 0.14, "nc": 0.12, "tc": 0.10, "te": 0.06, "label": "Pre-seed"},
    "seed": {"rf": 0.16, "nc": 0.15, "tc": 0.13, "te": 0.12, "label": "Seed"},
    "series_a": {"rf": 0.18, "nc": 0.18, "tc": 0.16, "te": 0.18, "label": "Series A"},
    "bridge": {"rf": 0.10, "nc": 0.08, "tc": 0.17, "te": 0.10, "label": "Bridge"},
    "revenue_based": {"rf": 0.12, "nc": 0.14, "tc": 0.14, "te": 0.16, "label": "Revenue-based"},
}

# ── Investor fit scoring ─────────────────────────────────────────────
# Keys: ia=investor_alignment, pe=pitch_effectiveness, nc=narrative_coherence, rf=round_fit
INVESTOR = {
    "angel_network": {"ia": 0.14, "pe": 0.12, "nc": 0.10, "rf": 0.10, "label": "Angel network"},
    "micro_vc": {"ia": 0.16, "pe": 0.14, "nc": 0.13, "rf": 0.12, "label": "Micro VC"},
    "institutional_vc": {"ia": 0.18, "pe": 0.18, "nc": 0.17, "rf": 0.16, "label": "Institutional VC"},
    "strategic": {"ia": 0.15, "pe": 0.10, "nc": 0.14, "rf": 0.11, "label": "Strategic"},
    "accelerator_follow_on": {"ia": 0.12, "pe": 0.11, "nc": 0.11, "rf": 0.09, "label": "Accelerator follow-on"},
}

# ── Readiness signal scoring ─────────────────────────────────────────
# Keys: te=traction_evidence, tc=timing_calibration, nc=narrative_coherence, ia=investor_alignment
READINESS = {
    "revenue_milestone": {"te": 0.20, "tc": 0.14, "nc": 0.16, "ia": 0.12, "label": "Revenue milestone"},
    "user_growth": {"te": 0.16, "tc": 0.12, "nc": 0.14, "ia": 0.10, "label": "User growth"},
    "team_completeness": {"te": 0.10, "tc": 0.10, "nc": 0.12, "ia": 0.14, "label": "Team completeness"},
    "market_timing": {"te": 0.08, "tc": 0.18, "nc": 0.10, "ia": 0.08, "label": "Market timing"},
    "competitive_pressure": {"te": 0.12, "tc": 0.16, "nc": 0.08, "ia": 0.06, "label": "Competitive pressure"},
}

# ── Pitch format scoring ─────────────────────────────────────────────
# Keys: pe=pitch_effectiveness, nc=narrative_coherence, ia=investor_alignment
PITCH = {
    "deck_only": {"pe": 0.12, "nc": 0.10, "ia": 0.08, "label": "Deck only"},
    "memo_first": {"pe": 0.16, "nc": 0.18, "ia": 0.12, "label": "Memo first"},
    "data_room": {"pe": 0.18, "nc": 0.16, "ia": 0.16, "label": "Data room"},
    "warm_intro": {"pe": 0.14, "nc": 0.12, "ia": 0.18, "label": "Warm intro"},
    "cold_outreach": {"pe": 0.08, "nc": 0.06, "ia": 0.05, "label": "Cold outreach"},
}

# ── Timing strategy scoring ──────────────────────────────────────────
# Keys: tc=timing_calibration, rf=round_fit, te=traction_evidence, nc=narrative_coherence
TIMING = {
    "raise_now": {"tc": 0.16, "rf": 0.14, "te": 0.10, "nc": 0.12, "label": "Raise now"},
    "build_more_traction": {"tc": 0.14, "rf": 0.10, "te": 0.16, "nc": 0.14, "label": "Build more traction"},
    "extend_runway": {"tc": 0.12, "rf": 0.08, "te": 0.08, "nc": 0.08, "label": "Extend runway"},
    "consider_bootstrap": {"tc": 0.10, "rf": 0.06, "te": 0.14, "nc": 0.10, "label": "Consider bootstrap"},
}

# ── Synergy: round_type x investor_fit ───────────────────────────────
ROUND_INVESTOR = {
    "pre_seed|angel_network": 0.14,
    "pre_seed|accelerator_follow_on": 0.12,
    "seed|micro_vc": 0.14,
    "seed|angel_network": 0.10,
    "series_a|institutional_vc": 0.16,
    "series_a|strategic": 0.10,
    "bridge|micro_vc": 0.08,
    "bridge|angel_network": 0.06,
    "revenue_based|strategic": 0.13,
    "revenue_based|micro_vc": 0.09,
}

# ── Synergy: timing_strategy x readiness_signal ─────────────────────
TIMING_READINESS = {
    "raise_now|revenue_milestone": 0.15,
    "raise_now|market_timing": 0.12,
    "raise_now|competitive_pressure": 0.10,
    "build_more_traction|user_growth": 0.13,
    "build_more_traction|revenue_milestone": 0.11,
    "extend_runway|team_completeness": 0.08,
    "consider_bootstrap|revenue_milestone": 0.12,
    "consider_bootstrap|team_completeness": 0.09,
}

# ── Anti-synergy: premature raise penalty ────────────────────────────
PREMATURE_PENALTY = {
    "series_a|raise_now|user_growth": 0.04,
    "series_a|raise_now|team_completeness": 0.08,
}


def score(mutations: dict) -> dict:
    """Score a capital readiness candidate. Returns metrics + verdict."""
    if not mutations:
        return {
            **BASE,
            "verdict": "baseline",
            "mechanism": "No capital configuration specified.",
            "boundary": "Baseline only. Cannot evaluate capital readiness without round type and timing strategy.",
            "recommended_next_step": "define_round_type_and_timing_strategy",
            "evidence_lane": "exploratory_frontier",
            "label": "Global baseline",
        }

    rnd = ROUND.get(mutations.get("round_type", ""), {})
    investor = INVESTOR.get(mutations.get("investor_fit", ""), {})
    readiness = READINESS.get(mutations.get("readiness_signal", ""), {})
    pitch = PITCH.get(mutations.get("pitch_format", ""), {})
    timing = TIMING.get(mutations.get("timing_strategy", ""), {})

    # Synergy lookups
    ri_key = f"{mutations.get('round_type', '')}|{mutations.get('investor_fit', '')}"
    tr_key = f"{mutations.get('timing_strategy', '')}|{mutations.get('readiness_signal', '')}"
    ri_bonus = ROUND_INVESTOR.get(ri_key, -0.02)
    tr_bonus = TIMING_READINESS.get(tr_key, -0.01)

    # Premature raise penalty
    premature_key = f"{mutations.get('round_type', '')}|{mutations.get('timing_strategy', '')}|{mutations.get('readiness_signal', '')}"
    premature = PREMATURE_PENALTY.get(premature_key, 0.0)

    # Compute sub-metrics
    round_fit = _c(
        BASE["round_fit_score"]
        + rnd.get("rf", 0)
        + investor.get("rf", 0)
        + timing.get("rf", 0)
        + ri_bonus * 0.3
    )

    investor_alignment = _c(
        BASE["investor_alignment_score"]
        + investor.get("ia", 0)
        + readiness.get("ia", 0)
        + pitch.get("ia", 0)
        + ri_bonus * 0.35
    )

    traction_evidence = _c(
        BASE["traction_evidence_score"]
        + rnd.get("te", 0)
        + readiness.get("te", 0)
        + timing.get("te", 0)
        + tr_bonus * 0.3
        - premature
    )

    pitch_effectiveness = _c(
        BASE["pitch_effectiveness_score"]
        + investor.get("pe", 0)
        + pitch.get("pe", 0)
        + ri_bonus * 0.2
    )

    timing_calibration = _c(
        BASE["timing_calibration_score"]
        + rnd.get("tc", 0)
        + readiness.get("tc", 0)
        + timing.get("tc", 0)
        + tr_bonus * 0.35
        - premature * 0.5
    )

    narrative_coherence = _c(
        BASE["narrative_coherence_score"]
        + rnd.get("nc", 0)
        + investor.get("nc", 0)
        + readiness.get("nc", 0)
        + pitch.get("nc", 0)
        + timing.get("nc", 0)
    )

    # Composite
    overall = _c(
        BASE["capital_readiness_score"]
        + round_fit * 0.16
        + investor_alignment * 0.17
        + traction_evidence * 0.19
        + pitch_effectiveness * 0.15
        + timing_calibration * 0.18
        + narrative_coherence * 0.15
        + ri_bonus * 0.06
        + tr_bonus * 0.06
        - premature * 0.10
    )

    # Bottleneck detection
    sub_metrics = [
        ("round_gap", round_fit),
        ("investor_gap", investor_alignment),
        ("traction_gap", traction_evidence),
        ("pitch_gap", pitch_effectiveness),
        ("timing_gap", timing_calibration),
        ("narrative_gap", narrative_coherence),
    ]
    bottleneck, _ = min(sub_metrics, key=lambda x: x[1])

    next_step_map = {
        "round_gap": "reconsider_round_type_for_current_stage",
        "investor_gap": "target_investors_who_match_round_and_sector",
        "traction_gap": "build_stronger_traction_evidence_before_raising",
        "pitch_gap": "improve_pitch_materials_and_format",
        "timing_gap": "recalibrate_fundraise_timing",
        "narrative_gap": "strengthen_founding_story_and_vision",
    }

    lesson_map = {
        "round_gap": "The round type does not match the current traction level or investor landscape.",
        "investor_gap": "Investor targeting is misaligned. The pitch is reaching the wrong audience.",
        "traction_gap": "Traction evidence is too weak for the round type. Build more before raising.",
        "pitch_gap": "Pitch materials are not compelling enough. Upgrade format or narrative.",
        "timing_gap": "The timing is off. Either raise earlier with urgency or wait for stronger signals.",
        "narrative_gap": "The fundraising story does not hold together. Round, traction, and timing need to align.",
    }

    # Verdict
    if overall >= 0.78 and traction_evidence >= 0.58 and timing_calibration >= 0.56:
        verdict = "approve"
    elif overall >= 0.58 and (round_fit >= 0.48 or investor_alignment >= 0.50):
        verdict = "defer"
    else:
        verdict = "reject"

    label = " | ".join(
        part for part in [
            rnd.get("label", ""),
            investor.get("label", ""),
            readiness.get("label", ""),
            pitch.get("label", ""),
        ] if part
    )

    return {
        "capital_readiness_score": overall,
        "round_fit_score": round_fit,
        "investor_alignment_score": investor_alignment,
        "traction_evidence_score": traction_evidence,
        "pitch_effectiveness_score": pitch_effectiveness,
        "timing_calibration_score": timing_calibration,
        "narrative_coherence_score": narrative_coherence,
        "verdict": verdict,
        "mechanism": f"Capital readiness compounds when {rnd.get('label', 'round')} targets {investor.get('label', 'investors')} backed by {readiness.get('label', 'signals')} via {pitch.get('label', 'pitch')}.",
        "boundary": "Fixed evaluator scaffold. Does not replace real investor conversations or term sheet negotiations.",
        "recommended_next_step": next_step_map.get(bottleneck, "hold_for_more_evidence"),
        "evidence_lane": "exploratory_frontier",
        "bottleneck": bottleneck,
        "lesson": lesson_map.get(bottleneck, ""),
        "label": label or "Unnamed capital play",
    }
