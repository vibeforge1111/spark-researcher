from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SITE_TYPES = {
    "marketing_site": {"award": 0.14, "ux": 0.09, "conversion": 0.10, "access": 0.03, "label": "Marketing site"},
    "saas_dashboard": {"award": 0.10, "ux": 0.18, "conversion": 0.13, "access": 0.06, "label": "SaaS dashboard"},
    "portfolio_studio": {"award": 0.19, "ux": 0.08, "conversion": 0.05, "label": "Portfolio studio"},
    "ecommerce_storytelling": {"award": 0.16, "ux": 0.10, "conversion": 0.12, "label": "E-commerce storytelling"},
    "editorial_brand": {"award": 0.17, "ux": 0.11, "conversion": 0.07, "label": "Editorial brand"},
}
DESIGN_DIRECTIONS = {
    "editorial_minimal": {"award": 0.12, "ux": 0.10, "access": 0.06, "label": "Editorial minimal"},
    "expressive_brutalist": {"award": 0.16, "ux": 0.04, "access": -0.04, "label": "Expressive brutalist"},
    "premium_motion": {"award": 0.15, "interaction": 0.16, "ux": 0.03, "access": -0.03, "label": "Premium motion"},
    "product_precision": {"award": 0.09, "ux": 0.15, "conversion": 0.08, "access": 0.05, "label": "Product precision"},
    "playful_3d": {"award": 0.14, "interaction": 0.18, "ux": -0.02, "access": -0.05, "label": "Playful 3D"},
}
NARRATIVE_MODELS = {
    "problem_proof_product": {"ux": 0.13, "conversion": 0.13, "label": "Problem-proof-product"},
    "story_demo_socialproof": {"award": 0.08, "ux": 0.09, "conversion": 0.11, "label": "Story-demo-social proof"},
    "portfolio_case_study": {"award": 0.13, "ux": 0.08, "conversion": 0.06, "label": "Portfolio case study"},
    "collection_feature_grid": {"award": 0.06, "ux": 0.08, "conversion": 0.10, "label": "Collection feature grid"},
    "dashboard_task_first": {"ux": 0.16, "conversion": 0.09, "access": 0.04, "label": "Dashboard task first"},
}
INTERACTION_MODELS = {
    "restrained": {"award": 0.04, "ux": 0.10, "interaction": 0.05, "access": 0.08, "label": "Restrained"},
    "guided_motion": {"award": 0.11, "ux": 0.06, "interaction": 0.12, "label": "Guided motion"},
    "immersive_scrollytelling": {"award": 0.15, "ux": -0.01, "interaction": 0.16, "access": -0.06, "label": "Immersive scrollytelling"},
    "micro_interaction_rich": {"award": 0.09, "ux": 0.04, "interaction": 0.14, "access": -0.02, "label": "Micro-interaction rich"},
    "app_like": {"ux": 0.12, "interaction": 0.10, "conversion": 0.08, "access": 0.02, "label": "App-like"},
}
PROOF_SURFACES = {
    "case_studies": {"award": 0.04, "ux": 0.08, "conversion": 0.11, "label": "Case studies"},
    "product_demo": {"ux": 0.10, "conversion": 0.12, "label": "Product demo"},
    "customer_logos": {"conversion": 0.07, "label": "Customer logos"},
    "metrics_benchmarks": {"ux": 0.05, "conversion": 0.10, "label": "Metrics and benchmarks"},
    "process_transparency": {"award": 0.06, "ux": 0.09, "label": "Process transparency"},
}
CONVERSION_STRATEGIES = {
    "single_primary_cta": {"ux": 0.08, "conversion": 0.11, "label": "Single primary CTA"},
    "dual_path_cta": {"ux": 0.07, "conversion": 0.10, "label": "Dual-path CTA"},
    "self_serve_demo": {"ux": 0.08, "conversion": 0.13, "label": "Self-serve demo"},
    "contact_qualification": {"ux": 0.03, "conversion": 0.08, "label": "Contact qualification"},
    "explore_then_convert": {"award": 0.06, "ux": 0.02, "conversion": -0.02, "label": "Explore then convert"},
}
ACCESSIBILITY_MODES = {
    "wcag_aa_default": {"ux": 0.08, "interaction": 0.01, "conversion": 0.04, "access": 0.16, "label": "WCAG AA default"},
    "motion_respectful": {"ux": 0.07, "interaction": 0.03, "access": 0.18, "label": "Motion respectful"},
    "contrast_first": {"ux": 0.09, "access": 0.15, "label": "Contrast first"},
    "keyboard_first": {"ux": 0.08, "access": 0.16, "label": "Keyboard first"},
    "experimental": {"award": 0.07, "ux": -0.04, "access": -0.08, "label": "Experimental"},
}
PAIR_BONUS = {
    "marketing_site|premium_motion": 0.03,
    "marketing_site|problem_proof_product": 0.03,
    "saas_dashboard|product_precision": 0.05,
    "saas_dashboard|dashboard_task_first": 0.06,
    "portfolio_studio|portfolio_case_study": 0.05,
    "editorial_brand|editorial_minimal": 0.04,
    "ecommerce_storytelling|collection_feature_grid": 0.04,
    "guided_motion|motion_respectful": 0.03,
    "app_like|self_serve_demo": 0.04,
    "immersive_scrollytelling|experimental": -0.08,
    "playful_3d|experimental": -0.06,
}
SYSTEM_BONUS = {
    "marketing_site|premium_motion|problem_proof_product|guided_motion|product_demo|single_primary_cta|motion_respectful": 0.11,
    "saas_dashboard|product_precision|dashboard_task_first|app_like|product_demo|self_serve_demo|keyboard_first": 0.14,
    "portfolio_studio|expressive_brutalist|portfolio_case_study|guided_motion|process_transparency|explore_then_convert|motion_respectful": 0.10,
    "editorial_brand|editorial_minimal|story_demo_socialproof|restrained|case_studies|dual_path_cta|contrast_first": 0.09,
    "ecommerce_storytelling|premium_motion|collection_feature_grid|micro_interaction_rich|metrics_benchmarks|single_primary_cta|wcag_aa_default": 0.10,
}
BASE = {
    "award_signal_score": 0.28,
    "ux_system_score": 0.29,
    "interaction_craft_score": 0.25,
    "conversion_clarity_score": 0.24,
    "accessibility_safety_score": 0.32,
    "verdict_confidence": 0.46,
}
FIELDS = (
    "site_type",
    "design_direction",
    "narrative_model",
    "interaction_model",
    "proof_surface",
    "conversion_strategy",
    "accessibility_mode",
)


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _write(path: str, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mutations(payload: dict[str, Any]) -> dict[str, str]:
    candidate = payload.get("candidate", {})
    raw = candidate.get("mutations", {}) if isinstance(candidate, dict) else {}
    return {str(key): str(value) for key, value in raw.items()}


def _row_mutations(row: dict[str, Any]) -> dict[str, str]:
    mutations = row.get("applied_mutations", [])
    if not isinstance(mutations, list):
        return {}
    return {
        str(item.get("name", "")): str(item.get("value", ""))
        for item in mutations
        if isinstance(item, dict) and item.get("name")
    }


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return cleaned.strip("-")[:64] or "candidate"


def _clamp(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


def _pair_bonus(mutations: dict[str, str]) -> float:
    pairs = [
        f"{mutations.get('site_type', '')}|{mutations.get('design_direction', '')}",
        f"{mutations.get('site_type', '')}|{mutations.get('narrative_model', '')}",
        f"{mutations.get('interaction_model', '')}|{mutations.get('accessibility_mode', '')}",
        f"{mutations.get('interaction_model', '')}|{mutations.get('conversion_strategy', '')}",
        f"{mutations.get('design_direction', '')}|{mutations.get('accessibility_mode', '')}",
    ]
    return sum(PAIR_BONUS.get(pair, 0.0) for pair in pairs)


def _system_bonus(mutations: dict[str, str]) -> float:
    signature = "|".join(mutations.get(field, "") for field in FIELDS)
    return SYSTEM_BONUS.get(signature, 0.0)


def _label(mutations: dict[str, str]) -> str:
    lookups = [
        SITE_TYPES.get(mutations.get("site_type", ""), {}),
        DESIGN_DIRECTIONS.get(mutations.get("design_direction", ""), {}),
        NARRATIVE_MODELS.get(mutations.get("narrative_model", ""), {}),
        INTERACTION_MODELS.get(mutations.get("interaction_model", ""), {}),
        PROOF_SURFACES.get(mutations.get("proof_surface", ""), {}),
        CONVERSION_STRATEGIES.get(mutations.get("conversion_strategy", ""), {}),
        ACCESSIBILITY_MODES.get(mutations.get("accessibility_mode", ""), {}),
    ]
    return " | ".join(item["label"] for item in lookups if item.get("label"))


def _score(mutations: dict[str, str]) -> dict[str, Any]:
    if not mutations:
        return {
            **BASE,
            "web_design_score": 0.31,
            "verdict": "baseline",
            "promotion_status": "advisory",
            "evidence_lane": "exploratory_frontier",
            "comparison_class": "heuristic_frontier",
            "recommended_next_step": "pick_one_coherent_reference_stack",
            "claim": "Generic web design advice does not reliably produce memorable or usable websites.",
            "mechanism": "Without a coherent site type, narrative, interaction, proof, and accessibility posture, the design system fragments.",
            "boundary": "Baseline only. Do not promote.",
            "lesson": "World-class web design needs a point of view plus guardrails.",
            "next_probe": "Start with one site archetype and one design direction instead of mixing styles.",
            "top_bottleneck": "coherence_gap",
            "label": "Global baseline",
        }

    site = SITE_TYPES.get(mutations.get("site_type", ""), {})
    design = DESIGN_DIRECTIONS.get(mutations.get("design_direction", ""), {})
    narrative = NARRATIVE_MODELS.get(mutations.get("narrative_model", ""), {})
    interaction = INTERACTION_MODELS.get(mutations.get("interaction_model", ""), {})
    proof = PROOF_SURFACES.get(mutations.get("proof_surface", ""), {})
    conversion = CONVERSION_STRATEGIES.get(mutations.get("conversion_strategy", ""), {})
    access = ACCESSIBILITY_MODES.get(mutations.get("accessibility_mode", ""), {})

    pair_bonus = _pair_bonus(mutations)
    system_bonus = _system_bonus(mutations)

    award = _clamp(
        BASE["award_signal_score"]
        + site.get("award", 0.0)
        + design.get("award", 0.0)
        + narrative.get("award", 0.0)
        + interaction.get("award", 0.0)
        + proof.get("award", 0.0)
        + conversion.get("award", 0.0)
        + access.get("award", 0.0)
        + pair_bonus * 0.55
        + system_bonus * 0.55
    )
    ux = _clamp(
        BASE["ux_system_score"]
        + site.get("ux", 0.0)
        + design.get("ux", 0.0)
        + narrative.get("ux", 0.0)
        + interaction.get("ux", 0.0)
        + proof.get("ux", 0.0)
        + conversion.get("ux", 0.0)
        + access.get("ux", 0.0)
        + pair_bonus * 0.45
        + system_bonus * 0.35
    )
    interaction_score = _clamp(
        BASE["interaction_craft_score"]
        + design.get("interaction", 0.0)
        + interaction.get("interaction", 0.0)
        + access.get("interaction", 0.0)
        + pair_bonus * 0.35
        + system_bonus * 0.45
    )
    conversion_score = _clamp(
        BASE["conversion_clarity_score"]
        + site.get("conversion", 0.0)
        + design.get("conversion", 0.0)
        + narrative.get("conversion", 0.0)
        + interaction.get("conversion", 0.0)
        + proof.get("conversion", 0.0)
        + conversion.get("conversion", 0.0)
        + access.get("conversion", 0.0)
        + pair_bonus * 0.40
        + system_bonus * 0.30
    )
    accessibility = _clamp(
        BASE["accessibility_safety_score"]
        + site.get("access", 0.0)
        + design.get("access", 0.0)
        + narrative.get("access", 0.0)
        + interaction.get("access", 0.0)
        + access.get("access", 0.0)
        + pair_bonus * 0.30
        + system_bonus * 0.25
    )
    overall = _clamp(
        award * 0.26
        + ux * 0.24
        + interaction_score * 0.18
        + conversion_score * 0.18
        + accessibility * 0.14
        + pair_bonus * 0.35
        + system_bonus * 0.45
    )
    confidence = _clamp(
        BASE["verdict_confidence"]
        + overall * 0.16
        + min(ux, accessibility, conversion_score) * 0.08
        + system_bonus * 0.20
    )

    weakest = min(
        [
            ("award_gap", award),
            ("ux_gap", ux),
            ("interaction_gap", interaction_score),
            ("conversion_gap", conversion_score),
            ("accessibility_gap", accessibility),
        ],
        key=lambda item: item[1],
    )[0]
    next_step = {
        "award_gap": "tighten_visual_point_of_view",
        "ux_gap": "simplify_information_architecture",
        "interaction_gap": "improve_motion_hierarchy",
        "conversion_gap": "clarify_primary_action_path",
        "accessibility_gap": "repair_accessibility_and_motion_safety",
    }[weakest]

    if overall >= 0.80 and ux >= 0.68 and conversion_score >= 0.62 and accessibility >= 0.70:
        verdict, promotion, lane, klass = "approve", "validated", "benchmark_grounded", "benchmark_grounded"
    elif overall >= 0.66 and ux >= 0.56 and accessibility >= 0.54:
        verdict, promotion, lane, klass = "defer", "candidate", "benchmark_grounded", "heuristic_frontier"
    else:
        verdict, promotion, lane, klass = "reject", "advisory", "exploratory_frontier", "heuristic_frontier"

    lesson = {
        "award_gap": "The system is usable but does not yet feel distinct or compositionally strong.",
        "ux_gap": "The visuals may be interesting, but the UX contract is still muddy.",
        "interaction_gap": "Motion and interface states are not yet doing enough design work.",
        "conversion_gap": "The page looks strong, but the user path to action is still weak.",
        "accessibility_gap": "The design direction is over-spending on style and under-spending on inclusive use.",
    }[weakest]
    probe = {
        "award_gap": "Deepen type, spacing, rhythm, and reference discipline before adding more effects.",
        "ux_gap": "Reduce sections, sharpen hierarchy, and make task flow legible in the first screenful.",
        "interaction_gap": "Use fewer but more purposeful transitions and state changes.",
        "conversion_gap": "Tie proof and CTA closer to the user decision moment.",
        "accessibility_gap": "Audit motion, keyboard flow, contrast, and semantic structure before styling further.",
    }[weakest]

    return {
        "award_signal_score": award,
        "ux_system_score": ux,
        "interaction_craft_score": interaction_score,
        "conversion_clarity_score": conversion_score,
        "accessibility_safety_score": accessibility,
        "verdict_confidence": confidence,
        "web_design_score": overall,
        "verdict": verdict,
        "promotion_status": promotion,
        "evidence_lane": lane,
        "comparison_class": klass,
        "recommended_next_step": next_step,
        "claim": f"{site.get('label', 'This site')} becomes stronger when {design.get('label', 'its design direction')} is matched with {narrative.get('label', 'a coherent narrative')} and an accessibility-aware interaction model.",
        "mechanism": "The benchmark rewards systems that align visual taste, narrative clarity, interaction hierarchy, conversion logic, and accessibility safety.",
        "boundary": "Award resemblance is not proof of usability, conversion, or real-world business performance.",
        "lesson": lesson,
        "next_probe": probe,
        "top_bottleneck": weakest,
        "label": _label(mutations) or "Unnamed web system",
    }


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    result = _score(_mutations(payload))
    stdout = "\n".join(
        [
            "web_design_score: " + str(result["web_design_score"]),
            "award_signal_score: " + str(result["award_signal_score"]),
            "ux_system_score: " + str(result["ux_system_score"]),
            "interaction_craft_score: " + str(result["interaction_craft_score"]),
            "conversion_clarity_score: " + str(result["conversion_clarity_score"]),
            "accessibility_safety_score: " + str(result["accessibility_safety_score"]),
            "verdict_confidence: " + str(result["verdict_confidence"]),
        ]
    )
    metrics = {key: result[key] for key in BASE}
    metrics["web_design_score"] = result["web_design_score"]
    return {"returncode": 0, "stdout": stdout, "stderr": "", "metrics": metrics, "result": result}


def suggest(payload: dict[str, Any]) -> dict[str, Any]:
    limit = max(1, int(payload.get("limit", 4) or 4))
    rows = payload.get("ledger_rows", [])
    rows = rows if isinstance(rows, list) else []
    tested = {tuple(_row_mutations(row).get(field, "") for field in FIELDS) for row in rows}
    existing = {
        tuple(str(mutations.get(field, "")) for field in FIELDS)
        for item in payload.get("candidate_trials", [])
        if isinstance(item, dict)
        for mutations in [item.get("mutations", {})]
        if isinstance(mutations, dict)
    }
    seeds = [
        {
            "site_type": "marketing_site",
            "design_direction": "premium_motion",
            "narrative_model": "problem_proof_product",
            "interaction_model": "guided_motion",
            "proof_surface": "product_demo",
            "conversion_strategy": "single_primary_cta",
            "accessibility_mode": "motion_respectful",
        },
        {
            "site_type": "saas_dashboard",
            "design_direction": "product_precision",
            "narrative_model": "dashboard_task_first",
            "interaction_model": "app_like",
            "proof_surface": "product_demo",
            "conversion_strategy": "self_serve_demo",
            "accessibility_mode": "keyboard_first",
        },
        {
            "site_type": "portfolio_studio",
            "design_direction": "expressive_brutalist",
            "narrative_model": "portfolio_case_study",
            "interaction_model": "guided_motion",
            "proof_surface": "process_transparency",
            "conversion_strategy": "explore_then_convert",
            "accessibility_mode": "motion_respectful",
        },
        {
            "site_type": "editorial_brand",
            "design_direction": "editorial_minimal",
            "narrative_model": "story_demo_socialproof",
            "interaction_model": "restrained",
            "proof_surface": "case_studies",
            "conversion_strategy": "dual_path_cta",
            "accessibility_mode": "contrast_first",
        },
        {
            "site_type": "ecommerce_storytelling",
            "design_direction": "premium_motion",
            "narrative_model": "collection_feature_grid",
            "interaction_model": "micro_interaction_rich",
            "proof_surface": "metrics_benchmarks",
            "conversion_strategy": "single_primary_cta",
            "accessibility_mode": "wcag_aa_default",
        },
    ]
    suggestions: list[dict[str, Any]] = []
    reasons: list[str] = []
    for seed in seeds:
        signature = tuple(seed[field] for field in FIELDS)
        if signature in tested or signature in existing:
            continue
        result = _score(seed)
        suggestions.append(
            {
                "candidate_id": _slug("-".join(signature[:3])),
                "candidate_summary": f"Probe {seed['site_type']} with {seed['design_direction']} and {seed['narrative_model']}.",
                "hypothesis": "A coherent reference stack should outperform generic visual mixing on both award and UX metrics.",
                "mutations": seed,
            }
        )
        reasons.append(
            f"Untested high-coherence system: {result['label']} projects to {result['web_design_score']} with bottleneck {result['top_bottleneck']}."
        )
        if len(suggestions) >= limit:
            break
    return {"baseline_metric": None, "reasons": reasons, "suggestions": suggestions}


def packets(payload: dict[str, Any]) -> dict[str, Any]:
    mutations = _mutations(payload)
    result = _score(mutations)
    slug = _slug(result["label"])
    content = "\n".join(
        [
            f"# {result['label']}",
            "",
            "## Verdict",
            f"- status: {result['promotion_status']}",
            f"- verdict: {result['verdict']}",
            f"- web_design_score: {result['web_design_score']}",
            f"- award_signal_score: {result['award_signal_score']}",
            f"- ux_system_score: {result['ux_system_score']}",
            f"- interaction_craft_score: {result['interaction_craft_score']}",
            f"- conversion_clarity_score: {result['conversion_clarity_score']}",
            f"- accessibility_safety_score: {result['accessibility_safety_score']}",
            "",
            "## Claim",
            result["claim"],
            "",
            "## Mechanism",
            result["mechanism"],
            "",
            "## Boundary",
            result["boundary"],
            "",
            "## Next Probe",
            result["next_probe"],
        ]
    )
    documents = [
        {
            "kind": "web_design_system",
            "slug": slug,
            "title": result["label"],
            "content": content,
        },
        {
            "kind": "web_design_lesson",
            "slug": slug + "-lesson",
            "title": "Web Design Lesson",
            "content": "# Lesson\n\n" + result["lesson"],
        },
    ]
    return {"documents": documents}


def watchtower(payload: dict[str, Any]) -> dict[str, Any]:
    mutations = _mutations(payload)
    result = _score(mutations)
    score_lines = [
        f"- web design score: {result['web_design_score']}",
        f"- award signal: {result['award_signal_score']}",
        f"- ux system: {result['ux_system_score']}",
        f"- interaction craft: {result['interaction_craft_score']}",
        f"- conversion clarity: {result['conversion_clarity_score']}",
        f"- accessibility safety: {result['accessibility_safety_score']}",
        f"- promotion status: {result['promotion_status']}",
    ]
    selected = [f"- {field}: {mutations[field]}" for field in FIELDS if field in mutations]
    home = "\n".join(
        [
            "# Web Design Domain",
            "",
            "This page tracks the current evaluated website system.",
            "",
            "## Current Candidate",
            result["label"],
            "",
            "## Scores",
            *score_lines,
            "",
            "## Mutations",
            *(selected or ["- baseline"]),
            "",
            "## Next Step",
            result["recommended_next_step"],
        ]
    )
    loop = "\n".join(
        [
            "# Web Design Learning Loop",
            "",
            "1. Research award winners and inspiration references.",
            "2. Normalize them into reusable visual and UX patterns.",
            "3. Evaluate candidate systems against craft, UX, conversion, and accessibility.",
            "4. Promote only candidates that survive benchmark and real-world checks.",
        ]
    )
    return {
        "pages": [
            {"path": "07-Domains/Web Design/Home.md", "content": home},
            {"path": "07-Domains/Web Design/Learning Loop.md", "content": loop},
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="domain_chip_web_designer")
    parser.add_argument("hook", choices=["evaluate", "suggest", "packets", "watchtower"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = _load(args.input)
    if args.hook == "evaluate":
        response = evaluate(payload)
    elif args.hook == "suggest":
        response = suggest(payload)
    elif args.hook == "packets":
        response = packets(payload)
    else:
        response = watchtower(payload)
    _write(args.output, response)


if __name__ == "__main__":
    main()
