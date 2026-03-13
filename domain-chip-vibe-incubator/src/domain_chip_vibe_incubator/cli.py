from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .ops_loop import evaluate_ops, ops_packet_documents, ops_watchtower_pages, suggest_ops
except ImportError:
    from ops_loop import evaluate_ops, ops_packet_documents, ops_watchtower_pages, suggest_ops

M = {
    "agentic_saas": {"a": 0.15, "l": 0.12, "r": 0.16, "s": 0.09, "z": 0.08, "label": "Agentic SaaS"},
    "service_to_software": {"a": 0.10, "l": 0.13, "r": 0.18, "s": 0.05, "z": 0.09, "label": "Service to software"},
    "internal_tool_spinout": {"a": 0.17, "l": 0.18, "r": 0.10, "s": 0.13, "z": 0.11, "label": "Internal tool spinout"},
    "media_to_tools": {"a": 0.12, "l": 0.15, "r": 0.13, "s": 0.11, "z": 0.06, "d": 0.08, "label": "Media to tools"},
    "studio_shared_services": {"a": 0.14, "l": 0.17, "r": 0.11, "s": 0.12, "z": 0.14, "label": "Studio shared services"},
}
C = {
    "founder_backoffice": {"d": 0.12, "r": 0.12, "s": 0.11, "z": 0.09, "label": "Founder backoffice"},
    "agency_operators": {"d": 0.09, "r": 0.15, "s": 0.08, "z": 0.08, "label": "Agency operators"},
    "local_services": {"d": 0.05, "r": 0.16, "s": 0.05, "z": 0.07, "label": "Local services"},
    "ecommerce_ops": {"d": 0.08, "r": 0.14, "s": 0.07, "z": 0.05, "label": "E-commerce ops"},
    "creators": {"d": 0.14, "r": 0.10, "s": 0.10, "z": 0.06, "label": "Creators"},
}
D = {
    "operator_content": {"d": 0.17, "l": 0.10, "s": 0.12, "label": "Operator content"},
    "warm_outbound": {"d": 0.11, "r": 0.12, "s": 0.05, "label": "Warm outbound"},
    "design_partner_network": {"d": 0.10, "r": 0.15, "z": 0.10, "label": "Design-partner network"},
    "community_loops": {"d": 0.14, "l": 0.13, "s": 0.09, "label": "Community loops"},
    "portfolio_crosssell": {"d": 0.08, "l": 0.16, "z": 0.11, "label": "Portfolio cross-sell"},
}
B = {
    "template_factory": {"a": 0.19, "l": 0.14, "s": 0.15, "label": "Template factory"},
    "agent_workflows": {"a": 0.17, "l": 0.13, "s": 0.13, "label": "Agent workflows"},
    "custom_apps": {"a": 0.12, "l": 0.08, "s": 0.06, "r": 0.07, "label": "Custom apps"},
    "human_in_loop_ops": {"a": 0.09, "l": 0.10, "s": 0.08, "z": 0.08, "r": 0.10, "label": "Human-in-loop ops"},
    "internal_tools_first": {"a": 0.15, "l": 0.17, "s": 0.11, "z": 0.10, "label": "Internal tools first"},
}
V = {
    "paid_pilot": {"r": 0.17, "z": 0.10, "l": 0.10, "label": "Paid pilot"},
    "concierge": {"r": 0.13, "l": 0.12, "s": 0.08, "label": "Concierge"},
    "design_partner": {"r": 0.15, "z": 0.12, "l": 0.11, "label": "Design partner"},
    "audience_presell": {"d": 0.10, "r": 0.08, "l": 0.09, "label": "Audience presell"},
    "dogfood_first": {"l": 0.15, "a": 0.06, "z": 0.10, "label": "Dogfood first"},
}
T = {
    "manual_review_first": {"z": 0.16, "s": 0.06, "label": "Manual review first"},
    "audit_trails": {"z": 0.17, "l": 0.08, "s": 0.08, "label": "Audit trails"},
    "self_serve_low_risk": {"z": 0.10, "a": 0.09, "s": 0.10, "label": "Self-serve low risk"},
    "human_in_loop_sensitive": {"z": 0.18, "r": 0.07, "s": 0.05, "label": "Human-in-loop sensitive"},
}
O = {
    "daily_ship": {"a": 0.08, "l": 0.14, "s": 0.09, "label": "Daily ship"},
    "weekly_release": {"r": 0.09, "l": 0.12, "s": 0.08, "label": "Weekly release"},
    "twoweek_sprints": {"z": 0.08, "l": 0.10, "s": 0.06, "label": "Two-week sprints"},
}
MD = {"media_to_tools|operator_content": 0.14, "service_to_software|design_partner_network": 0.11, "agentic_saas|operator_content": 0.10, "internal_tool_spinout|portfolio_crosssell": 0.13, "studio_shared_services|portfolio_crosssell": 0.12}
MC = {"agentic_saas|founder_backoffice": 0.10, "service_to_software|agency_operators": 0.12, "internal_tool_spinout|founder_backoffice": 0.11, "media_to_tools|creators": 0.13, "studio_shared_services|agency_operators": 0.08}
BV = {"template_factory|paid_pilot": 0.11, "agent_workflows|design_partner": 0.09, "internal_tools_first|dogfood_first": 0.13, "human_in_loop_ops|concierge": 0.08, "custom_apps|paid_pilot": 0.07}
TC = {"audit_trails|founder_backoffice": 0.08, "manual_review_first|agency_operators": 0.07, "human_in_loop_sensitive|ecommerce_ops": 0.09, "self_serve_low_risk|creators": 0.06}
BASE = {"incubator_compound_score": 0.12, "solo_operator_fit_score": 0.16, "distribution_leverage_score": 0.17, "automation_leverage_score": 0.16, "portfolio_learning_score": 0.15, "revenue_readiness_score": 0.15, "resilience_score": 0.17, "verdict_confidence": 0.40}
GENERIC = ("ai startup", "automation tool", "agent app", "saas", "workflow tool", "startup idea", "seed_theme")


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _write(path: str, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mutations(payload: dict[str, Any]) -> dict[str, str]:
    c = payload.get("candidate", {})
    raw = c.get("mutations", {}) if isinstance(c, dict) else {}
    return {str(k): str(v) for k, v in raw.items()}


def _row_mutations(row: dict[str, Any]) -> dict[str, str]:
    muts = row.get("applied_mutations", [])
    if not isinstance(muts, list):
        return {}
    return {str(item.get("name", "")): str(item.get("value", "")) for item in muts if isinstance(item, dict) and item.get("name")}


def _c(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return cleaned.strip("-")[:64] or "unknown"


def _theme_penalty(theme: str, venture_model: str) -> float:
    lowered = theme.strip().lower()
    if not lowered:
        return 0.14 if venture_model else 0.09
    if lowered in GENERIC or any(term in lowered for term in GENERIC):
        return 0.16 if lowered in GENERIC else 0.12
    return 0.08 if len(lowered.split()) < 2 else 0.0


def _score(m: dict[str, str]) -> dict[str, Any]:
    if not m:
        return {
            **BASE,
            "theme_penalty_score": 0.74,
            "label": "Global baseline",
            "verdict": "baseline",
            "promotion_status": "advisory",
            "evidence_lane": "exploratory_frontier",
            "comparison_class": "heuristic_frontier",
            "recommended_next_step": "choose_one_customer_and_one_validation_motion",
            "claim": "An incubator with no clear venture model, distribution engine, or trust posture cannot compound.",
            "mechanism": "Solo operator leverage comes from focused venture selection, reusable build systems, fast learning loops, and trust discipline, not from trying to build everything.",
            "boundary": "Baseline only. Do not treat generic startup ambition as incubator doctrine.",
            "lesson": "Pick one venture lane, one customer surface, one distribution engine, and one validation motion before scaling the system.",
            "next_probe": "Start with a venture that can reach paid validation quickly without hidden team assumptions.",
            "bottleneck": "model_gap",
        }

    model = M.get(m.get("venture_model", ""), {})
    customer = C.get(m.get("customer_surface", ""), {})
    dist = D.get(m.get("distribution_engine", ""), {})
    build = B.get(m.get("build_stack", ""), {})
    valid = V.get(m.get("validation_motion", ""), {})
    trust = T.get(m.get("trust_model", ""), {})
    cadence = O.get(m.get("operating_cadence", ""), {})
    penalty = _theme_penalty(m.get("venture_theme", ""), m.get("venture_model", ""))
    md = MD.get(f"{m.get('venture_model', '')}|{m.get('distribution_engine', '')}", -0.03)
    mc = MC.get(f"{m.get('venture_model', '')}|{m.get('customer_surface', '')}", -0.03)
    bv = BV.get(f"{m.get('build_stack', '')}|{m.get('validation_motion', '')}", -0.02)
    tc = TC.get(f"{m.get('trust_model', '')}|{m.get('customer_surface', '')}", -0.01)
    complexity = 0.08 if m.get("build_stack") == "custom_apps" and m.get("operating_cadence") == "daily_ship" else 0.0
    fragility = 0.07 if m.get("distribution_engine") == "warm_outbound" and m.get("trust_model") == "self_serve_low_risk" else 0.0

    solo = _c(BASE["solo_operator_fit_score"] + model.get("s", 0) + customer.get("s", 0) + dist.get("s", 0) + build.get("s", 0) + valid.get("s", 0) + trust.get("s", 0) + cadence.get("s", 0) - complexity)
    distribution = _c(BASE["distribution_leverage_score"] + model.get("d", 0) + customer.get("d", 0) + dist.get("d", 0) + valid.get("d", 0) + md + mc * 0.45 - penalty - fragility)
    automation = _c(BASE["automation_leverage_score"] + model.get("a", 0) + build.get("a", 0) + valid.get("a", 0) + trust.get("a", 0) + cadence.get("a", 0) + bv * 0.45 - complexity)
    learning = _c(BASE["portfolio_learning_score"] + model.get("l", 0) + dist.get("l", 0) + build.get("l", 0) + valid.get("l", 0) + trust.get("l", 0) + cadence.get("l", 0) + bv * 0.55)
    revenue = _c(BASE["revenue_readiness_score"] + model.get("r", 0) + customer.get("r", 0) + dist.get("r", 0) + build.get("r", 0) + valid.get("r", 0) + trust.get("r", 0) + cadence.get("r", 0) + mc * 0.45 + md * 0.35 + bv * 0.40)
    resilience = _c(BASE["resilience_score"] + model.get("z", 0) + customer.get("z", 0) + dist.get("z", 0) + build.get("z", 0) + valid.get("z", 0) + trust.get("z", 0) + cadence.get("z", 0) + tc - fragility)
    overall = _c(BASE["incubator_compound_score"] + solo * 0.18 + distribution * 0.18 + automation * 0.17 + learning * 0.17 + revenue * 0.15 + resilience * 0.15 - penalty * 0.35 - complexity * 0.25)
    confidence = _c(BASE["verdict_confidence"] + overall * 0.18 + learning * 0.09 + resilience * 0.08 - penalty * 0.30)
    bottleneck, _ = min([("model_gap", solo), ("distribution_gap", distribution), ("automation_gap", automation), ("learning_gap", learning), ("revenue_gap", revenue), ("resilience_gap", resilience)], key=lambda item: item[1])
    next_step = {"model_gap": "simplify_venture_model_before_scaling", "distribution_gap": "strengthen_distribution_engine", "automation_gap": "replace_handwork_with_reusable_stack", "learning_gap": "instrument_post_launch_reviews", "revenue_gap": "move_to_paid_validation", "resilience_gap": "tighten_trust_and_audit_controls"}[bottleneck]
    if penalty >= 0.15 or solo < 0.46 or resilience < 0.48:
        verdict, promotion = "reject", "advisory"
    elif overall >= 0.79 and revenue >= 0.66 and automation >= 0.62 and resilience >= 0.63:
        verdict, promotion, next_step = "approve", "candidate_doctrine", "launch_design_partner_sprint"
    elif overall >= 0.64 and (distribution >= 0.57 or revenue >= 0.58):
        verdict, promotion = "defer", "candidate"
    else:
        verdict, promotion = "reject", "advisory"
    label = " | ".join(part for part in [model.get("label", ""), customer.get("label", ""), dist.get("label", ""), build.get("label", "")] if part)
    lesson = {"model_gap": "The venture asks the operator to carry too much ambiguity or hidden team burden.", "distribution_gap": "The incubator motion is stronger than the current path to attention and trust.", "automation_gap": "The build and operating system will create work faster than it creates leverage.", "learning_gap": "The portfolio will not compound if launches do not feed reusable doctrine and tooling back into the system.", "revenue_gap": "The motion still feels interesting before it feels sellable.", "resilience_gap": "Trust, auditability, or review controls are too thin for the venture surface."}[bottleneck]
    probe = {"model_gap": "Shrink the venture to a narrower customer pain and a delivery path that one operator plus agents can carry.", "distribution_gap": "Change the distribution surface before changing the product surface again.", "automation_gap": "Move repeated build or fulfillment steps into templates, agents, or shared internal tools.", "learning_gap": "Add post-launch review checkpoints and reusable asset capture before opening more lanes.", "revenue_gap": "Force a paid pilot, design-partner commitment, or sharper willingness-to-pay test.", "resilience_gap": "Tighten trust controls, audit trails, and human review before calling the motion scalable."}[bottleneck]
    return {"incubator_compound_score": overall, "solo_operator_fit_score": solo, "distribution_leverage_score": distribution, "automation_leverage_score": automation, "portfolio_learning_score": learning, "revenue_readiness_score": revenue, "resilience_score": resilience, "verdict_confidence": confidence, "theme_penalty_score": _c(0.20 + penalty * 2.5), "verdict": verdict, "promotion_status": promotion, "evidence_lane": "exploratory_frontier", "comparison_class": "heuristic_frontier", "recommended_next_step": next_step, "claim": f"{model.get('label', 'This venture model')} can become an incubator-worthy play only if distribution, reusable automation, and trust discipline compound together.", "mechanism": "The scaffold rewards fast paid validation, reusable build systems, operator-visible trust controls, and portfolio learning loops that make the next venture cheaper and smarter.", "boundary": "This is a fixed-evaluator scaffold, not live market proof. Do not confuse a strong incubator score with actual customer pull or operational resilience under stress.", "lesson": lesson, "next_probe": probe, "label": label or "Unnamed incubator play", "bottleneck": bottleneck}


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("command_name") or "") == "ops":
        return evaluate_ops(payload)
    result = _score(_mutations(payload))
    stdout = "\n".join([f"{name}: {result[name]}" for name in BASE])
    return {"returncode": 0, "stdout": stdout, "stderr": "", "metrics": {key: result[key] for key in BASE}, "result": result}


def _signature(m: dict[str, str]) -> tuple[str, ...]:
    return tuple(m.get(key, "") for key in ("venture_model", "customer_surface", "distribution_engine", "build_stack", "validation_motion", "trust_model", "operating_cadence", "venture_theme"))


def _seed_candidates() -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": "founder-ops-ledger",
            "candidate_summary": "Founder backoffice agentic SaaS with audit trails, design-partner validation, and a reusable template factory.",
            "hypothesis": "Founder operators reward a system that combines clear distribution, auditability, and reusable delivery assets.",
            "mutations": {"venture_model": "agentic_saas", "customer_surface": "founder_backoffice", "distribution_engine": "operator_content", "build_stack": "template_factory", "validation_motion": "design_partner", "trust_model": "audit_trails", "operating_cadence": "daily_ship", "venture_theme": "founder ops ledger"},
        },
        {
            "candidate_id": "agency-margin-engine",
            "candidate_summary": "Agency operator workflow system with warm outbound, human-in-loop ops, and paid pilot conversion pressure.",
            "hypothesis": "Agency pain turns into durable software only if revenue comes fast enough to fund reusable tooling.",
            "mutations": {"venture_model": "service_to_software", "customer_surface": "agency_operators", "distribution_engine": "warm_outbound", "build_stack": "human_in_loop_ops", "validation_motion": "paid_pilot", "trust_model": "manual_review_first", "operating_cadence": "weekly_release", "venture_theme": "agency margin engine"},
        },
        {
            "candidate_id": "portfolio-war-room",
            "candidate_summary": "Studio shared-services layer with internal tools first, cross-sell distribution, and dogfood validation.",
            "hypothesis": "The incubator compounds faster when internal leverage assets become externalizable portfolio infrastructure.",
            "mutations": {"venture_model": "studio_shared_services", "customer_surface": "founder_backoffice", "distribution_engine": "portfolio_crosssell", "build_stack": "internal_tools_first", "validation_motion": "dogfood_first", "trust_model": "audit_trails", "operating_cadence": "daily_ship", "venture_theme": "portfolio war room"},
        },
        {
            "candidate_id": "creator-automation-foundry",
            "candidate_summary": "Creator toolchain venture with audience presell, low-risk self-serve onboarding, and template-driven build leverage.",
            "hypothesis": "Creator distribution can pull ventures forward fast, but only if the toolchain becomes a real product rather than a content artifact.",
            "mutations": {"venture_model": "media_to_tools", "customer_surface": "creators", "distribution_engine": "community_loops", "build_stack": "template_factory", "validation_motion": "audience_presell", "trust_model": "self_serve_low_risk", "operating_cadence": "weekly_release", "venture_theme": "creator automation foundry"},
        },
    ]


def _dynamic_probe(best: dict[str, str], bottleneck: str) -> dict[str, str]:
    probe = dict(best)
    if bottleneck == "distribution_gap":
        probe["distribution_engine"] = "design_partner_network" if probe.get("distribution_engine") != "design_partner_network" else "operator_content"
    elif bottleneck == "automation_gap":
        probe["build_stack"] = "template_factory" if probe.get("build_stack") != "template_factory" else "agent_workflows"
    elif bottleneck == "learning_gap":
        probe["operating_cadence"] = "daily_ship"
        probe["validation_motion"] = "dogfood_first" if probe.get("validation_motion") != "dogfood_first" else "design_partner"
    elif bottleneck == "revenue_gap":
        probe["validation_motion"] = "paid_pilot"
    elif bottleneck == "resilience_gap":
        probe["trust_model"] = "audit_trails" if probe.get("trust_model") != "audit_trails" else "human_in_loop_sensitive"
    else:
        probe["venture_model"] = "internal_tool_spinout" if probe.get("venture_model") != "internal_tool_spinout" else "studio_shared_services"
        probe["build_stack"] = "internal_tools_first"
    probe["venture_theme"] = str(best.get("venture_theme") or "compound motion") + " next"
    return probe


def suggest(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("command_name") or "") == "ops":
        return suggest_ops(payload)
    limit = max(1, int(payload.get("limit", 4) or 4))
    rows = payload.get("ledger_rows", [])
    rows = rows if isinstance(rows, list) else []
    tested = {_signature(_row_mutations(row)) for row in rows}
    existing = {_signature({str(k): str(v) for k, v in item.get("mutations", {}).items()}) for item in payload.get("candidate_trials", []) if isinstance(item, dict) and isinstance(item.get("mutations"), dict)}
    suggestions: list[dict[str, Any]] = []
    reasons: list[str] = []
    for seed in _seed_candidates():
        sig = _signature(seed["mutations"])
        if sig in tested or sig in existing:
            continue
        suggestions.append(seed)
        reasons.append(f"Untested incubator play with explicit distribution, validation, and trust posture: {seed['candidate_id']}.")
        if len(suggestions) >= limit:
            break
    scored_rows = [row for row in rows if isinstance(row.get("metric_value"), (int, float))]
    scored_rows.sort(key=lambda row: float(row.get("metric_value", 0.0) or 0.0), reverse=True)
    if len(suggestions) < limit and scored_rows:
        best_mutations = _row_mutations(scored_rows[0])
        best_result = _score(best_mutations)
        probe = _dynamic_probe(best_mutations, str(best_result["bottleneck"]))
        sig = _signature(probe)
        if sig not in tested and sig not in existing:
            suggestions.append({"candidate_id": _slug(probe["venture_theme"]), "candidate_summary": f"Pressure-test the strongest incubator play against its current {best_result['bottleneck']}.", "hypothesis": "The next useful move is usually to repair the strongest play's current bottleneck instead of opening a random new lane.", "mutations": probe})
            reasons.append(f"Current best play is constrained by {best_result['bottleneck']}; probe the fix before widening the incubator.")
    baseline_metric = None
    for row in rows:
        if not row.get("applied_mutations") and isinstance(row.get("metric_value"), (int, float)):
            baseline_metric = float(row["metric_value"])
            break
    return {"baseline_metric": baseline_metric, "reasons": reasons[:limit], "suggestions": suggestions[:limit]}


def packets(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("ledger_rows", [])
    rows = rows if isinstance(rows, list) else []
    ordered = [row for row in rows if row.get("command_name") == "research" and isinstance(row.get("metric_value"), (int, float))]
    ordered.sort(key=lambda row: float(row.get("metric_value", 0.0) or 0.0), reverse=True)
    docs: list[dict[str, Any]] = []
    for row in ordered[:3]:
        result = _score(_row_mutations(row))
        slug = _slug(result["label"])
        docs.append({"kind": "benchmark_evidence", "memory_tier": "benchmark_evidence", "slug": f"vibe-incubator-evidence-{slug}", "title": f"Vibe Incubator Evidence: {result['label']}", "content": "\n".join([f"# Vibe Incubator Evidence: {result['label']}", "", "- comparison_class: `heuristic_frontier`", "- evidence_note: `fixed evaluator scaffold, not live market proof`", f"- incubator_compound_score: {result['incubator_compound_score']}", f"- solo_operator_fit_score: {result['solo_operator_fit_score']}", f"- distribution_leverage_score: {result['distribution_leverage_score']}", f"- automation_leverage_score: {result['automation_leverage_score']}", f"- portfolio_learning_score: {result['portfolio_learning_score']}", f"- revenue_readiness_score: {result['revenue_readiness_score']}", f"- resilience_score: {result['resilience_score']}", f"- verdict: {result['verdict']}", "", "## Mechanism", "", result["mechanism"], "", "## Boundary", "", result["boundary"]])})
        if result["verdict"] == "approve":
            docs.append({"kind": "grounded_doctrine", "memory_tier": "grounded_doctrine", "slug": f"vibe-incubator-doctrine-{slug}", "title": f"Vibe Incubator Doctrine Candidate: {result['label']}", "content": "\n".join([f"# Vibe Incubator Doctrine Candidate: {result['label']}", "", result["claim"], "", "Treat this as fixed-evaluator doctrine candidate only until live customer validation, portfolio reuse, and operator review confirm it."])})
    if ordered:
        weak = _score(_row_mutations(ordered[-1]))
        docs.append({"kind": "grounded_boundary", "memory_tier": "grounded_boundary", "slug": f"vibe-incubator-boundary-{_slug(weak['label'])}", "title": f"Vibe Incubator Boundary: {weak['label']}", "content": "\n".join([f"# Vibe Incubator Boundary: {weak['label']}", "", weak["boundary"], "", f"- bottleneck: `{weak['bottleneck']}`", f"- next_probe: {weak['next_probe']}"])})
    docs.append({"kind": "exploratory_frontier", "memory_tier": "exploratory_frontier", "slug": "vibe-incubator-frontier", "title": "Vibe Incubator Frontier", "content": "Next probes: " + ", ".join(seed["candidate_id"] for seed in _seed_candidates()) + ". Keep new lanes bounded and operator-legible."})
    docs.extend(ops_packet_documents(str(payload.get("runtime_root") or "")))
    return {"documents": docs}


def _coverage_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = _row_mutations(row).get(key, "")
        if value:
            counts[value] = counts.get(value, 0) + 1
    return counts


def watchtower(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary", {})
    rows = payload.get("ledger_rows", [])
    rows = rows if isinstance(rows, list) else []
    run_count = int(summary.get("run_count", 0) or 0) if isinstance(summary, dict) else 0
    ordered = [row for row in rows if row.get("command_name") == "research" and isinstance(row.get("metric_value"), (int, float))]
    ordered.sort(key=lambda row: float(row.get("metric_value", 0.0) or 0.0), reverse=True)
    best = _score(_row_mutations(ordered[0])) if ordered else _score({})
    weak = _score(_row_mutations(ordered[-1])) if ordered else _score({})
    approved = [_score(_row_mutations(row)) for row in ordered if _score(_row_mutations(row))["verdict"] == "approve"][:3]
    why_lost = []
    for row in ordered[-3:]:
        result = _score(_row_mutations(row))
        why_lost.extend([f"## {result['label']}", "", f"- score: `{result['incubator_compound_score']}`", f"- bottleneck: `{result['bottleneck']}`", f"- lesson: {result['lesson']}", ""])
    doctrine = ["# Doctrine", ""]
    if approved:
        for item in approved:
            doctrine.extend([f"## {item['label']}", "", item["claim"], "", f"- next real-world step: `{item['recommended_next_step']}`", ""])
    else:
        doctrine.extend(["No fixed-evaluator doctrine candidates have cleared the current gates yet.", "", "Treat the current strongest play as exploratory until live proof exists."])
    coverage = ["# Coverage Map", "", "## Venture Models", "", *[f"- {name}: `{count}`" for name, count in sorted(_coverage_counts(rows, 'venture_model').items())], "", "## Distribution Engines", "", *[f"- {name}: `{count}`" for name, count in sorted(_coverage_counts(rows, 'distribution_engine').items())], "", "Use this page to see whether the incubator is circling the same lane or actually broadening doctrine territory."]
    frontier = ["# Frontier Probes", "", "The incubator should expand through bounded venture plays, not vague startup brainstorming.", ""]
    for item in _seed_candidates()[:4]:
        frontier.extend([f"## {item['candidate_id']}", "", item["candidate_summary"], "", f"- hypothesis: {item['hypothesis']}", ""])
    pages = [
            {"path": "07-Domains/Vibe Incubator/Home.md", "content": "\n".join(["# Vibe Incubator Domain", "", "- mission: rebuild a powerful incubator with agentic leverage instead of missing headcount", f"- total runs: `{run_count}`", f"- best label: `{best['label']}`", f"- best incubator_compound_score: `{best['incubator_compound_score']}`", f"- best resilience_score: `{best['resilience_score']}`", f"- best verdict: `{best['verdict']}`", "", "## Views", "", "- [[07-Domains/Vibe Incubator/Doctrine]]", "- [[07-Domains/Vibe Incubator/Boundaries]]", "- [[07-Domains/Vibe Incubator/Benchmark Evidence]]", "- [[07-Domains/Vibe Incubator/Frontier Probes]]", "- [[07-Domains/Vibe Incubator/Why It Lost]]", "- [[07-Domains/Vibe Incubator/Coverage Map]]", "- [[07-Domains/Vibe Incubator/Real-World Validation]]", "- [[07-Domains/Vibe Incubator/Ops Flywheel]]", "- [[07-Domains/Vibe Incubator/Ops Queue]]", "- [[07-Domains/Vibe Incubator/Office Hours Packets]]", "- [[07-Domains/Vibe Incubator/Program State]]", "- [[07-Domains/Vibe Incubator/Decision Log]]"])} ,
            {"path": "07-Domains/Vibe Incubator/Doctrine.md", "content": "\n".join(doctrine)},
            {"path": "07-Domains/Vibe Incubator/Boundaries.md", "content": "\n".join(["# Boundaries", "", weak["boundary"], "", f"- weakest active bottleneck: `{weak['bottleneck']}`", f"- recommended next move: `{weak['recommended_next_step']}`", f"- next probe: {weak['next_probe']}"])},
            {"path": "07-Domains/Vibe Incubator/Benchmark Evidence.md", "content": "\n".join(["# Benchmark Evidence", "", "This chip currently uses a deterministic fixed evaluator rather than a live incubator benchmark.", "", f"- best solo_operator_fit_score: `{best['solo_operator_fit_score']}`", f"- best distribution_leverage_score: `{best['distribution_leverage_score']}`", f"- best automation_leverage_score: `{best['automation_leverage_score']}`", f"- best portfolio_learning_score: `{best['portfolio_learning_score']}`", f"- best revenue_readiness_score: `{best['revenue_readiness_score']}`", f"- best resilience_score: `{best['resilience_score']}`", "", "Use this page as fixed-evaluator evidence only. It does not replace live customer proof."])},
            {"path": "07-Domains/Vibe Incubator/Frontier Probes.md", "content": "\n".join(frontier)},
            {"path": "07-Domains/Vibe Incubator/Why It Lost.md", "content": "\n".join(["# Why It Lost", "", *(why_lost or ["No losing rows yet."])])},
            {"path": "07-Domains/Vibe Incubator/Coverage Map.md", "content": "\n".join(coverage)},
            {"path": "07-Domains/Vibe Incubator/Real-World Validation.md", "content": "\n".join(["# Real-World Validation", "", "A venture should not graduate from incubator doctrine candidate to real doctrine until it proves:", "", "- real paid validation or binding design-partner commitment", "- a delivery loop that one operator plus agents can sustain", "- reusable assets that lower the cost of the next venture", "- trust and review controls strong enough for the customer surface", "- post-launch learning captured back into the incubator system", "", "Priority real-world queue:", "", "1. founder backoffice command center", "2. incubator operating system", "3. agency operations autopilot", "", "Do not widen the portfolio faster than the incubator can review, secure, and learn from each launch."])},
        ]
    pages.extend(ops_watchtower_pages(str(payload.get("runtime_root") or "")))
    return {
        "pages": [
            *pages,
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="domain_chip_vibe_incubator")
    parser.add_argument("hook", choices=["evaluate", "suggest", "packets", "watchtower"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = _load(args.input)
    response = {"evaluate": evaluate, "suggest": suggest, "packets": packets, "watchtower": watchtower}[args.hook](payload)
    _write(args.output, response)


if __name__ == "__main__":
    main()
