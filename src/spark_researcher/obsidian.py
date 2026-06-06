from __future__ import annotations

import json
import shutil
from pathlib import Path

from .config import ProjectConfig
from .beliefs import build_beliefs
from .chips import chip_has_hook, invoke_chip_hook
from .memory import load_episode_memory, load_working_memory, sync_memory
from .packets import packet_status
from .paths import beliefs_root, trainers_root, vault_root
from .runner import ledger_summary, read_jsonl
from .tracing import trace_status
from .trial_queue import pending_queue_count


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


def copy_runtime_beliefs(runtime_root: Path, output_root: Path) -> list[str]:
    written = []
    source = beliefs_root(runtime_root)
    output_root.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        return written
    for path in output_root.glob("*"):
        if path.is_file():
            path.unlink()
    for path in sorted(source.glob("*")):
        if not path.is_file():
            continue
        target = output_root / path.name
        shutil.copyfile(path, target)
        written.append(str(target))
    return written


def render_home(
    summary: dict,
    trainer_rows: list[dict],
    memory_manifest: dict,
    belief_manifest: dict,
    packet_manifest: dict,
    domain_pages: list[str],
    research_signals: dict,
    frontier_queue_count: int,
) -> str:
    domain_lines = [f"- [[{page}]]" for page in domain_pages]
    return "\n".join(
        [
            "# Spark Researcher Vault",
            "",
            "## Start",
            "",
            "- [[00-Intent/System Intent]]",
            "- [[05-Runtime/Run Ledger]]",
            "- [[05-Runtime/Trainer State]]",
            "- [[05-Runtime/Memory Index]]",
            "- [[05-Runtime/Packet Status]]",
            "- [[05-Runtime/Working Memory]]",
            "- [[05-Runtime/Episode Memory]]",
            "- [[05-Runtime/Outcome State]]",
            "- [[05-Runtime/Research Signals]]",
            "- [[05-Runtime/Self Edit Queue]]",
            "- [[06-References/beliefs/INDEX]]",
            *domain_lines,
            "",
            "## Snapshot",
            "",
            f"- total runs: `{summary['run_count']}`",
            f"- tracked metrics: `{len(summary['best_by_metric'])}`",
            f"- trainer entries: `{len(trainer_rows)}`",
            f"- memory docs: `{memory_manifest.get('document_count', 0)}`",
            f"- packet docs: `{packet_manifest.get('packet_count', 0)}`",
            f"- episode rows: `{memory_manifest.get('episode_count', 0)}`",
            f"- durable beliefs: `{belief_manifest.get('durable_belief_count', 0)}`",
            f"- provisional beliefs: `{belief_manifest.get('provisional_belief_count', 0)}`",
            f"- active belief contradictions: `{belief_manifest.get('contradiction_count', 0)}`",
            f"- research retries: `{research_signals.get('research_retry_count', 0)}`",
            f"- citation mismatches: `{research_signals.get('citation_mismatch_count', 0)}`",
            f"- queued frontier candidates: `{frontier_queue_count}`",
            f"- domain pages: `{len(domain_pages)}`",
            "",
            "## References",
            "",
            "- [[06-References/ARCHITECTURE]]",
            "- [[06-References/BELIEFS]]",
            "- [[06-References/MEMORY]]",
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


def render_memory_index(memory_manifest: dict) -> str:
    kinds = memory_manifest.get("kinds", {})
    lines = [
        "# Memory Index",
        "",
        f"- backend: `{memory_manifest.get('backend', 'local')}`",
        f"- document_count: `{memory_manifest.get('document_count', 0)}`",
        f"- documents_root: `{memory_manifest.get('documents_root')}`",
        "",
        "## Kinds",
        "",
    ]
    lines.extend(f"- {kind}: `{count}`" for kind, count in sorted(kinds.items()))
    return "\n".join(lines)


def render_packet_status(packet_manifest: dict) -> str:
    kinds = packet_manifest.get("kinds", {})
    lines = [
        "# Packet Status",
        "",
        f"- packet_count: `{packet_manifest.get('packet_count', 0)}`",
        f"- packets_root: `{packet_manifest.get('packets_root', 'n/a')}`",
        "",
        "## Packet Kinds",
        "",
    ]
    lines.extend(f"- {kind}: `{count}`" for kind, count in sorted(kinds.items()))
    lines.extend(
        [
            "",
            "## Evidence Contract",
            "",
            "- `belief` packets are promoted local lessons and can be `durable` or `provisional`.",
            "- `research_outcome` packets are bounded evidence-only surfaces derived from the `research` command.",
            "- `research_outcome` packets are not promoted doctrine or belief and should rank below those packet types when both match.",
            "",
            "## Research Outcome Fields",
            "",
            "- `kind`: `research_outcome`",
            "- `claim`: bounded statement of the current research-suite result",
            "- `mechanism`: explicit note that the row comes from the research ledger as evidence-only support",
            "- `boundary`: explicit limit that the row is a single recorded research outcome and not doctrine",
        ]
    )
    return "\n".join(lines)


def render_working_memory(payload: dict) -> str:
    lines = ["# Working Memory", ""]
    if not payload:
        lines.append("No active working memory yet.")
        return "\n".join(lines)
    lines.extend(
        [
            f"- updated_at: `{payload.get('updated_at', 'n/a')}`",
            f"- kind: `{payload.get('kind', 'n/a')}`",
            f"- status: `{payload.get('status', 'n/a')}`",
            "",
            "## Focus",
            "",
            str(payload.get("focus") or "n/a"),
            "",
        ]
    )
    for heading, key in (("Notes", "notes"), ("Open Questions", "questions")):
        items = [str(item) for item in payload.get(key, []) if str(item).strip()]
        if not items:
            continue
        lines.extend([f"## {heading}", "", *[f"- {item}" for item in items], ""])
    return "\n".join(lines)


def render_episode_memory(rows: list[dict]) -> str:
    lines = ["# Episode Memory", ""]
    if not rows:
        lines.append("No episodes yet.")
        return "\n".join(lines)
    for row in rows:
        lines.extend(
            [
                f"## {row.get('title', row.get('kind', 'episode'))}",
                "",
                f"- created_at: `{row.get('created_at', 'n/a')}`",
                f"- kind: `{row.get('kind', 'n/a')}`",
                f"- status: `{row.get('status', 'n/a')}`",
                "",
                str(row.get("summary") or "n/a"),
                "",
            ]
        )
    return "\n".join(lines)


def render_outcome_state(memory_manifest: dict) -> str:
    lines = ["# Outcome State", ""]
    outcomes = memory_manifest.get("outcomes", [])
    if not outcomes:
        lines.append("No outcomes yet.")
        return "\n".join(lines)
    for item in outcomes:
        lines.extend(
            [
                f"## {item.get('title')}",
                "",
                f"- runs: `{item.get('run_count')}`",
                f"- improved_runs: `{item.get('improved_runs')}`",
                f"- latest_verdict: `{item.get('latest_verdict')}`",
                f"- best_metric: `{item.get('best_metric')}`",
                f"- latest_metric: `{item.get('latest_metric')}`",
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
        try:
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(proposal, dict):
            continue
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


def render_research_signals(packet: dict) -> str:
    lines = [
        "# Research Signals",
        "",
        f"- research_retries: `{packet.get('research_retry_count', 0)}`",
        f"- research_escalations: `{packet.get('research_escalation_count', 0)}`",
        f"- citation_checks: `{packet.get('citation_check_count', 0)}`",
        f"- citation_mismatches: `{packet.get('citation_mismatch_count', 0)}`",
        f"- verifier_selections: `{packet.get('verifier_selection_count', 0)}`",
        f"- packet_selections: `{packet.get('packet_selection_count', 0)}`",
        "",
    ]
    recent = packet.get("recent", [])
    if not recent:
        lines.append("No research or citation signals yet.")
        return "\n".join(lines)
    for item in recent:
        lines.extend(
            [
                f"## {item.get('signal', 'signal')}",
                "",
                f"- created_at: `{item.get('created_at', 'n/a')}`",
                f"- trace_id: `{item.get('trace_id', 'n/a')}`",
                f"- research_query: `{item.get('research_query', 'n/a')}`" if item.get("research_query") else "",
                f"- selected: `{item.get('selected', 'n/a')}`" if item.get("selected") else "",
                f"- decision: `{item.get('decision', 'n/a')}`" if item.get("decision") else "",
                f"- selected_packet_ids: `{', '.join(item.get('selected_packet_ids', [])) or 'none'}`" if "selected_packet_ids" in item else "",
                f"- packet_stability: `{item.get('packet_stability', 'n/a')}`" if item.get("packet_stability") else "",
                f"- belief_mix: durable={item.get('durable_belief_count', 0)}, provisional={item.get('provisional_belief_count', 0)}, contradictions={item.get('contradiction_count', 0)}" if "durable_belief_count" in item else "",
                f"- issue_count: `{item.get('issue_count', 'n/a')}`" if "issue_count" in item else "",
                f"- top_issue: {item.get('top_issue')}" if item.get("top_issue") else "",
                f"- best_next_question: {item.get('best_next_question')}" if item.get("best_next_question") else "",
                f"- implicated_failure_surface: `{item.get('implicated_failure_surface', 'n/a')}`" if item.get("implicated_failure_surface") else "",
                f"- used_note_ids: `{', '.join(item.get('used_note_ids', [])) or 'none'}`" if "used_note_ids" in item else "",
                f"- relevant_note_ids: `{', '.join(item.get('relevant_note_ids', [])) or 'none'}`" if "relevant_note_ids" in item else "",
                f"- mismatch: `{item.get('mismatch')}`" if "mismatch" in item else "",
                "",
            ]
        )
        sources = item.get("sources", [])
        if isinstance(sources, list) and sources:
            lines.extend(["### Sources", ""])
            for source in sources:
                if not isinstance(source, dict):
                    continue
                note_id = str(source.get("note_id") or "note").strip()
                title = str(source.get("title") or "untitled").strip()
                domain = str(source.get("domain") or "").strip()
                url = str(source.get("url") or "").strip()
                source_line = f"- `{note_id}`: {title}"
                if domain:
                    source_line += f" [{domain}]"
                lines.append(source_line)
                if url:
                    lines.append(f"  - url: `{url}`")
            lines.append("")
    return "\n".join(line for line in lines if line != "")


def build_vault(repo_root: Path, runtime_root: Path, config: ProjectConfig, *, config_path: Path | None = None) -> dict[str, object]:
    effective_config_path = config_path or (repo_root / "spark-researcher.project.json")
    rows = read_jsonl(runtime_root / "artifacts" / "ledger" / "runs.jsonl")
    memory_manifest = sync_memory(repo_root, runtime_root, goal=config.eval_goal, config_path=effective_config_path)
    belief_manifest = build_beliefs(repo_root, runtime_root)
    packet_manifest = packet_status(effective_config_path)
    output_root = vault_root(runtime_root)
    summary = ledger_summary(runtime_root, goal=config.eval_goal)
    traces = trace_status(runtime_root)
    frontier_queue_count = pending_queue_count(effective_config_path, rows)
    working_memory = load_working_memory(runtime_root)
    episode_rows = load_episode_memory(runtime_root)
    trainer_rows = []
    trainer_dir = trainers_root(runtime_root)
    if trainer_dir.exists():
        for path in sorted(trainer_dir.glob("*.json")):
            try:
                trainer_row = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(trainer_row, dict):
                trainer_rows.append(trainer_row)
    domain_pages: list[str] = []
    if chip_has_hook(effective_config_path, "watchtower", config):
        packet = invoke_chip_hook(
            effective_config_path,
            "watchtower",
            {
                "project_name": config.project_name,
                "summary": summary,
                "ledger_rows": rows,
                "memory_manifest": memory_manifest,
                "belief_manifest": belief_manifest,
                "vault_root": str(output_root),
                "runtime_root": str(runtime_root),
                "config_path": str(effective_config_path),
            },
            config=config,
        )
        for item in packet.get("pages", []):
            page_path = str(item.get("path") or "").strip().replace("\\", "/")
            if not page_path:
                continue
            write_text(output_root / page_path, str(item.get("content") or ""))
            domain_pages.append(page_path.removesuffix(".md"))
    copy_docs(repo_root, output_root / "06-References")
    copy_runtime_beliefs(runtime_root, output_root / "06-References" / "beliefs")
    write_text(
        output_root / "Home.md",
        render_home(summary, trainer_rows, memory_manifest, belief_manifest, packet_manifest, domain_pages, traces.get("research_signals", {}), frontier_queue_count),
    )
    write_text(output_root / "00-Intent" / "System Intent.md", render_intent())
    write_text(output_root / "05-Runtime" / "Run Ledger.md", render_run_ledger(summary))
    write_text(output_root / "05-Runtime" / "Trainer State.md", render_trainer_state(trainer_rows))
    write_text(output_root / "05-Runtime" / "Memory Index.md", render_memory_index(memory_manifest))
    write_text(output_root / "05-Runtime" / "Packet Status.md", render_packet_status(packet_manifest))
    write_text(output_root / "05-Runtime" / "Working Memory.md", render_working_memory(working_memory))
    write_text(output_root / "05-Runtime" / "Episode Memory.md", render_episode_memory(episode_rows))
    write_text(output_root / "05-Runtime" / "Outcome State.md", render_outcome_state(memory_manifest))
    write_text(output_root / "05-Runtime" / "Research Signals.md", render_research_signals(traces.get("research_signals", {})))
    write_text(output_root / "05-Runtime" / "Self Edit Queue.md", render_self_edit_queue(runtime_root))
    return {
        "vault_root": str(output_root),
        "run_count": summary["run_count"],
        "trainer_entries": len(trainer_rows),
        "memory_document_count": memory_manifest["document_count"],
        "belief_count": belief_manifest["belief_count"],
        "domain_page_count": len(domain_pages),
        "episode_count": len(episode_rows),
    }
