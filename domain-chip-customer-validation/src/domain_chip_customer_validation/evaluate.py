"""Domain-specific scoring for customer validation methods."""
from __future__ import annotations


def _c(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


# ── Base scores ──────────────────────────────────────────────────────
BASE = {
    "validation_confidence_score": 0.10,
    "signal_strength_score": 0.14,
    "icp_clarity_score": 0.13,
    "method_fit_score": 0.15,
    "evidence_weight_score": 0.12,
    "market_alignment_score": 0.14,
    "scalability_signal_score": 0.11,
}

# ── Validation method scoring ────────────────────────────────────────
# Keys: ss=signal_strength, mf=method_fit, ew=evidence_weight, sc=scalability
METHOD = {
    "customer_interview": {"ss": 0.16, "mf": 0.18, "ew": 0.14, "sc": 0.05, "label": "Customer interview"},
    "landing_page_test": {"ss": 0.10, "mf": 0.12, "ew": 0.08, "sc": 0.18, "label": "Landing page test"},
    "concierge_mvp": {"ss": 0.19, "mf": 0.16, "ew": 0.17, "sc": 0.07, "label": "Concierge MVP"},
    "smoke_test": {"ss": 0.12, "mf": 0.10, "ew": 0.10, "sc": 0.16, "label": "Smoke test"},
    "letter_of_intent": {"ss": 0.22, "mf": 0.14, "ew": 0.21, "sc": 0.09, "label": "Letter of intent"},
}

# ── ICP stage scoring ────────────────────────────────────────────────
# Keys: ic=icp_clarity, ss=signal_strength, mf=method_fit, ew=evidence_weight
ICP = {
    "hypothesis": {"ic": 0.08, "ss": 0.06, "mf": 0.10, "ew": 0.05, "label": "Hypothesis"},
    "narrowing": {"ic": 0.14, "ss": 0.12, "mf": 0.13, "ew": 0.11, "label": "Narrowing"},
    "confirmed": {"ic": 0.20, "ss": 0.16, "mf": 0.15, "ew": 0.16, "label": "Confirmed"},
    "expanding": {"ic": 0.17, "ss": 0.14, "mf": 0.12, "ew": 0.14, "label": "Expanding"},
}

# ── Signal type scoring ──────────────────────────────────────────────
# Keys: ss=signal_strength, ew=evidence_weight, sc=scalability
SIGNAL = {
    "verbal_interest": {"ss": 0.06, "ew": 0.04, "sc": 0.03, "label": "Verbal interest"},
    "email_signup": {"ss": 0.10, "ew": 0.08, "sc": 0.12, "label": "Email signup"},
    "time_commitment": {"ss": 0.14, "ew": 0.12, "sc": 0.07, "label": "Time commitment"},
    "payment": {"ss": 0.20, "ew": 0.19, "sc": 0.10, "label": "Payment"},
    "referral": {"ss": 0.17, "ew": 0.16, "sc": 0.15, "label": "Referral"},
}

# ── Market type scoring ──────────────────────────────────────────────
# Keys: ma=market_alignment, sc=scalability, mf=method_fit, ew=evidence_weight
MARKET = {
    "b2b_saas": {"ma": 0.16, "sc": 0.14, "mf": 0.12, "ew": 0.13, "label": "B2B SaaS"},
    "b2c_app": {"ma": 0.12, "sc": 0.18, "mf": 0.09, "ew": 0.08, "label": "B2C App"},
    "marketplace": {"ma": 0.14, "sc": 0.16, "mf": 0.10, "ew": 0.10, "label": "Marketplace"},
    "api_platform": {"ma": 0.15, "sc": 0.13, "mf": 0.14, "ew": 0.15, "label": "API Platform"},
    "agency": {"ma": 0.18, "sc": 0.08, "mf": 0.16, "ew": 0.14, "label": "Agency"},
}

# ── Sample size scoring ──────────────────────────────────────────────
# Keys: ew=evidence_weight, ss=signal_strength, sc=scalability
SAMPLE = {
    "small_5": {"ew": 0.06, "ss": 0.08, "sc": 0.04, "label": "Small (5)"},
    "medium_15": {"ew": 0.12, "ss": 0.12, "sc": 0.10, "label": "Medium (15)"},
    "large_30_plus": {"ew": 0.18, "ss": 0.15, "sc": 0.16, "label": "Large (30+)"},
}

# ── Synergy: validation_method x market_type ─────────────────────────
METHOD_MARKET = {
    "customer_interview|b2b_saas": 0.12,
    "customer_interview|agency": 0.10,
    "concierge_mvp|b2b_saas": 0.14,
    "concierge_mvp|agency": 0.11,
    "landing_page_test|b2c_app": 0.13,
    "landing_page_test|marketplace": 0.10,
    "smoke_test|b2c_app": 0.11,
    "smoke_test|marketplace": 0.12,
    "letter_of_intent|b2b_saas": 0.15,
    "letter_of_intent|api_platform": 0.13,
}

# ── Synergy: icp_stage x signal_type ─────────────────────────────────
ICP_SIGNAL = {
    "hypothesis|verbal_interest": 0.08,
    "hypothesis|email_signup": 0.06,
    "narrowing|time_commitment": 0.11,
    "narrowing|payment": 0.09,
    "confirmed|payment": 0.14,
    "confirmed|referral": 0.13,
    "expanding|referral": 0.12,
    "expanding|payment": 0.10,
}


def score(mutations: dict) -> dict:
    """Score a customer validation candidate. Returns metrics + verdict."""
    if not mutations:
        return {
            **BASE,
            "verdict": "baseline",
            "mechanism": "No validation configuration specified.",
            "boundary": "Baseline only. Cannot assess validation confidence without method and market.",
            "recommended_next_step": "define_validation_method_and_market",
            "evidence_lane": "exploratory_frontier",
            "label": "Global baseline",
        }

    method = METHOD.get(mutations.get("validation_method", ""), {})
    icp = ICP.get(mutations.get("icp_stage", ""), {})
    signal = SIGNAL.get(mutations.get("signal_type", ""), {})
    market = MARKET.get(mutations.get("market_type", ""), {})
    sample = SAMPLE.get(mutations.get("sample_size", ""), {})

    # Synergy lookups
    mm_key = f"{mutations.get('validation_method', '')}|{mutations.get('market_type', '')}"
    is_key = f"{mutations.get('icp_stage', '')}|{mutations.get('signal_type', '')}"
    mm_bonus = METHOD_MARKET.get(mm_key, -0.02)
    is_bonus = ICP_SIGNAL.get(is_key, -0.01)

    # Compute sub-metrics
    signal_strength = _c(
        BASE["signal_strength_score"]
        + method.get("ss", 0)
        + icp.get("ss", 0)
        + signal.get("ss", 0)
        + sample.get("ss", 0)
        + is_bonus * 0.3
    )

    icp_clarity = _c(
        BASE["icp_clarity_score"]
        + icp.get("ic", 0)
        + mm_bonus * 0.2
    )

    method_fit = _c(
        BASE["method_fit_score"]
        + method.get("mf", 0)
        + icp.get("mf", 0)
        + market.get("mf", 0)
        + mm_bonus * 0.4
    )

    evidence_weight = _c(
        BASE["evidence_weight_score"]
        + method.get("ew", 0)
        + icp.get("ew", 0)
        + signal.get("ew", 0)
        + market.get("ew", 0)
        + sample.get("ew", 0)
        + is_bonus * 0.3
    )

    market_alignment = _c(
        BASE["market_alignment_score"]
        + market.get("ma", 0)
        + mm_bonus * 0.35
    )

    scalability_signal = _c(
        BASE["scalability_signal_score"]
        + method.get("sc", 0)
        + signal.get("sc", 0)
        + market.get("sc", 0)
        + sample.get("sc", 0)
    )

    # Composite
    overall = _c(
        BASE["validation_confidence_score"]
        + signal_strength * 0.20
        + icp_clarity * 0.15
        + method_fit * 0.18
        + evidence_weight * 0.22
        + market_alignment * 0.13
        + scalability_signal * 0.12
        + mm_bonus * 0.08
        + is_bonus * 0.08
    )

    # Bottleneck detection
    sub_metrics = [
        ("signal_gap", signal_strength),
        ("icp_gap", icp_clarity),
        ("method_gap", method_fit),
        ("evidence_gap", evidence_weight),
        ("market_gap", market_alignment),
        ("scalability_gap", scalability_signal),
    ]
    bottleneck, _ = min(sub_metrics, key=lambda x: x[1])

    next_step_map = {
        "signal_gap": "upgrade_signal_type_to_payment_or_commitment",
        "icp_gap": "run_more_discovery_to_narrow_icp",
        "method_gap": "switch_to_higher_fidelity_validation_method",
        "evidence_gap": "increase_sample_size_or_signal_depth",
        "market_gap": "validate_market_type_assumptions",
        "scalability_gap": "test_demand_at_larger_scale",
    }

    lesson_map = {
        "signal_gap": "Current signals are too weak to build conviction. Upgrade from verbal to payment or commitment.",
        "icp_gap": "The ideal customer profile is still too vague. More discovery conversations needed.",
        "method_gap": "The validation method does not match the market type or stage.",
        "evidence_gap": "Not enough evidence weight to support the validation claim. Larger sample or stronger signals needed.",
        "market_gap": "Market type assumptions have not been tested against real buyer behavior.",
        "scalability_gap": "Validation is not yet showing signs of repeatable demand at scale.",
    }

    # Verdict
    if overall >= 0.76 and evidence_weight >= 0.58 and signal_strength >= 0.55:
        verdict = "approve"
    elif overall >= 0.58 and (method_fit >= 0.48 or icp_clarity >= 0.45):
        verdict = "defer"
    else:
        verdict = "reject"

    label = " | ".join(
        part for part in [
            method.get("label", ""),
            icp.get("label", ""),
            signal.get("label", ""),
            market.get("label", ""),
        ] if part
    )

    return {
        "validation_confidence_score": overall,
        "signal_strength_score": signal_strength,
        "icp_clarity_score": icp_clarity,
        "method_fit_score": method_fit,
        "evidence_weight_score": evidence_weight,
        "market_alignment_score": market_alignment,
        "scalability_signal_score": scalability_signal,
        "verdict": verdict,
        "mechanism": f"Validation confidence compounds when {method.get('label', 'method')} produces {signal.get('label', 'signals')} from {market.get('label', 'market')} at {icp.get('label', 'stage')} ICP clarity.",
        "boundary": "Fixed evaluator scaffold. Does not replace real customer conversations or binding purchase commitments.",
        "recommended_next_step": next_step_map.get(bottleneck, "hold_for_more_evidence"),
        "evidence_lane": "exploratory_frontier",
        "bottleneck": bottleneck,
        "lesson": lesson_map.get(bottleneck, ""),
        "label": label or "Unnamed validation play",
    }
