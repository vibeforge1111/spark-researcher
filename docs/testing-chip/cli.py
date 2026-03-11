from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _write(path: str, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mods(repo_root: Path) -> dict[str, object]:
    sys.path.insert(0, str(repo_root / "src"))
    from spark_researcher.adapters.base import adapter_request
    from spark_researcher.advisory import _epistemic_packet
    from spark_researcher.obsidian import render_research_signals
    from spark_researcher.packets import _PREFERRED_KINDS, _belief_status_bonus, _packet_from_path
    from spark_researcher.research import _clean_result_url, _domain_from_url
    from spark_researcher.tracing import start_trace, trace_status

    return locals()


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": ok, "detail": detail}


def evaluate(payload: dict) -> dict:
    repo_root = Path(str(payload.get("repo_root") or ".")).resolve()
    mods = _mods(repo_root)
    suite = str(payload.get("candidate", {}).get("mutations", {}).get("suite") or "full")
    checks = []
    if suite in {"memory", "full", "smoke"}:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            durable = root / "belief-durable.md"
            provisional = root / "belief-provisional.md"
            durable.write_text("# Durable\n\n- belief_status: `durable`\n- contradiction_count: `0`\n\n## Lesson\nlearning rate improves stability\n", encoding="utf-8")
            provisional.write_text("# Provisional\n\n- belief_status: `provisional`\n- contradiction_count: `1`\n\n## Lesson\nlearning rate improves stability\n", encoding="utf-8")
            a = mods["_packet_from_path"](durable, "generic")
            b = mods["_packet_from_path"](provisional, "generic")
            score_a = 1 + mods["_PREFERRED_KINDS"]["belief"] + mods["_belief_status_bonus"](a) - min(a.contradiction_count, 2)
            score_b = 1 + mods["_PREFERRED_KINDS"]["belief"] + mods["_belief_status_bonus"](b) - min(b.contradiction_count, 2)
            checks.append(_check("durable_belief_priority", score_a > score_b, f"durable={score_a} provisional={score_b}"))
        epistemic = mods["_epistemic_packet"](
            task="test",
            packet_rows=[{"packet_id": "belief-a"}],
            guidance=["Keep claims narrow."],
            boundaries=["No broad claims."],
            intent={"memory_context": {"memory_hits": [{"x": 1}], "ruvector_hits": []}},
            packet_stability={"status": "provisional_only", "durable_belief_count": 0, "provisional_belief_count": 2, "contradiction_count": 1},
        )
        checks.append(_check("advisory_downgrades_provisional_only", epistemic["status"] == "partial", epistemic["status"]))
        prompt = mods["adapter_request"](
            "generic",
            "Answer the task",
            {"epistemic_status": epistemic, "guidance": ["Keep claims narrow."], "boundaries": ["No broad claims."], "failure_priorities": {}},
        )["user_prompt"]
        checks.append(_check("adapter_brief_exposes_packet_stability", "Packet Stability: provisional_only" in prompt, "packet stability in prompt"))
    if suite in {"tracing", "full", "smoke"}:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace = mods["start_trace"](root, kind="advisory_build", name="testing")
            trace.event("packet_selection", attributes={"selected_packet_ids": ["belief-a"], "packet_stability": "durable_supported", "durable_belief_count": 1, "provisional_belief_count": 0, "contradiction_count": 0})
            trace.finish()
            signals = mods["trace_status"](root)["research_signals"]
            rendered = mods["render_research_signals"](signals)
            checks.append(_check("obsidian_renders_packet_selection", "selected_packet_ids: `belief-a`" in rendered, "packet ids in watchtower"))
    if suite in {"research", "full", "smoke"}:
        url = mods["_clean_result_url"]("https://duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.python.org%2F3%2Flibrary%2Fjson.html")
        checks.append(_check("research_url_cleanup", url == "https://docs.python.org/3/library/json.html", url))
        checks.append(_check("research_domain_extraction", mods["_domain_from_url"](url) == "docs.python.org", mods["_domain_from_url"](url)))
    passed = sum(1 for item in checks if item["ok"])
    total = max(len(checks), 1)
    score = round(passed / total, 2)
    stdout = "\n".join([f"reliability_score: {score}", f"verdict_confidence: {score}", f"passed_checks: {passed}/{total}"])
    return {
        "returncode": 0,
        "stdout": stdout,
        "stderr": "",
        "metrics": {"reliability_score": score, "verdict_confidence": score},
        "result": {"claim": "Core reliability probes should pass deterministically.", "suite": suite, "passed": passed, "total": total, "checks": checks},
    }


def suggest(payload: dict) -> dict:
    tested = {str(row.get("candidate_id") or "") for row in payload.get("ledger_rows", []) if isinstance(row, dict)}
    suites = [("smoke-suite", "smoke"), ("memory-suite", "memory"), ("tracing-suite", "tracing"), ("research-suite", "research"), ("full-suite", "full")]
    suggestions = [{"candidate_id": cid, "candidate_summary": f"Run the {suite} reliability suite.", "hypothesis": "Reliability probes should stay deterministic.", "mutations": {"suite": suite}} for cid, suite in suites if cid not in tested]
    return {"baseline_metric": None, "reasons": ["Cover untested reliability suites first."], "suggestions": suggestions[:3]}


def packets(payload: dict) -> dict:
    return {"documents": [{"kind": "testing_belief", "slug": "core-reliability", "title": "Core Reliability Rule", "content": "# Core Reliability Rule\n\nPrefer stop-ship signals over polished output when advisory honesty, verifier caution, research provenance, or watchtower truthfulness fail."}]}


def watchtower(payload: dict) -> dict:
    rows = [row for row in payload.get("ledger_rows", []) if isinstance(row, dict)]
    best = max((float(row.get("metric_value")) for row in rows if isinstance(row.get("metric_value"), (int, float))), default=0.0)
    content = "# Testing Domain\n\n" + "\n".join([f"- run_count: `{len(rows)}`", f"- best_reliability_score: `{best}`", "- goal: keep the deterministic probes green before trusting core changes."])
    return {"pages": [{"path": "07-Domains/Testing/Home.md", "content": content}]}


def main() -> None:
    parser = argparse.ArgumentParser(prog="spark-testing-chip")
    parser.add_argument("hook", choices=["evaluate", "suggest", "packets", "watchtower"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = _load(args.input)
    response = {"evaluate": evaluate, "suggest": suggest, "packets": packets, "watchtower": watchtower}[args.hook](payload)
    _write(args.output, response)


if __name__ == "__main__":
    main()
