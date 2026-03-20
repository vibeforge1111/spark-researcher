"""Domain-specific scoring for trust posture and compliance readiness."""
from __future__ import annotations


def _c(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


# ── Base scores ──────────────────────────────────────────────────────
BASE = {
    "trust_health_score": 0.12,
    "risk_coverage_score": 0.14,
    "review_thoroughness_score": 0.13,
    "regulatory_alignment_score": 0.15,
    "signal_accuracy_score": 0.16,
    "remediation_readiness_score": 0.13,
    "compliance_maturity_score": 0.12,
}

# ── Risk domain scoring ─────────────────────────────────────────────
# Keys: rc=risk_coverage, cm=compliance_maturity, ra=regulatory_alignment, sa=signal_accuracy
RISK = {
    "data_privacy": {"rc": 0.16, "cm": 0.14, "ra": 0.18, "sa": 0.12, "label": "Data privacy"},
    "financial_compliance": {"rc": 0.18, "cm": 0.17, "ra": 0.20, "sa": 0.14, "label": "Financial compliance"},
    "security_posture": {"rc": 0.20, "cm": 0.12, "ra": 0.14, "sa": 0.18, "label": "Security posture"},
    "legal_structure": {"rc": 0.12, "cm": 0.16, "ra": 0.15, "sa": 0.10, "label": "Legal structure"},
    "ip_protection": {"rc": 0.14, "cm": 0.13, "ra": 0.10, "sa": 0.11, "label": "IP protection"},
}

# ── Review depth scoring ─────────────────────────────────────────────
# Keys: rt=review_thoroughness, rc=risk_coverage, cm=compliance_maturity, rr=remediation_readiness
REVIEW = {
    "surface_scan": {"rt": 0.08, "rc": 0.06, "cm": 0.05, "rr": 0.06, "label": "Surface scan"},
    "standard_review": {"rt": 0.15, "rc": 0.13, "cm": 0.12, "rr": 0.12, "label": "Standard review"},
    "deep_audit": {"rt": 0.22, "rc": 0.19, "cm": 0.18, "rr": 0.16, "label": "Deep audit"},
}

# ── Regulatory context scoring ───────────────────────────────────────
# Keys: ra=regulatory_alignment, cm=compliance_maturity, rt=review_thoroughness
REGULATORY = {
    "pre_revenue_light": {"ra": 0.08, "cm": 0.06, "rt": 0.05, "label": "Pre-revenue light"},
    "b2b_standard": {"ra": 0.14, "cm": 0.12, "rt": 0.10, "label": "B2B standard"},
    "fintech_regulated": {"ra": 0.20, "cm": 0.18, "rt": 0.16, "label": "Fintech regulated"},
    "health_hipaa": {"ra": 0.22, "cm": 0.19, "rt": 0.18, "label": "Health HIPAA"},
    "eu_gdpr": {"ra": 0.19, "cm": 0.17, "rt": 0.15, "label": "EU GDPR"},
}

# ── Trust signal scoring ─────────────────────────────────────────────
# Keys: sa=signal_accuracy, rr=remediation_readiness, rc=risk_coverage
SIGNAL = {
    "green_clear": {"sa": 0.18, "rr": 0.06, "rc": 0.10, "label": "Green (clear)"},
    "amber_watch": {"sa": 0.14, "rr": 0.14, "rc": 0.14, "label": "Amber (watch)"},
    "red_escalate": {"sa": 0.10, "rr": 0.20, "rc": 0.18, "label": "Red (escalate)"},
}

# ── Remediation urgency scoring ──────────────────────────────────────
# Keys: rr=remediation_readiness, sa=signal_accuracy, cm=compliance_maturity
REMEDIATION = {
    "preventive": {"rr": 0.10, "sa": 0.14, "cm": 0.12, "label": "Preventive"},
    "corrective": {"rr": 0.16, "sa": 0.10, "cm": 0.10, "label": "Corrective"},
    "emergency": {"rr": 0.22, "sa": 0.06, "cm": 0.05, "label": "Emergency"},
}

# ── Synergy: risk_domain x regulatory_context ────────────────────────
RISK_REGULATORY = {
    "data_privacy|eu_gdpr": 0.14,
    "data_privacy|health_hipaa": 0.12,
    "data_privacy|b2b_standard": 0.08,
    "financial_compliance|fintech_regulated": 0.16,
    "financial_compliance|b2b_standard": 0.10,
    "security_posture|eu_gdpr": 0.11,
    "security_posture|fintech_regulated": 0.13,
    "security_posture|health_hipaa": 0.12,
    "legal_structure|pre_revenue_light": 0.09,
    "legal_structure|b2b_standard": 0.08,
    "ip_protection|pre_revenue_light": 0.07,
    "ip_protection|b2b_standard": 0.06,
}

# ── Synergy: trust_signal x remediation_urgency ─────────────────────
SIGNAL_REMEDIATION = {
    "green_clear|preventive": 0.14,
    "green_clear|corrective": 0.04,
    "green_clear|emergency": -0.06,
    "amber_watch|preventive": 0.06,
    "amber_watch|corrective": 0.12,
    "amber_watch|emergency": 0.05,
    "red_escalate|preventive": -0.05,
    "red_escalate|corrective": 0.08,
    "red_escalate|emergency": 0.15,
}

# ── Anti-synergy: under-review for severity ──────────────────────────
UNDER_REVIEW_PENALTY = {
    "red_escalate|surface_scan": 0.12,
    "amber_watch|surface_scan": 0.06,
}


def score(mutations: dict) -> dict:
    """Score a trust compliance candidate. Returns metrics + verdict."""
    if not mutations:
        return {
            **BASE,
            "verdict": "baseline",
            "mechanism": "No trust configuration specified.",
            "boundary": "Baseline only. Cannot evaluate trust health without risk domain and trust signal.",
            "recommended_next_step": "define_risk_domain_and_trust_signal",
            "evidence_lane": "exploratory_frontier",
            "label": "Global baseline",
        }

    risk = RISK.get(mutations.get("risk_domain", ""), {})
    review = REVIEW.get(mutations.get("review_depth", ""), {})
    regulatory = REGULATORY.get(mutations.get("regulatory_context", ""), {})
    signal = SIGNAL.get(mutations.get("trust_signal", ""), {})
    remediation = REMEDIATION.get(mutations.get("remediation_urgency", ""), {})

    # Synergy lookups
    rr_key = f"{mutations.get('risk_domain', '')}|{mutations.get('regulatory_context', '')}"
    sr_key = f"{mutations.get('trust_signal', '')}|{mutations.get('remediation_urgency', '')}"
    ur_key = f"{mutations.get('trust_signal', '')}|{mutations.get('review_depth', '')}"
    rr_bonus = RISK_REGULATORY.get(rr_key, -0.02)
    sr_bonus = SIGNAL_REMEDIATION.get(sr_key, -0.01)
    ur_penalty = UNDER_REVIEW_PENALTY.get(ur_key, 0.0)

    # Compute sub-metrics
    risk_coverage = _c(
        BASE["risk_coverage_score"]
        + risk.get("rc", 0)
        + review.get("rc", 0)
        + signal.get("rc", 0)
        + rr_bonus * 0.25
        - ur_penalty
    )

    review_thoroughness = _c(
        BASE["review_thoroughness_score"]
        + review.get("rt", 0)
        + regulatory.get("rt", 0)
        - ur_penalty * 0.5
    )

    regulatory_alignment = _c(
        BASE["regulatory_alignment_score"]
        + risk.get("ra", 0)
        + regulatory.get("ra", 0)
        + rr_bonus * 0.4
    )

    signal_accuracy = _c(
        BASE["signal_accuracy_score"]
        + risk.get("sa", 0)
        + signal.get("sa", 0)
        + remediation.get("sa", 0)
        + sr_bonus * 0.3
    )

    remediation_readiness = _c(
        BASE["remediation_readiness_score"]
        + review.get("rr", 0)
        + signal.get("rr", 0)
        + remediation.get("rr", 0)
        + sr_bonus * 0.35
    )

    compliance_maturity = _c(
        BASE["compliance_maturity_score"]
        + risk.get("cm", 0)
        + review.get("cm", 0)
        + regulatory.get("cm", 0)
        + remediation.get("cm", 0)
        + rr_bonus * 0.2
    )

    # Composite
    overall = _c(
        BASE["trust_health_score"]
        + risk_coverage * 0.17
        + review_thoroughness * 0.15
        + regulatory_alignment * 0.18
        + signal_accuracy * 0.16
        + remediation_readiness * 0.17
        + compliance_maturity * 0.17
        + rr_bonus * 0.06
        + sr_bonus * 0.06
        - ur_penalty * 0.12
    )

    # Bottleneck detection
    sub_metrics = [
        ("coverage_gap", risk_coverage),
        ("thoroughness_gap", review_thoroughness),
        ("regulatory_gap", regulatory_alignment),
        ("signal_gap", signal_accuracy),
        ("remediation_gap", remediation_readiness),
        ("maturity_gap", compliance_maturity),
    ]
    bottleneck, _ = min(sub_metrics, key=lambda x: x[1])

    next_step_map = {
        "coverage_gap": "expand_risk_coverage_scope",
        "thoroughness_gap": "increase_review_depth",
        "regulatory_gap": "align_controls_to_regulatory_requirements",
        "signal_gap": "improve_trust_signal_detection_accuracy",
        "remediation_gap": "build_remediation_playbooks",
        "maturity_gap": "invest_in_compliance_infrastructure",
    }

    lesson_map = {
        "coverage_gap": "Risk coverage is too narrow. Key risk domains are not being monitored.",
        "thoroughness_gap": "Review depth is insufficient for the current trust signal severity.",
        "regulatory_gap": "Controls do not align with the regulatory context. Compliance gaps are likely.",
        "signal_gap": "Trust signal detection is unreliable. Real issues may be missed or false-alarmed.",
        "remediation_gap": "Remediation playbooks are missing or untested. Response time will be too slow.",
        "maturity_gap": "Compliance infrastructure is immature. Processes are ad-hoc rather than systematic.",
    }

    # Verdict
    if overall >= 0.78 and regulatory_alignment >= 0.60 and risk_coverage >= 0.56:
        verdict = "approve"
    elif overall >= 0.58 and (signal_accuracy >= 0.50 or remediation_readiness >= 0.48):
        verdict = "defer"
    else:
        verdict = "reject"

    label = " | ".join(
        part for part in [
            risk.get("label", ""),
            review.get("label", ""),
            regulatory.get("label", ""),
            signal.get("label", ""),
        ] if part
    )

    return {
        "trust_health_score": overall,
        "risk_coverage_score": risk_coverage,
        "review_thoroughness_score": review_thoroughness,
        "regulatory_alignment_score": regulatory_alignment,
        "signal_accuracy_score": signal_accuracy,
        "remediation_readiness_score": remediation_readiness,
        "compliance_maturity_score": compliance_maturity,
        "verdict": verdict,
        "mechanism": f"Trust health compounds when {risk.get('label', 'risk')} is reviewed at {review.get('label', 'depth')} under {regulatory.get('label', 'regulation')} with {signal.get('label', 'signal')} posture.",
        "boundary": "Fixed evaluator scaffold. Does not replace real compliance audits or legal counsel.",
        "recommended_next_step": next_step_map.get(bottleneck, "hold_for_more_evidence"),
        "evidence_lane": "exploratory_frontier",
        "bottleneck": bottleneck,
        "lesson": lesson_map.get(bottleneck, ""),
        "label": label or "Unnamed trust play",
    }
