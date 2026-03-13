from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MOTIONS = {
    "founder_led_content": {"d": 0.16, "s": 0.08, "label": "Founder-led content"},
    "programmatic_seo": {"d": 0.18, "s": 0.14, "label": "Programmatic SEO"},
    "signal_based_outbound": {"d": 0.13, "s": 0.18, "label": "Signal-based outbound"},
    "community_embeds": {"d": 0.11, "s": 0.12, "label": "Community embeds"},
    "partner_distribution": {"d": 0.17, "s": 0.10, "label": "Partner distribution"},
}
CHANNELS = {
    "x": {"d": 0.16, "s": 0.07, "f": 0.06, "label": "X"},
    "linkedin": {"d": 0.14, "s": 0.06, "f": 0.05, "label": "LinkedIn"},
    "seo": {"d": 0.18, "s": 0.14, "f": 0.04, "label": "SEO"},
    "email": {"d": 0.12, "s": 0.12, "f": 0.10, "label": "Email"},
    "communities": {"d": 0.10, "s": 0.14, "f": 0.10, "label": "Communities"},
    "partner_ecosystem": {"d": 0.15, "s": 0.11, "f": 0.08, "label": "Partner ecosystem"},
}
OFFERS = {
    "teardown": {"d": 0.10, "s": 0.07, "label": "Teardown"},
    "comparison_page": {"d": 0.13, "s": 0.08, "label": "Comparison page"},
    "template_pack": {"d": 0.09, "s": 0.06, "label": "Template pack"},
    "benchmark_report": {"d": 0.11, "s": 0.10, "label": "Benchmark report"},
    "roi_calculator": {"d": 0.08, "s": 0.12, "label": "ROI calculator"},
}
ORCH = {
    "n8n_core": {"d": 0.08, "a": 0.18, "f": 0.06, "label": "n8n core"},
    "mautic_campaigns": {"d": 0.07, "a": 0.14, "f": 0.08, "label": "Mautic campaigns"},
    "hybrid_agent_stack": {"d": 0.10, "a": 0.20, "f": 0.12, "label": "Hybrid agent stack"},
}
FEEDBACK = {
    "posthog_twenty": {"s": 0.08, "a": 0.06, "c": 0.15, "label": "PostHog + Twenty"},
    "formbricks_chatwoot": {"s": 0.10, "a": 0.05, "c": 0.12, "label": "Formbricks + Chatwoot"},
    "full_flywheel": {"s": 0.14, "a": 0.10, "c": 0.18, "label": "Full flywheel"},
}
SURFACES = {
    "typebot": {"d": 0.08, "a": 0.10, "f": 0.06, "label": "Typebot"},
    "chatwoot": {"d": 0.06, "a": 0.08, "f": 0.10, "label": "Chatwoot"},
    "microsite": {"d": 0.09, "a": 0.05, "f": 0.04, "label": "Microsite"},
    "calendar_router": {"d": 0.05, "a": 0.07, "f": 0.08, "label": "Calendar router"},
}
MOTION_CHANNEL = {
    "founder_led_content|x": 0.10,
    "founder_led_content|linkedin": 0.08,
    "programmatic_seo|seo": 0.12,
    "signal_based_outbound|email": 0.11,
    "community_embeds|communities": 0.11,
    "partner_distribution|partner_ecosystem": 0.12,
}
MOTION_OFFER = {
    "founder_led_content|teardown": 0.09,
    "programmatic_seo|comparison_page": 0.10,
    "signal_based_outbound|benchmark_report": 0.08,
    "community_embeds|template_pack": 0.07,
    "partner_distribution|roi_calculator": 0.06,
}
ORCH_FEEDBACK = {
    "n8n_core|posthog_twenty": 0.09,
    "mautic_campaigns|formbricks_chatwoot": 0.08,
    "hybrid_agent_stack|full_flywheel": 0.12,
}
CHANNEL_SURFACE = {
    "x|typebot": 0.08,
    "linkedin|calendar_router": 0.07,
    "seo|microsite": 0.10,
    "email|chatwoot": 0.07,
    "communities|chatwoot": 0.08,
    "partner_ecosystem|microsite": 0.06,
}
BASE = {"distribution_system_score": 0.26, "signal_coverage_score": 0.22, "automation_coverage_score": 0.20, "feedback_closure_score": 0.21, "verdict_confidence": 0.48}


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _write(path: str, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mutations(payload: dict[str, Any]) -> dict[str, str]:
    candidate = payload.get("candidate", {})
    raw = candidate.get("mutations", {}) if isinstance(candidate, dict) else {}
    return {str(k): str(v) for k, v in raw.items()}


def _row_mutations(row: dict[str, Any]) -> dict[str, str]:
    muts = row.get("applied_mutations", [])
    if not isinstance(muts, list):
        return {}
    return {str(m.get("name", "")): str(m.get("value", "")) for m in muts if isinstance(m, dict) and m.get("name")}


def _clamp(value: float) -> float:
    return round(max(0.0, min(0.99, value)), 4)


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return cleaned.strip("-")[:64] or "unknown"


def _score(m: dict[str, str]) -> dict[str, Any]:
    if not m:
        return {
            **BASE,
            "label": "Global baseline",
            "verdict": "baseline",
            "promotion_status": "advisory",
            "evidence_lane": "exploratory_frontier",
            "comparison_class": "heuristic_frontier",
            "recommended_next_step": "probe_one_coherent_motion",
            "claim": "Disconnected startup marketing is not a distribution system.",
            "mechanism": "No motion, no capture, and no feedback loop means no compounding.",
            "boundary": "Baseline only. Do not promote.",
            "lesson": "Pick one motion-channel-offer system and close the loop.",
            "next_probe": "Start with one channel tied to one offer and one conversion surface.",
            "bottleneck": "system_gap",
        }

    motion = MOTIONS.get(m.get("motion_id", ""), {})
    channel = CHANNELS.get(m.get("primary_channel", ""), {})
    offer = OFFERS.get(m.get("offer_type", ""), {})
    orch = ORCH.get(m.get("orchestration_layer", ""), {})
    feedback = FEEDBACK.get(m.get("feedback_loop", ""), {})
    surface = SURFACES.get(m.get("conversion_surface", ""), {})

    mc = MOTION_CHANNEL.get(f"{m.get('motion_id','')}|{m.get('primary_channel','')}", -0.02)
    mo = MOTION_OFFER.get(f"{m.get('motion_id','')}|{m.get('offer_type','')}", -0.01)
    of = ORCH_FEEDBACK.get(f"{m.get('orchestration_layer','')}|{m.get('feedback_loop','')}", -0.01)
    cs = CHANNEL_SURFACE.get(f"{m.get('primary_channel','')}|{m.get('conversion_surface','')}", -0.01)

    signal = _clamp(BASE["signal_coverage_score"] + motion.get("s", 0.0) + channel.get("s", 0.0) + offer.get("s", 0.0) + feedback.get("s", 0.0) + mc * 0.45 + mo * 0.35)
    automation = _clamp(BASE["automation_coverage_score"] + orch.get("a", 0.0) + feedback.get("a", 0.0) + surface.get("a", 0.0) + of * 0.45 + cs * 0.25)
    closure = _clamp(BASE["feedback_closure_score"] + feedback.get("c", 0.0) + orch.get("f", 0.0) + channel.get("f", 0.0) + surface.get("f", 0.0) + of * 0.40 + cs * 0.20)
    distribution = _clamp(BASE["distribution_system_score"] + motion.get("d", 0.0) + channel.get("d", 0.0) + offer.get("d", 0.0) + orch.get("d", 0.0) + surface.get("d", 0.0) + signal * 0.14 + automation * 0.14 + closure * 0.16 + mc + mo + of * 0.50 + cs * 0.60)
    confidence = _clamp(BASE["verdict_confidence"] + signal * 0.12 + automation * 0.10 + closure * 0.10 + distribution * 0.12)

    bottleneck = min([("signal_gap", signal), ("automation_gap", automation), ("feedback_gap", closure)], key=lambda item: item[1])[0]
    next_step = {
        "signal_gap": "tighten_research_and_offer_fit",
        "automation_gap": "connect_orchestration_and_capture",
        "feedback_gap": "close_loop_into_crm_and_research",
    }[bottleneck]
    if distribution >= 0.80 and automation >= 0.68 and closure >= 0.66:
        verdict, promotion, lane, klass, next_step = "approve", "validated", "benchmark_grounded", "benchmark_grounded", "run_realworld_pilot"
    elif distribution >= 0.64 and signal >= 0.55:
        verdict, promotion, lane, klass = "defer", "candidate", "benchmark_grounded", "heuristic_frontier"
    else:
        verdict, promotion, lane, klass = "reject", "advisory", "exploratory_frontier", "heuristic_frontier"

    label = " | ".join(
        part
        for part in [
            motion.get("label", ""),
            channel.get("label", ""),
            offer.get("label", ""),
            orch.get("label", ""),
            feedback.get("label", ""),
            surface.get("label", ""),
        ]
        if part
    )
    lesson = {
        "signal_gap": "The message and buyer intent are weaker than the stack.",
        "automation_gap": "The motion has promise but routing is too manual.",
        "feedback_gap": "The system cannot learn fast enough from CRM and conversations.",
    }[bottleneck]
    probe = {
        "signal_gap": "Sharpen one offer before widening channels.",
        "automation_gap": "Automate research-to-publish-to-capture routing.",
        "feedback_gap": "Join analytics, CRM, inbox, and survey traces.",
    }[bottleneck]
    return {
        "distribution_system_score": distribution,
        "signal_coverage_score": signal,
        "automation_coverage_score": automation,
        "feedback_closure_score": closure,
        "verdict_confidence": confidence,
        "verdict": verdict,
        "promotion_status": promotion,
        "evidence_lane": lane,
        "comparison_class": klass,
        "recommended_next_step": next_step,
        "claim": f"{motion.get('label', 'System')} on {channel.get('label', 'channel')} is only strong when it is tied to {offer.get('label', 'an offer')} and a closed feedback loop.",
        "mechanism": "The benchmark rewards systems that connect message, distribution, capture, CRM, and analytics.",
        "boundary": "Synthetic fit is not proof of live CAC or pipeline quality.",
        "lesson": lesson,
        "next_probe": probe,
        "label": label or "Unnamed system",
        "bottleneck": bottleneck,
    }


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    result = _score(_mutations(payload))
    stdout = "\n".join([
        "distribution_system_score: " + str(result["distribution_system_score"]),
        "signal_coverage_score: " + str(result["signal_coverage_score"]),
        "automation_coverage_score: " + str(result["automation_coverage_score"]),
        "feedback_closure_score: " + str(result["feedback_closure_score"]),
        "verdict_confidence: " + str(result["verdict_confidence"]),
    ])
    return {"returncode": 0, "stdout": stdout, "stderr": "", "metrics": {k: result[k] for k in BASE}, "result": result}


def suggest(payload: dict[str, Any]) -> dict[str, Any]:
    limit = max(1, int(payload.get("limit", 4) or 4))
    rows = payload.get("ledger_rows", [])
    rows = rows if isinstance(rows, list) else []
    tested = {
        (
            muts.get("motion_id", ""),
            muts.get("primary_channel", ""),
            muts.get("offer_type", ""),
            muts.get("orchestration_layer", ""),
            muts.get("feedback_loop", ""),
            muts.get("conversion_surface", ""),
        )
        for muts in (_row_mutations(row) for row in rows)
    }
    existing = {
        (
            str(m.get("motion_id", "")),
            str(m.get("primary_channel", "")),
            str(m.get("offer_type", "")),
            str(m.get("orchestration_layer", "")),
            str(m.get("feedback_loop", "")),
            str(m.get("conversion_surface", "")),
        )
        for item in payload.get("candidate_trials", [])
        if isinstance(item, dict)
        for m in [item.get("mutations", {})]
        if isinstance(m, dict)
    }
    seeds = [
        {"motion_id": "founder_led_content", "primary_channel": "x", "offer_type": "teardown", "orchestration_layer": "n8n_core", "feedback_loop": "posthog_twenty", "conversion_surface": "typebot"},
        {"motion_id": "programmatic_seo", "primary_channel": "seo", "offer_type": "comparison_page", "orchestration_layer": "hybrid_agent_stack", "feedback_loop": "full_flywheel", "conversion_surface": "microsite"},
        {"motion_id": "signal_based_outbound", "primary_channel": "email", "offer_type": "benchmark_report", "orchestration_layer": "mautic_campaigns", "feedback_loop": "formbricks_chatwoot", "conversion_surface": "chatwoot"},
        {"motion_id": "community_embeds", "primary_channel": "communities", "offer_type": "template_pack", "orchestration_layer": "n8n_core", "feedback_loop": "formbricks_chatwoot", "conversion_surface": "chatwoot"},
    ]
    suggestions = []
    reasons = []
    for seed in seeds:
        sig = tuple(seed[key] for key in ["motion_id", "primary_channel", "offer_type", "orchestration_layer", "feedback_loop", "conversion_surface"])
        if sig in tested or sig in existing:
            continue
        suggestions.append({
            "candidate_id": "-".join(sig[:3]),
            "candidate_summary": f"Probe {seed['motion_id']} on {seed['primary_channel']} with {seed['offer_type']}.",
            "hypothesis": "A coherent motion-channel-offer system should outperform fragmented startup marketing.",
            "mutations": seed,
        })
        reasons.append(f"Untested high-fit system: {seed['motion_id']} + {seed['primary_channel']} + {seed['offer_type']}.")
        if len(suggestions) >= limit:
            break
    baseline_metric = None
    for row in rows:
        if not row.get("applied_mutations") and isinstance(row.get("metric_value"), (int, float)):
            baseline_metric = float(row["metric_value"])
            break
    return {"baseline_metric": baseline_metric, "reasons": reasons[:limit], "suggestions": suggestions[:limit]}


def packets(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("ledger_rows", [])
    rows = rows if isinstance(rows, list) else []
    ordered = [row for row in rows if isinstance(row.get("metric_value"), (int, float))]
    ordered.sort(key=lambda row: float(row.get("metric_value", 0.0) or 0.0), reverse=True)
    docs = []
    for row in ordered[:3]:
        result = _score(_row_mutations(row))
        slug = _slug(result["label"])
        docs.append({
            "kind": "benchmark_evidence",
            "memory_tier": "benchmark_evidence",
            "slug": f"agentic-marketing-evidence-{slug}",
            "title": f"Agentic Marketing Evidence: {result['label']}",
            "content": "\n".join([
                f"# Agentic Marketing Evidence: {result['label']}",
                "",
                f"- distribution_system_score: {result['distribution_system_score']}",
                f"- signal_coverage_score: {result['signal_coverage_score']}",
                f"- automation_coverage_score: {result['automation_coverage_score']}",
                f"- feedback_closure_score: {result['feedback_closure_score']}",
                f"- verdict: {result['verdict']}",
                "",
                "## Lesson",
                "",
                result["lesson"],
            ]),
        })
        if result["verdict"] == "approve":
            docs.append({
                "kind": "grounded_doctrine",
                "memory_tier": "grounded_doctrine",
                "slug": f"agentic-marketing-doctrine-{slug}",
                "title": f"Agentic Marketing Doctrine: {result['label']}",
                "content": result["claim"],
            })
    if ordered:
        weak = _score(_row_mutations(ordered[-1]))
        docs.append({
            "kind": "grounded_boundary",
            "memory_tier": "grounded_boundary",
            "slug": f"agentic-marketing-boundary-{_slug(weak['label'])}",
            "title": f"Agentic Marketing Boundary: {weak['label']}",
            "content": weak["boundary"],
        })
    if not any(doc["kind"] == "grounded_doctrine" for doc in docs):
        docs.append({
            "kind": "exploratory_frontier",
            "memory_tier": "exploratory_frontier",
            "slug": "agentic-marketing-frontier",
            "title": "Agentic Marketing Frontier",
            "content": "Next probes: founder-led X teardown, SEO comparison pages, signal-based outbound benchmark reports.",
        })
    return {"documents": docs}


def watchtower(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary", {})
    rows = payload.get("ledger_rows", [])
    rows = rows if isinstance(rows, list) else []
    run_count = int(summary.get("run_count", 0) or 0) if isinstance(summary, dict) else 0
    ordered = [row for row in rows if isinstance(row.get("metric_value"), (int, float))]
    ordered.sort(key=lambda row: float(row.get("metric_value", 0.0) or 0.0), reverse=True)
    best = _score(_row_mutations(ordered[0])) if ordered else _score({})
    weak = _score(_row_mutations(ordered[-1])) if ordered else _score({})
    pages = [
        {"path": "07-Domains/Agentic Marketing/Home.md", "content": "\n".join(["# Agentic Marketing Domain", "", f"- total runs: `{run_count}`", f"- best label: `{best['label']}`", f"- best distribution_system_score: `{best['distribution_system_score']}`", "", "## Views", "", "- [[07-Domains/Agentic Marketing/Doctrine]]", "- [[07-Domains/Agentic Marketing/Boundaries]]", "- [[07-Domains/Agentic Marketing/Benchmark Evidence]]", "- [[07-Domains/Agentic Marketing/Frontier Probes]]", "- [[07-Domains/Agentic Marketing/Why It Lost]]", "- [[07-Domains/Agentic Marketing/Coverage Map]]", "- [[07-Domains/Agentic Marketing/Real-World Validation]]"])},
        {"path": "07-Domains/Agentic Marketing/Doctrine.md", "content": "Promote only systems that connect motion, channel, offer, orchestration, capture, and feedback closure."},
        {"path": "07-Domains/Agentic Marketing/Boundaries.md", "content": "\n".join(["# Boundaries", "", weak["boundary"], "", f"- current weakest bottleneck: `{weak['bottleneck']}`"])},
        {"path": "07-Domains/Agentic Marketing/Benchmark Evidence.md", "content": "\n".join(["# Benchmark Evidence", "", f"- best distribution_system_score: `{best['distribution_system_score']}`", f"- best signal_coverage_score: `{best['signal_coverage_score']}`", f"- best automation_coverage_score: `{best['automation_coverage_score']}`", f"- best feedback_closure_score: `{best['feedback_closure_score']}`"])},
        {"path": "07-Domains/Agentic Marketing/Frontier Probes.md", "content": "- founder_led_content + x + teardown\n- programmatic_seo + seo + comparison_page\n- signal_based_outbound + email + benchmark_report"},
        {"path": "07-Domains/Agentic Marketing/Why It Lost.md", "content": "- signal_gap: weak offer or weak buyer mapping\n- automation_gap: too much manual routing\n- feedback_gap: analytics, CRM, and conversation traces are not joined"},
        {"path": "07-Domains/Agentic Marketing/Coverage Map.md", "content": "\n".join(["# Coverage Map", "", "## Motions", ""] + [f"- `{k}`" for k in MOTIONS] + ["", "## Channels", ""] + [f"- `{k}`" for k in CHANNELS] + ["", "## Offers", ""] + [f"- `{k}`" for k in OFFERS])},
        {"path": "07-Domains/Agentic Marketing/Real-World Validation.md", "content": "Live pilots require attribution, CRM stage mapping, conversion surfaces, and weekly review of qualified pipeline and feedback latency."},
    ]
    return {"pages": pages}


def main() -> None:
    parser = argparse.ArgumentParser(prog="domain_chip_agentic_marketing")
    parser.add_argument("hook", choices=["evaluate", "suggest", "packets", "watchtower"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = _load(args.input)
    response = evaluate(payload) if args.hook == "evaluate" else suggest(payload) if args.hook == "suggest" else packets(payload) if args.hook == "packets" else watchtower(payload)
    _write(args.output, response)


if __name__ == "__main__":
    main()
