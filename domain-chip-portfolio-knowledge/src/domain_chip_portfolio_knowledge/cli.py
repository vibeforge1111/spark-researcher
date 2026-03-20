"""CLI entry point for domain-chip-portfolio-knowledge."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
    )


def _mutations(payload):
    candidate = payload.get("candidate", {})
    raw = candidate.get("mutations", {}) if isinstance(candidate, dict) else {}
    return {str(k): str(v) for k, v in raw.items()}


try:
    from .evaluate import score
except ImportError:
    from evaluate import score


def evaluate(payload):
    mutations = _mutations(payload)
    metrics = score(mutations)
    lines = [f"{k}: {v}" for k, v in metrics.items() if isinstance(v, (int, float))]
    verdict = metrics.get("verdict", "defer")
    return {
        "returncode": 0,
        "stdout": "\n".join(lines),
        "stderr": "",
        "metrics": {k: v for k, v in metrics.items() if isinstance(v, (int, float))},
        "result": {
            "verdict": verdict,
            "mechanism": metrics.get("mechanism", ""),
            "boundary": metrics.get("boundary", ""),
            "recommended_next_step": metrics.get(
                "recommended_next_step", "hold_for_more_evidence"
            ),
            "evidence_lane": metrics.get("evidence_lane", "exploratory_frontier"),
        },
    }


def suggest(payload):
    return {
        "suggestions": [],
        "baseline_metric": None,
        "reasons": [
            "No suggestions yet -- chip needs research data"
        ],
    }


def packets(payload):
    return {"documents": []}


def watchtower(payload):
    return {"pages": []}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "hook", choices=["evaluate", "suggest", "packets", "watchtower"]
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = _load(args.input)
    dispatch = {
        "evaluate": evaluate,
        "suggest": suggest,
        "packets": packets,
        "watchtower": watchtower,
    }
    result = dispatch[args.hook](payload)
    _write(args.output, result)


if __name__ == "__main__":
    main()
