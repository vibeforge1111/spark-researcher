from __future__ import annotations

from spark_researcher.advisory import (
    _compress_claim,
    _epistemic_packet,
    _guidance_from_packets,
    _packet_stability,
    _result_count,
    _task_type,
)


def test_task_type_classifies_keywords() -> None:
    assert _task_type("Update the belief packet", "research") == "research_packeting"
    assert _task_type("Explore failure modes", "generic") == "generic_research"
    assert _task_type("optimize loop budget", "training") == "training_optimization"
    assert _task_type("Reply to onboarding email", "generic") == "generic_advisory"


def test_compress_claim_trims_marker_and_truncates() -> None:
    assert _compress_claim("   - hello\n  world  ") == "hello world"
    result = _compress_claim("x" * 200, limit=50)
    assert result.endswith("...") and len(result) == 50


def test_guidance_from_packets_dedupes_and_caps() -> None:
    rows = [
        {"claim": "use bounded retries", "boundary": "do not exceed 3 retries"},
        {"claim": "use bounded retries", "boundary": "stay within 5s budget"},
        {"claim": "log structured events"},
        {"claim": "warn on partial output"},
        {"claim": "watch for memory leaks"},
        {"claim": "deflake retries before merge"},
    ]
    guidance, boundaries = _guidance_from_packets(rows)
    assert guidance == [
        "use bounded retries",
        "log structured events",
        "warn on partial output",
        "watch for memory leaks",
    ]
    assert boundaries == ["do not exceed 3 retries", "stay within 5s budget"]


def test_packet_stability_reports_each_status() -> None:
    durable = _packet_stability([
        {"kind": "belief", "memory_status": "durable"},
        {"kind": "belief", "memory_status": "provisional", "contradiction_count": 1},
    ])
    assert durable["status"] == "durable_supported"
    assert durable["contradiction_count"] == 1

    provisional = _packet_stability([{"kind": "belief", "memory_status": "provisional"}])
    assert provisional["status"] == "provisional_only"

    none = _packet_stability([{"kind": "note"}])
    assert none["status"] == "no_belief_packets"
    assert none["belief_packet_count"] == 0


def test_result_count_for_list_dict_and_other_shapes() -> None:
    assert _result_count([1, 2, 3]) == 3
    assert _result_count({"results": ["a", "b"]}) == 2
    assert _result_count({"error": "boom"}) == 0
    assert _result_count("not iterable") == 0


def test_epistemic_packet_marks_under_supported_without_evidence() -> None:
    packet = _epistemic_packet(
        task="What does the system do?",
        packet_rows=[],
        guidance=[],
        boundaries=[],
        intent={"memory_context": {"memory_hits": [], "ruvector_hits": []}},
        packet_stability={"status": "no_belief_packets"},
    )
    assert packet["status"] == "under_supported"
    assert "Ask clarifying questions before answering." in packet["recommended_actions"]
    assert packet["clarifying_questions"]


def test_epistemic_packet_downgrades_to_partial_when_provisional() -> None:
    packet = _epistemic_packet(
        task="task",
        packet_rows=[{"kind": "belief"}],
        guidance=["g"],
        boundaries=["b"],
        intent={"memory_context": {"memory_hits": [1, 2], "ruvector_hits": []}},
        packet_stability={"status": "provisional_only"},
    )
    assert packet["status"] == "partial"
    assert packet["memory_hit_count"] == 2
    assert any("provisional" in action for action in packet["recommended_actions"])
