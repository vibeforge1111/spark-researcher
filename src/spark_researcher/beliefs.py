from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import load_config
from .paths import resolve_runtime_root
from .runner import read_jsonl


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except PermissionError:
        pass


def _docs_root(repo_root: Path) -> Path:
    return repo_root / "docs" / "beliefs"


def _self_edit_root(runtime_root: Path) -> Path:
    return runtime_root / "artifacts" / "self-edit"


def _ledger_path(runtime_root: Path) -> Path:
    return runtime_root / "artifacts" / "ledger" / "runs.jsonl"


def _belief_id(prefix: str, source_id: str) -> str:
    safe = source_id.replace("|", "-").replace(":", "-").replace("/", "-").replace("\\", "-")
    return f"{prefix}-{safe}"


def _safe_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-") or "item"


def _signature(run: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(item["name"]), str(item["value"])) for item in run.get("applied_mutations", [])))


def _is_better(candidate: float, current: float | None, goal: str) -> bool:
    if current is None:
        return True
    return candidate > current if goal == "maximize" else candidate < current


def _command_best(rows: list[dict[str, Any]], *, goal: str) -> dict[str, float]:
    best: dict[str, float] = {}
    for row in rows:
        command_name = str(row.get("command_name") or "")
        metric_value = row.get("metric_value")
        if not command_name or not isinstance(metric_value, (int, float)):
            continue
        current = best.get(command_name)
        value = float(metric_value)
        if _is_better(value, current, goal):
            best[command_name] = value
    return best


def _promotable_run_groups(rows: list[dict[str, Any]], *, goal: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, tuple[tuple[str, str], ...]], dict[str, Any]] = {}
    best_by_command = _command_best(rows, goal=goal)
    for row in rows:
        command_name = str(row.get("command_name") or "")
        metric_value = row.get("metric_value")
        signature = _signature(row)
        if not command_name or not signature or not isinstance(metric_value, (int, float)):
            continue
        key = (command_name, signature)
        group = grouped.setdefault(
            key,
            {
                "command_name": command_name,
                "signature": signature,
                "runs": [],
                "improved_runs": 0,
                "regressed_runs": 0,
                "best_metric": None,
                "representative": None,
                "promotion_reason": "",
            },
        )
        group["runs"].append(row)
        if row.get("verdict") == "improved":
            group["improved_runs"] += 1
        if row.get("verdict") == "regressed":
            group["regressed_runs"] += 1
        value = float(metric_value)
        if _is_better(value, group["best_metric"], goal):
            group["best_metric"] = value
            group["representative"] = row
    promoted: list[dict[str, Any]] = []
    for group in grouped.values():
        best_metric = float(group["best_metric"])
        command_best = best_by_command.get(group["command_name"])
        if group["improved_runs"] >= 2:
            group["promotion_reason"] = "replicated improvement"
            promoted.append(group)
            continue
        if group["improved_runs"] >= 1 and group["regressed_runs"] == 0 and command_best is not None and best_metric == command_best:
            group["promotion_reason"] = "current best observed candidate"
            promoted.append(group)
    promoted.sort(key=lambda item: (str(item["command_name"]), str(item["promotion_reason"]), str(item["representative"].get("run_id"))))
    return promoted


def _render_run_belief(group: dict[str, Any]) -> str:
    run = dict(group["representative"])
    mutations = run.get("applied_mutations") or []
    mutation_lines = [f"- `{item['name']}` -> `{item['value']}`" for item in mutations] or ["- none"]
    return "\n".join(
        [
            f"# Run Belief {run.get('candidate_id') or run.get('run_id')}",
            "",
            f"- source_run: `{run.get('run_id')}`",
            f"- command: `{run.get('command_name')}`",
            f"- verdict: `{run.get('verdict')}`",
            f"- metric: `{run.get('metric_name')}` = `{run.get('metric_value')}`",
            f"- baseline: `{run.get('baseline_value')}`",
            f"- improved_runs_for_signature: `{group.get('improved_runs')}`",
            f"- regressed_runs_for_signature: `{group.get('regressed_runs')}`",
            f"- promotion_reason: `{group.get('promotion_reason')}`",
            "",
            "## Lesson",
            "",
            str(run.get("hypothesis") or run.get("candidate_summary") or "Improved run observed."),
            "",
            "## Mechanism",
            "",
            "This belief was promoted only after a keepability gate over repeated or strongest observed performance.",
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
    config = load_config(repo_root / "spark-researcher.project.json")
    output_root = _docs_root(repo_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for path in output_root.glob("*.md"):
        _safe_unlink(path)
    manifest_path = output_root / "manifest.json"
    if manifest_path.exists():
        _safe_unlink(manifest_path)
    rows = read_jsonl(_ledger_path(runtime_root))
    written: list[dict[str, Any]] = []
    promoted_groups = _promotable_run_groups(rows, goal=config.eval_goal)
    skipped_runs = 0
    for group in promoted_groups:
        representative = dict(group["representative"])
        signature_slug = _safe_slug(
            "-".join(f"{name}-{value}" for name, value in group["signature"])
        )
        belief_id = _belief_id("run", f"{representative.get('command_name')}-{signature_slug}")
        path = output_root / f"{belief_id}.md"
        _write_text(path, _render_run_belief(group))
        written.append({"belief_id": belief_id, "path": str(path), "kind": "run"})
    promoted_run_signatures = {
        (str(group["command_name"]), tuple(group["signature"]))
        for group in promoted_groups
    }
    for row in rows:
        if row.get("verdict") != "improved" or not row.get("applied_mutations"):
            continue
        signature = (str(row.get("command_name") or ""), _signature(row))
        if signature not in promoted_run_signatures:
            skipped_runs += 1
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
    manifest = {
        "belief_count": len(written),
        "beliefs": written,
        "skipped_improved_runs": skipped_runs,
        "promotion_policy": [
            "Promote repeated improvements for the same mutation signature.",
            "Allow a single-run promotion only when it is the current best observed candidate with no regressions for that signature.",
        ],
    }
    _write_text(output_root / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    return manifest
