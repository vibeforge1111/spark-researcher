from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import resolve_runtime_root
from .runner import read_jsonl


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _docs_root(repo_root: Path) -> Path:
    return repo_root / "docs" / "beliefs"


def _self_edit_root(runtime_root: Path) -> Path:
    return runtime_root / "artifacts" / "self-edit"


def _ledger_path(runtime_root: Path) -> Path:
    return runtime_root / "artifacts" / "ledger" / "runs.jsonl"


def _belief_id(prefix: str, source_id: str) -> str:
    safe = source_id.replace("|", "-").replace(":", "-").replace("/", "-").replace("\\", "-")
    return f"{prefix}-{safe}"


def _render_run_belief(run: dict[str, Any]) -> str:
    mutations = run.get("applied_mutations") or []
    mutation_lines = [f"- `{item['name']}` -> `{item['value']}`" for item in mutations] or ["- none"]
    return "\n".join(
        [
            f"# Run Belief {run.get('candidate_id') or run.get('run_id')}",
            "",
            f"- source_run: `{run.get('run_id')}`",
            f"- verdict: `{run.get('verdict')}`",
            f"- metric: `{run.get('metric_name')}` = `{run.get('metric_value')}`",
            f"- baseline: `{run.get('baseline_value')}`",
            "",
            "## Lesson",
            "",
            str(run.get("hypothesis") or run.get("candidate_summary") or "Improved run observed."),
            "",
            "## Mechanism",
            "",
            "This belief comes from a concrete improved run against a fixed evaluator.",
            "",
            "## Mutations",
            "",
            *mutation_lines,
            "",
            "## Boundaries",
            "",
            "- local to the current evaluator and project config",
            "- should be re-tested if the target command or metric changes",
        ]
    )


def _render_self_edit_belief(proposal: dict[str, Any], review: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Self Edit Belief {proposal.get('proposal_id')}",
            "",
            f"- proposal_id: `{proposal.get('proposal_id')}`",
            f"- status: `{proposal.get('status')}`",
            f"- decision: `{review.get('decision')}`",
            "",
            "## Root Lesson",
            "",
            str(review.get("root_lesson") or "n/a"),
            "",
            "## Lineage Failures",
            "",
            *[f"- {item}" for item in review.get("lineage_failures", [])],
            "",
            "## Counterfactual",
            "",
            str(review.get("counterfactual") or "n/a"),
            "",
            "## Rollback Condition",
            "",
            str(review.get("rollback_condition") or "n/a"),
        ]
    )


def build_beliefs(repo_root: Path, runtime_root: Path | None = None) -> dict[str, Any]:
    runtime_root = runtime_root or resolve_runtime_root(repo_root / "spark-researcher.project.json")
    output_root = _docs_root(repo_root)
    rows = read_jsonl(_ledger_path(runtime_root))
    written: list[dict[str, Any]] = []
    for run in rows:
        if run.get("verdict") != "improved":
            continue
        belief_id = _belief_id("run", str(run.get("run_id")))
        path = output_root / f"{belief_id}.md"
        _write_text(path, _render_run_belief(run))
        written.append({"belief_id": belief_id, "path": str(path), "kind": "run"})
    self_edit_root = _self_edit_root(runtime_root)
    if self_edit_root.exists():
        for proposal_path in sorted(self_edit_root.glob("*/proposal.json")):
            review_path = proposal_path.parent / "review.json"
            if not review_path.exists():
                continue
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            review = json.loads(review_path.read_text(encoding="utf-8"))
            if review.get("decision") != "approve":
                continue
            belief_id = _belief_id("self-edit", str(proposal.get("proposal_id")))
            path = output_root / f"{belief_id}.md"
            _write_text(path, _render_self_edit_belief(proposal, review))
            written.append({"belief_id": belief_id, "path": str(path), "kind": "self_edit"})
    index_lines = ["# Beliefs", ""]
    for item in written:
        index_lines.append(f"- [{item['belief_id']}]({Path(item['path']).name})")
    _write_text(output_root / "INDEX.md", "\n".join(index_lines))
    manifest = {"belief_count": len(written), "beliefs": written}
    _write_text(output_root / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    return manifest
