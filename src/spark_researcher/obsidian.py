from __future__ import annotations

import json
import shutil
from pathlib import Path

from .beliefs import build_beliefs
from .memory import sync_memory
from .paths import trainers_root, vault_root
from .runner import ledger_summary


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def copy_docs(repo_root: Path, output_root: Path) -> list[str]:
    written = []
    source = repo_root / "docs"
    output_root.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        return written
    for path in sorted(source.rglob("*.md")):
        target = output_root / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        written.append(str(target))
    return written


def render_home(summary: dict, trainer_rows: list[dict]) -> str:
    return "\n".join(
        [
            "# Spark Researcher Vault",
            "",
            "## Start",
            "",
            "- [[00-Intent/System Intent]]",
            "- [[05-Runtime/Run Ledger]]",
            "- [[05-Runtime/Trainer State]]",
            "- [[05-Runtime/Self Edit Queue]]",
            "- [[06-References/beliefs/INDEX]]",
            "",
            "## Snapshot",
            "",
            f"- total runs: `{summary['run_count']}`",
            f"- tracked metrics: `{len(summary['best_by_metric'])}`",
            f"- trainer entries: `{len(trainer_rows)}`",
            "",
            "## References",
            "",
            "- [[06-References/ARCHITECTURE]]",
            "- [[06-References/BELIEFS]]",
            "- [[06-References/RULES]]",
            "- [[06-References/SELF_EDITING]]",
            "- [[06-References/OBSIDIAN]]",
        ]
    )


def render_intent() -> str:
    return "\n".join(
        [
            "# System Intent",
            "",
            "- Keep the core small enough to read in one sitting.",
            "- Treat the evaluator as fixed and the strategy as mutable.",
            "- Prefer file artifacts over hidden services.",
            "- Keep the owner in the loop for self-edit persistence.",
        ]
    )


def render_run_ledger(summary: dict) -> str:
    lines = ["# Run Ledger", "", f"- total runs: `{summary['run_count']}`", ""]
    for row in summary["recent"]:
        lines.extend(
            [
                f"## {row.get('run_id')}",
                "",
                f"- candidate: `{row.get('candidate_id')}`",
                f"- verdict: `{row.get('verdict')}`",
                f"- metric: `{row.get('metric_value')}`",
                f"- created_at: `{row.get('created_at')}`",
                "",
            ]
        )
    return "\n".join(lines)


def render_trainer_state(rows: list[dict]) -> str:
    lines = ["# Trainer State", ""]
    for row in rows:
        lines.extend(
            [
                f"## {row.get('name', row.get('trainer', 'trainer'))}",
                "",
                f"- last_status: `{row.get('last_status', row.get('status', 'unknown'))}`",
                f"- example_count: `{row.get('example_count', 'n/a')}`",
                f"- compile_count: `{row.get('compile_count', 'n/a')}`",
                f"- last_reason: `{row.get('last_reason', row.get('reason', 'n/a'))}`",
                "",
            ]
        )
    return "\n".join(lines)


def render_self_edit_queue(runtime_root: Path) -> str:
    root = runtime_root / "artifacts" / "self-edit"
    lines = ["# Self Edit Queue", ""]
    if not root.exists():
        lines.append("No proposals yet.")
        return "\n".join(lines)
    for proposal_path in sorted(root.glob("*/proposal.json"), reverse=True):
        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        lines.extend(
            [
                f"## {proposal.get('proposal_id')}",
                "",
                f"- status: `{proposal.get('status')}`",
                f"- changes: `{proposal.get('change_count')}`",
                f"- blocked_changes: `{len(proposal.get('blocked_changes', []))}`",
                f"- prompt: {proposal.get('prompt')}",
                "",
            ]
        )
    return "\n".join(lines)


def build_vault(repo_root: Path, runtime_root: Path) -> dict[str, object]:
    sync_memory(runtime_root)
    belief_manifest = build_beliefs(repo_root, runtime_root)
    output_root = vault_root(runtime_root)
    summary = ledger_summary(runtime_root)
    trainer_rows = []
    trainer_dir = trainers_root(runtime_root)
    if trainer_dir.exists():
        for path in sorted(trainer_dir.glob("*.json")):
            trainer_rows.append(json.loads(path.read_text(encoding="utf-8")))
    copy_docs(repo_root, output_root / "06-References")
    write_text(output_root / "Home.md", render_home(summary, trainer_rows))
    write_text(output_root / "00-Intent" / "System Intent.md", render_intent())
    write_text(output_root / "05-Runtime" / "Run Ledger.md", render_run_ledger(summary))
    write_text(output_root / "05-Runtime" / "Trainer State.md", render_trainer_state(trainer_rows))
    write_text(output_root / "05-Runtime" / "Self Edit Queue.md", render_self_edit_queue(runtime_root))
    return {
        "vault_root": str(output_root),
        "run_count": summary["run_count"],
        "trainer_entries": len(trainer_rows),
        "belief_count": belief_manifest["belief_count"],
    }
