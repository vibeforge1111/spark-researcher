from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .authority import memory_authority_refs, require_memory_write_authority
from .config import load_config
from .paths import beliefs_root, resolve_runtime_root
from .runner import read_jsonl


MAX_BELIEF_FILENAME_STEM = 80


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except PermissionError:
        pass


def _beliefs_root(runtime_root: Path) -> Path:
    return beliefs_root(runtime_root)


def _self_edit_root(runtime_root: Path) -> Path:
    return runtime_root / "artifacts" / "self-edit"


def _ledger_path(runtime_root: Path) -> Path:
    return runtime_root / "artifacts" / "ledger" / "runs.jsonl"


def beliefs_authority_refs(repo_root: Path, runtime_root: Path) -> tuple[str, ...]:
    output_root = _beliefs_root(runtime_root)
    return memory_authority_refs(
        "beliefs",
        output_root,
        output_root / "manifest.json",
        _ledger_path(runtime_root),
        repo_root / "spark-researcher.project.json",
    )


def _belief_id(prefix: str, source_id: str) -> str:
    safe = source_id.replace("|", "-").replace(":", "-").replace("/", "-").replace("\\", "-")
    return f"{prefix}-{safe}"


def _safe_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-") or "item"


def _bounded_filename_stem(value: str, *, limit: int = MAX_BELIEF_FILENAME_STEM) -> str:
    safe = _safe_slug(value)
    if len(safe) <= limit:
        return safe
    digest = hashlib.sha1(safe.encode("utf-8")).hexdigest()[:12]
    head_limit = max(1, limit - len(digest) - 1)
    head = safe[:head_limit].rstrip("-._") or "item"
    return f"{head}-{digest}"


def _signature(run: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(item["name"]), str(item["value"])) for item in run.get("applied_mutations", [])))


def _signature_map(signature: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return {name: value for name, value in signature}


def _group_belief_id(group: dict[str, Any]) -> str:
    representative = dict(group["representative"])
    signature_slug = _safe_slug("-".join(f"{name}-{value}" for name, value in group["signature"]))
    return _belief_id("run", f"{representative.get('command_name')}-{signature_slug}")


def _is_better(candidate: float, current: float | None, goal: str) -> bool:
    if current is None:
        return True
    return candidate > current if goal == "maximize" else candidate < current


def _skip_core_run_belief(row: dict[str, Any]) -> bool:
    chip_result = row.get("chip_result")
    if not isinstance(chip_result, dict):
        return False
    comparison_class = str(chip_result.get("comparison_class") or "").strip()
    benchmark_profile = str(chip_result.get("benchmark_profile") or "").strip()
    baseline_id = str(chip_result.get("baseline_id") or "").strip()
    if comparison_class == "benchmark_grounded":
        return True
    if benchmark_profile and baseline_id:
        return True
    return False


def _command_best(rows: list[dict[str, Any]], *, goal: str) -> dict[str, float]:
    best: dict[str, float] = {}
    for row in rows:
        if _skip_core_run_belief(row):
            continue
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
        if _skip_core_run_belief(row):
            continue
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


def _annotate_belief_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated = [dict(group) for group in groups]
    for group in annotated:
        group["belief_id"] = _group_belief_id(group)
        group["belief_status"] = "durable" if str(group.get("promotion_reason") or "") == "replicated improvement" else "provisional"
        group["contradictions"] = []
    by_command: dict[str, list[dict[str, Any]]] = {}
    for group in annotated:
        by_command.setdefault(str(group["command_name"]), []).append(group)
    for command_groups in by_command.values():
        for index, left in enumerate(command_groups):
            left_map = _signature_map(left["signature"])
            for right in command_groups[index + 1 :]:
                right_map = _signature_map(right["signature"])
                conflicting_fields = [
                    {
                        "name": name,
                        "left": left_map[name],
                        "right": right_map[name],
                    }
                    for name in sorted(set(left_map) & set(right_map))
                    if left_map[name] != right_map[name]
                ]
                if not conflicting_fields:
                    continue
                left["contradictions"].append({"belief_id": right["belief_id"], "fields": conflicting_fields})
                right["contradictions"].append({"belief_id": left["belief_id"], "fields": conflicting_fields})
                left["belief_status"] = "provisional"
                right["belief_status"] = "provisional"
    return annotated


def _render_run_belief(group: dict[str, Any]) -> str:
    run = dict(group["representative"])
    mutations = run.get("applied_mutations") or []
    mutation_lines = [f"- `{item['name']}` -> `{item['value']}`" for item in mutations] or ["- none"]
    contradiction_lines = []
    for item in group.get("contradictions", []):
        if not isinstance(item, dict):
            continue
        field_bits = []
        for field in item.get("fields", []):
            if not isinstance(field, dict):
                continue
            field_bits.append(f"`{field.get('name')}`: `{field.get('left')}` vs `{field.get('right')}`")
        contradiction_lines.append(f"- conflicts with `{item.get('belief_id')}` on {', '.join(field_bits)}")
    return "\n".join(
        [
            f"# Run Belief {run.get('candidate_id') or run.get('run_id')}",
            "",
            f"- belief_id: `{group.get('belief_id')}`",
            f"- belief_status: `{group.get('belief_status')}`",
            f"- source_run: `{run.get('run_id')}`",
            f"- command: `{run.get('command_name')}`",
            f"- verdict: `{run.get('verdict')}`",
            f"- metric: `{run.get('metric_name')}` = `{run.get('metric_value')}`",
            f"- baseline: `{run.get('baseline_value')}`",
            f"- improved_runs_for_signature: `{group.get('improved_runs')}`",
            f"- regressed_runs_for_signature: `{group.get('regressed_runs')}`",
            f"- promotion_reason: `{group.get('promotion_reason')}`",
            f"- contradiction_count: `{len(group.get('contradictions', []))}`",
            "",
            "## Lesson",
            "",
            str(run.get("hypothesis") or run.get("candidate_summary") or "Improved run observed."),
            "",
            "## Mechanism",
            "",
            "This belief was promoted only after a keepability gate over repeated or strongest observed performance.",
            "Durable means the lesson has repeated support and no active contradiction. Provisional means it is still the current best local lesson but competing evidence exists or replication is still thin.",
            "",
            "## Mutations",
            "",
            *mutation_lines,
            "",
            "## Contradictions",
            "",
            *(contradiction_lines or ["- none"]),
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


def build_beliefs(
    repo_root: Path,
    runtime_root: Path | None = None,
    *,
    governor_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_root = runtime_root or resolve_runtime_root(repo_root / "spark-researcher.project.json")
    require_memory_write_authority(governor_decision, binding_refs=beliefs_authority_refs(repo_root, runtime_root))
    config = load_config(repo_root / "spark-researcher.project.json")
    output_root = _beliefs_root(runtime_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for path in output_root.glob("*.md"):
        _safe_unlink(path)
    manifest_path = output_root / "manifest.json"
    if manifest_path.exists():
        _safe_unlink(manifest_path)
    rows = read_jsonl(_ledger_path(runtime_root))
    written: list[dict[str, Any]] = []
    promoted_groups = _annotate_belief_groups(_promotable_run_groups(rows, goal=config.eval_goal))
    skipped_runs = 0
    for group in promoted_groups:
        belief_id = str(group["belief_id"])
        path = output_root / f"{_bounded_filename_stem(belief_id)}.md"
        _write_text(path, _render_run_belief(group))
        written.append({"belief_id": belief_id, "path": str(path), "kind": "run", "status": group.get("belief_status", "provisional")})
    promoted_run_signatures = {
        (str(group["command_name"]), tuple(group["signature"]))
        for group in promoted_groups
    }
    for row in rows:
        if _skip_core_run_belief(row):
            continue
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
            path = output_root / f"{_bounded_filename_stem(belief_id)}.md"
            _write_text(path, _render_self_edit_belief(proposal, review))
            written.append({"belief_id": belief_id, "path": str(path), "kind": "self_edit", "status": "durable"})
    index_lines = ["# Beliefs", ""]
    for item in written:
        index_lines.append(f"- [{item['belief_id']}]({Path(item['path']).name}) - `{item.get('status', 'n/a')}`")
    _write_text(output_root / "INDEX.md", "\n".join(index_lines))
    contradiction_lines = ["# Belief Contradictions", ""]
    run_groups = [group for group in promoted_groups if group.get("contradictions")]
    if not run_groups:
        contradiction_lines.append("No active belief contradictions.")
    else:
        for group in run_groups:
            contradiction_lines.extend(
                [
                    f"## {group.get('belief_id')}",
                    "",
                    *[
                        f"- conflicts with `{item.get('belief_id')}` on "
                        + ", ".join(
                            f"`{field.get('name')}`: `{field.get('left')}` vs `{field.get('right')}`"
                            for field in item.get("fields", [])
                            if isinstance(field, dict)
                        )
                        for item in group.get("contradictions", [])
                        if isinstance(item, dict)
                    ],
                    "",
                ]
            )
    _write_text(output_root / "CONTRADICTIONS.md", "\n".join(contradiction_lines))
    durable_count = sum(1 for item in written if item.get("status") == "durable")
    provisional_count = sum(1 for item in written if item.get("status") == "provisional")
    manifest = {
        "belief_count": len(written),
        "beliefs": written,
        "skipped_improved_runs": skipped_runs,
        "durable_belief_count": durable_count,
        "provisional_belief_count": provisional_count,
        "contradiction_count": sum(len(group.get("contradictions", [])) for group in promoted_groups),
        "promotion_policy": [
            "Promote repeated improvements for the same mutation signature as durable only when no active contradiction remains.",
            "Allow a single-run promotion only when it is the current best observed candidate with no regressions for that signature, and keep it provisional by default.",
            "If two promoted lessons for the same command disagree on a shared mutation value, mark both as provisional until more evidence resolves the contradiction.",
        ],
    }
    _write_text(output_root / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    return manifest
