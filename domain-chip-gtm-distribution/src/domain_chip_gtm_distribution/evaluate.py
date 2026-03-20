"""Domain-specific scoring for go-to-market distribution strategies."""
from __future__ import annotations


def _c(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


# ── Base scores ──────────────────────────────────────────────────────
BASE = {
    "gtm_effectiveness_score": 0.11,
    "channel_leverage_score": 0.14,
    "content_resonance_score": 0.13,
    "launch_momentum_score": 0.12,
    "funnel_efficiency_score": 0.13,
    "compounding_potential_score": 0.15,
    "stage_alignment_score": 0.14,
}

# ── Distribution channel scoring ─────────────────────────────────────
# Keys: cl=channel_leverage, cp=compounding_potential, fe=funnel_efficiency, sa=stage_alignment
CHANNEL = {
    "content_marketing": {"cl": 0.16, "cp": 0.19, "fe": 0.10, "sa": 0.12, "label": "Content marketing"},
    "cold_outbound": {"cl": 0.12, "cp": 0.06, "fe": 0.17, "sa": 0.09, "label": "Cold outbound"},
    "community": {"cl": 0.18, "cp": 0.20, "fe": 0.08, "sa": 0.14, "label": "Community"},
    "partnerships": {"cl": 0.15, "cp": 0.16, "fe": 0.13, "sa": 0.11, "label": "Partnerships"},
    "product_led": {"cl": 0.20, "cp": 0.18, "fe": 0.16, "sa": 0.10, "label": "Product-led"},
    "paid_acquisition": {"cl": 0.10, "cp": 0.05, "fe": 0.19, "sa": 0.08, "label": "Paid acquisition"},
}

# ── Content format scoring ───────────────────────────────────────────
# Keys: cr=content_resonance, cp=compounding_potential, cl=channel_leverage
CONTENT = {
    "long_form_blog": {"cr": 0.17, "cp": 0.16, "cl": 0.10, "label": "Long-form blog"},
    "social_threads": {"cr": 0.14, "cp": 0.12, "cl": 0.13, "label": "Social threads"},
    "video_demo": {"cr": 0.16, "cp": 0.10, "cl": 0.15, "label": "Video demo"},
    "case_study": {"cr": 0.19, "cp": 0.14, "cl": 0.12, "label": "Case study"},
    "newsletter": {"cr": 0.15, "cp": 0.18, "cl": 0.11, "label": "Newsletter"},
}

# ── Launch strategy scoring ──────────────────────────────────────────
# Keys: lm=launch_momentum, fe=funnel_efficiency, sa=stage_alignment
LAUNCH = {
    "soft_launch": {"lm": 0.08, "fe": 0.12, "sa": 0.14, "label": "Soft launch"},
    "public_launch": {"lm": 0.20, "fe": 0.14, "sa": 0.10, "label": "Public launch"},
    "waitlist_build": {"lm": 0.16, "fe": 0.10, "sa": 0.16, "label": "Waitlist build"},
    "beta_invite": {"lm": 0.12, "fe": 0.15, "sa": 0.15, "label": "Beta invite"},
    "community_seed": {"lm": 0.14, "fe": 0.09, "sa": 0.18, "label": "Community seed"},
}

# ── Growth stage scoring ─────────────────────────────────────────────
# Keys: sa=stage_alignment, lm=launch_momentum, cp=compounding_potential, fe=funnel_efficiency
STAGE = {
    "pre_launch": {"sa": 0.16, "lm": 0.08, "cp": 0.12, "fe": 0.06, "label": "Pre-launch"},
    "early_traction": {"sa": 0.14, "lm": 0.14, "cp": 0.15, "fe": 0.12, "label": "Early traction"},
    "scaling": {"sa": 0.12, "lm": 0.16, "cp": 0.18, "fe": 0.17, "label": "Scaling"},
    "mature": {"sa": 0.10, "lm": 0.10, "cp": 0.14, "fe": 0.15, "label": "Mature"},
}

# ── Conversion focus scoring ─────────────────────────────────────────
# Keys: fe=funnel_efficiency, cr=content_resonance, lm=launch_momentum
CONVERSION = {
    "awareness": {"fe": 0.06, "cr": 0.14, "lm": 0.12, "label": "Awareness"},
    "activation": {"fe": 0.14, "cr": 0.10, "lm": 0.14, "label": "Activation"},
    "retention": {"fe": 0.12, "cr": 0.08, "lm": 0.06, "label": "Retention"},
    "referral": {"fe": 0.10, "cr": 0.12, "lm": 0.10, "label": "Referral"},
    "revenue": {"fe": 0.18, "cr": 0.09, "lm": 0.16, "label": "Revenue"},
}

# ── Synergy: channel x growth_stage ──────────────────────────────────
CHANNEL_STAGE = {
    "content_marketing|pre_launch": 0.12,
    "content_marketing|early_traction": 0.10,
    "community|pre_launch": 0.14,
    "community|early_traction": 0.12,
    "product_led|early_traction": 0.13,
    "product_led|scaling": 0.15,
    "cold_outbound|scaling": 0.11,
    "cold_outbound|mature": 0.09,
    "partnerships|early_traction": 0.10,
    "partnerships|scaling": 0.12,
    "paid_acquisition|scaling": 0.08,
    "paid_acquisition|mature": 0.10,
}

# ── Synergy: content_format x conversion_focus ───────────────────────
CONTENT_CONVERSION = {
    "long_form_blog|awareness": 0.12,
    "social_threads|awareness": 0.10,
    "video_demo|activation": 0.14,
    "case_study|revenue": 0.13,
    "case_study|activation": 0.10,
    "newsletter|retention": 0.12,
    "newsletter|referral": 0.11,
}


def score(mutations: dict) -> dict:
    """Score a GTM distribution candidate. Returns metrics + verdict."""
    if not mutations:
        return {
            **BASE,
            "verdict": "baseline",
            "mechanism": "No GTM configuration specified.",
            "boundary": "Baseline only. Cannot evaluate GTM effectiveness without channel and stage.",
            "recommended_next_step": "define_distribution_channel_and_stage",
            "evidence_lane": "exploratory_frontier",
            "label": "Global baseline",
        }

    channel = CHANNEL.get(mutations.get("distribution_channel", ""), {})
    content = CONTENT.get(mutations.get("content_format", ""), {})
    launch = LAUNCH.get(mutations.get("launch_strategy", ""), {})
    stage = STAGE.get(mutations.get("growth_stage", ""), {})
    conversion = CONVERSION.get(mutations.get("conversion_focus", ""), {})

    # Synergy lookups
    cs_key = f"{mutations.get('distribution_channel', '')}|{mutations.get('growth_stage', '')}"
    cc_key = f"{mutations.get('content_format', '')}|{mutations.get('conversion_focus', '')}"
    cs_bonus = CHANNEL_STAGE.get(cs_key, -0.02)
    cc_bonus = CONTENT_CONVERSION.get(cc_key, -0.01)

    # Compute sub-metrics
    channel_leverage = _c(
        BASE["channel_leverage_score"]
        + channel.get("cl", 0)
        + content.get("cl", 0)
        + cs_bonus * 0.3
    )

    content_resonance = _c(
        BASE["content_resonance_score"]
        + content.get("cr", 0)
        + conversion.get("cr", 0)
        + cc_bonus * 0.35
    )

    launch_momentum = _c(
        BASE["launch_momentum_score"]
        + launch.get("lm", 0)
        + stage.get("lm", 0)
        + conversion.get("lm", 0)
        + cs_bonus * 0.2
    )

    funnel_efficiency = _c(
        BASE["funnel_efficiency_score"]
        + channel.get("fe", 0)
        + launch.get("fe", 0)
        + stage.get("fe", 0)
        + conversion.get("fe", 0)
        + cc_bonus * 0.25
    )

    compounding_potential = _c(
        BASE["compounding_potential_score"]
        + channel.get("cp", 0)
        + content.get("cp", 0)
        + stage.get("cp", 0)
        + launch.get("cp", 0) if "cp" in launch else 0
    )
    # Recompute cleanly
    compounding_potential = _c(
        BASE["compounding_potential_score"]
        + channel.get("cp", 0)
        + content.get("cp", 0)
        + stage.get("cp", 0)
    )

    stage_alignment = _c(
        BASE["stage_alignment_score"]
        + channel.get("sa", 0)
        + launch.get("sa", 0)
        + stage.get("sa", 0)
        + cs_bonus * 0.4
    )

    # Composite
    overall = _c(
        BASE["gtm_effectiveness_score"]
        + channel_leverage * 0.18
        + content_resonance * 0.15
        + launch_momentum * 0.16
        + funnel_efficiency * 0.18
        + compounding_potential * 0.17
        + stage_alignment * 0.16
        + cs_bonus * 0.08
        + cc_bonus * 0.06
    )

    # Bottleneck detection
    sub_metrics = [
        ("channel_gap", channel_leverage),
        ("content_gap", content_resonance),
        ("momentum_gap", launch_momentum),
        ("funnel_gap", funnel_efficiency),
        ("compounding_gap", compounding_potential),
        ("alignment_gap", stage_alignment),
    ]
    bottleneck, _ = min(sub_metrics, key=lambda x: x[1])

    next_step_map = {
        "channel_gap": "test_alternative_distribution_channel",
        "content_gap": "improve_content_format_for_audience",
        "momentum_gap": "accelerate_launch_strategy",
        "funnel_gap": "optimize_conversion_funnel",
        "compounding_gap": "build_compounding_distribution_assets",
        "alignment_gap": "realign_strategy_to_growth_stage",
    }

    lesson_map = {
        "channel_gap": "The distribution channel is not generating enough leverage for the current stage.",
        "content_gap": "Content is not resonating with the target audience or conversion goal.",
        "momentum_gap": "The launch strategy is not creating enough initial momentum.",
        "funnel_gap": "The funnel is leaking at the current conversion focus point.",
        "compounding_gap": "Distribution efforts are not building on each other over time.",
        "alignment_gap": "The GTM strategy does not match the current growth stage requirements.",
    }

    # Verdict
    if overall >= 0.77 and funnel_efficiency >= 0.58 and compounding_potential >= 0.56:
        verdict = "approve"
    elif overall >= 0.59 and (channel_leverage >= 0.50 or launch_momentum >= 0.48):
        verdict = "defer"
    else:
        verdict = "reject"

    label = " | ".join(
        part for part in [
            channel.get("label", ""),
            content.get("label", ""),
            launch.get("label", ""),
            stage.get("label", ""),
        ] if part
    )

    return {
        "gtm_effectiveness_score": overall,
        "channel_leverage_score": channel_leverage,
        "content_resonance_score": content_resonance,
        "launch_momentum_score": launch_momentum,
        "funnel_efficiency_score": funnel_efficiency,
        "compounding_potential_score": compounding_potential,
        "stage_alignment_score": stage_alignment,
        "verdict": verdict,
        "mechanism": f"GTM effectiveness compounds when {channel.get('label', 'channel')} at {stage.get('label', 'stage')} is paired with {content.get('label', 'content')} targeting {conversion.get('label', 'conversion')}.",
        "boundary": "Fixed evaluator scaffold. Does not replace real funnel analytics or customer acquisition cost data.",
        "recommended_next_step": next_step_map.get(bottleneck, "hold_for_more_evidence"),
        "evidence_lane": "exploratory_frontier",
        "bottleneck": bottleneck,
        "lesson": lesson_map.get(bottleneck, ""),
        "label": label or "Unnamed GTM play",
    }
