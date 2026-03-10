from __future__ import annotations

import difflib
import json
import os
import shlex
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import load_config
from .paths import IGNORED_NAMES, resolve_runtime_root, self_edit_root


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")


BUILTIN_BACKEND_PROFILES = {
    "codex-exec": {
        "description": "Run Codex CLI non-interactively against the copied workspace.",
        "command": [
            "codex",
            "exec",
            "--cd",
            "{workspace}",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "-o",
            "{last_message}",
            "Read the request file at {request}. Apply the requested edits in this workspace only. Do not edit files outside the declared mutable targets in the request.",
        ],
    }
}


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, indent=2, sort_keys=True))


def _proposal_dir(runtime_root: Path, proposal_id: str) -> Path:
    return self_edit_root(runtime_root) / proposal_id


def _workspace_dir(proposal_id: str) -> Path:
    return Path(tempfile.gettempdir()) / "spark-researcher-self-edit" / proposal_id / "workspace"


def _proposal_path(runtime_root: Path, proposal_id: str) -> Path:
    return _proposal_dir(runtime_root, proposal_id) / "proposal.json"


def _review_path(runtime_root: Path, proposal_id: str) -> Path:
    return _proposal_dir(runtime_root, proposal_id) / "review.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def backend_profiles() -> list[dict[str, Any]]:
    rows = []
    for name, spec in BUILTIN_BACKEND_PROFILES.items():
        executable = str(spec["command"][0])
        rows.append(
            {
                "name": name,
                "description": spec["description"],
                "command": spec["command"],
                "installed": shutil.which(executable) is not None,
                "executable": executable,
            }
        )
    return rows


def run_git_status(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain", "--untracked-files=no"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def copy_repo(repo_root: Path, workspace_root: Path) -> None:
    shutil.copytree(
        repo_root,
        workspace_root,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(*IGNORED_NAMES),
    )


def is_allowed_path(path_text: str, mutable_targets: list[str]) -> bool:
    normalized = path_text.replace("\\", "/")
    return any(normalized == target or normalized.startswith(target.rstrip("/") + "/") for target in mutable_targets)


def file_inventory(root: Path) -> dict[str, bytes]:
    rows: dict[str, bytes] = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in IGNORED_NAMES for part in rel.parts):
            continue
        if path.is_file():
            rows[str(rel).replace("\\", "/")] = path.read_bytes()
    return rows


def diff_text(path_text: str, before: bytes, after: bytes) -> str:
    try:
        before_text = before.decode("utf-8")
        after_text = after.decode("utf-8")
    except UnicodeDecodeError:
        return f"Binary diff omitted for {path_text}"
    return "\n".join(
        difflib.unified_diff(
            before_text.splitlines(),
            after_text.splitlines(),
            fromfile=f"a/{path_text}",
            tofile=f"b/{path_text}",
            lineterm="",
        )
    )


def collect_changes(repo_root: Path, workspace_root: Path, mutable_targets: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    before = file_inventory(repo_root)
    after = file_inventory(workspace_root)
    allowed: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for path_text in sorted(set(before) | set(after)):
        before_bytes = before.get(path_text)
        after_bytes = after.get(path_text)
        if before_bytes == after_bytes:
            continue
        status = "modified"
        if before_bytes is None:
            status = "added"
        elif after_bytes is None:
            status = "deleted"
        row = {"path": path_text, "status": status, "diff": diff_text(path_text, before_bytes or b"", after_bytes or b"")}
        if is_allowed_path(path_text, mutable_targets):
            allowed.append(row)
        else:
            blocked.append(row)
    return allowed, blocked


def expand_command(parts: list[str], *, workspace_root: Path, request_path: Path, last_message_path: Path) -> list[str]:
    return [
        part.replace("{workspace}", str(workspace_root))
        .replace("{request}", str(request_path))
        .replace("{last_message}", str(last_message_path))
        for part in parts
    ]


def guard_command(parts: list[str], blocked_fragments: list[str]) -> None:
    lowered = " ".join(parts).lower()
    for fragment in blocked_fragments:
        if fragment.lower() in lowered:
            raise RuntimeError(f"Blocked self-edit command fragment detected: {fragment}")


def render_request(prompt: str, preamble: str, mutable_targets: list[str]) -> str:
    return "\n".join(
        [
            "# Spark Researcher Self-Edit Request",
            "",
            "## Intent",
            "",
            preamble or "Keep the repo lightweight and transparent.",
            "",
            "## Owner Prompt",
            "",
            prompt,
            "",
            "## Hard Rules",
            "",
            "- Only edit declared mutable targets.",
            "- Prefer simplification over abstraction.",
            "- Do not auto-apply anything.",
            "- Keep every change easy to review.",
            "",
            "## Mutable Targets",
            "",
            *[f"- `{item}`" for item in mutable_targets],
        ]
    )


def _resolve_command_override(command_override: list[str] | None) -> list[str]:
    if command_override:
        return [str(item) for item in command_override]
    raw = os.environ.get("SPARK_RESEARCHER_SELF_EDIT_COMMAND", "").strip()
    if not raw:
        return []
    return shlex.split(raw, posix=False)


def _resolve_backend_profile(profile_name: str | None) -> dict[str, Any] | None:
    if not profile_name:
        return None
    key = profile_name.strip().lower()
    if key not in BUILTIN_BACKEND_PROFILES:
        raise RuntimeError(f"Unknown backend profile: {profile_name}")
    spec = BUILTIN_BACKEND_PROFILES[key]
    executable = str(spec["command"][0])
    resolved_executable = shutil.which(executable)
    if resolved_executable is None:
        raise RuntimeError(f"Backend profile '{profile_name}' requires '{executable}' in PATH.")
    return {"name": key, "description": spec["description"], "command": [resolved_executable, *spec["command"][1:]]}


def _proposal_summary(proposal: dict[str, Any], review: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "proposal_id": proposal.get("proposal_id"),
        "created_at": proposal.get("created_at"),
        "status": proposal.get("status"),
        "prompt": proposal.get("prompt"),
        "change_count": proposal.get("change_count"),
        "allowed_change_count": len(proposal.get("allowed_changes", [])),
        "blocked_change_count": len(proposal.get("blocked_changes", [])),
        "review_decision": review.get("decision") if review else None,
        "review_status": review.get("status") if review else None,
    }


def propose(
    config_path: Path,
    prompt: str,
    *,
    dry_run: bool = False,
    command_override: list[str] | None = None,
    backend_profile: str | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    repo_root = config_path.parent.resolve()
    runtime_root = resolve_runtime_root(config_path)
    mutable_targets = config.self_edit.mutable_targets or config.mutable_targets
    if not mutable_targets:
        raise RuntimeError("No mutable targets declared for self edit.")
    if config.guardrails.require_clean_git_for_self_edit and run_git_status(repo_root):
        raise RuntimeError("Git worktree must be clean before self-edit proposals.")
    proposal_id = f"{now_stamp()}-self-edit"
    proposal_root = self_edit_root(runtime_root) / proposal_id
    workspace_root = _workspace_dir(proposal_id)
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    copy_repo(repo_root, workspace_root)
    request_path = proposal_root / "request.md"
    last_message_path = proposal_root / "agent-last-message.txt"
    write_text(request_path, render_request(prompt, config.self_edit.prompt_preamble, mutable_targets))
    profile = _resolve_backend_profile(backend_profile)
    resolved_command = _resolve_command_override(command_override) or (profile["command"] if profile else []) or config.self_edit.command
    command = expand_command(
        resolved_command,
        workspace_root=workspace_root,
        request_path=request_path,
        last_message_path=last_message_path,
    )
    if command:
        guard_command(command, config.guardrails.blocked_command_fragments)
    stdout_path = proposal_root / "stdout.log"
    stderr_path = proposal_root / "stderr.log"
    status = "draft_only"
    if command and not dry_run:
        process = subprocess.run(command, cwd=str(workspace_root), capture_output=True, text=True, encoding="utf-8", errors="replace")
        write_text(stdout_path, process.stdout)
        write_text(stderr_path, process.stderr)
        status = "pending_review" if process.returncode == 0 else "failed"
    else:
        write_text(stdout_path, json.dumps({"command": command, "dry_run": dry_run}, indent=2))
        write_text(stderr_path, "")
    allowed_changes, blocked_changes = collect_changes(repo_root, workspace_root, mutable_targets)
    if blocked_changes:
        status = "blocked_scope_violation"
    proposal = {
        "proposal_id": proposal_id,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "status": status,
        "prompt": prompt,
        "request_path": str(request_path),
        "workspace_root": str(workspace_root),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "last_message_path": str(last_message_path),
        "backend_profile": profile["name"] if profile else None,
        "command": command,
        "mutable_targets": mutable_targets,
        "change_count": len(allowed_changes),
        "allowed_changes": allowed_changes,
        "blocked_changes": blocked_changes,
    }
    _write_json(proposal_root / "proposal.json", proposal)
    write_text(proposal_root / "diff.txt", "\n\n".join(change["diff"] for change in allowed_changes + blocked_changes if change["diff"]))
    return proposal


def review_proposal(
    config_path: Path,
    proposal_id: str,
    *,
    decision: str,
    root_lesson: str,
    lineage_failures: list[str],
    counterfactual: str,
    ghost_improvement_check: str,
    rollback_condition: str,
    notes: str = "",
) -> dict[str, Any]:
    runtime_root = resolve_runtime_root(config_path)
    proposal = _load_json(_proposal_path(runtime_root, proposal_id))
    if not proposal:
        raise FileNotFoundError(f"Unknown proposal: {proposal_id}")
    normalized_decision = decision.strip().lower()
    if normalized_decision not in {"approve", "defer", "reject"}:
        raise RuntimeError("Decision must be approve, defer, or reject.")
    lineage = [item.strip() for item in lineage_failures if item.strip()]
    if normalized_decision == "approve" and len(lineage) != 3:
        raise RuntimeError("Approved self-edit proposals require exactly 3 lineage failures.")
    if normalized_decision == "approve" and proposal.get("blocked_changes"):
        raise RuntimeError("Cannot approve a proposal with blocked changes.")
    if normalized_decision == "approve" and int(proposal.get("change_count", 0)) <= 0:
        raise RuntimeError("Cannot approve a proposal with no changes.")
    review = {
        "proposal_id": proposal_id,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "status": "approved" if normalized_decision == "approve" else normalized_decision,
        "decision": normalized_decision,
        "root_lesson": root_lesson.strip(),
        "lineage_failures": lineage,
        "counterfactual": counterfactual.strip(),
        "ghost_improvement_check": ghost_improvement_check.strip(),
        "rollback_condition": rollback_condition.strip(),
        "notes": notes.strip(),
        "guardrail_status": {
            "schema_gate": "pass",
            "lineage_gate": "pass" if len(lineage) == 3 else "fail" if normalized_decision == "approve" else "warn",
            "complexity_gate": "pass" if len(proposal.get("allowed_changes", [])) <= 12 else "warn",
            "transfer_gate": "warn",
            "memory_hygiene_gate": "pass",
            "human_gate": "pass",
        },
    }
    _write_json(_review_path(runtime_root, proposal_id), review)
    proposal["status"] = "reviewed" if normalized_decision == "approve" else normalized_decision
    _write_json(_proposal_path(runtime_root, proposal_id), proposal)
    return {"proposal": _proposal_summary(proposal, review), "review": review}


def apply_proposal(config_path: Path, proposal_id: str) -> dict[str, Any]:
    config = load_config(config_path)
    repo_root = config_path.parent.resolve()
    runtime_root = resolve_runtime_root(config_path)
    if config.guardrails.require_clean_git_for_self_edit and run_git_status(repo_root):
        raise RuntimeError("Git worktree must be clean before applying a self-edit proposal.")
    proposal_path = _proposal_path(runtime_root, proposal_id)
    if not proposal_path.exists():
        raise FileNotFoundError(f"Unknown proposal: {proposal_id}")
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    review = _load_json(_review_path(runtime_root, proposal_id))
    if not review:
        raise RuntimeError("Proposal must be reviewed before apply.")
    if review.get("decision") != "approve":
        raise RuntimeError("Only approved proposals can be applied.")
    if len(review.get("lineage_failures", [])) != 3:
        raise RuntimeError("Approved proposals must keep exactly 3 lineage failures.")
    if proposal.get("blocked_changes"):
        raise RuntimeError("Proposal contains out-of-scope edits and cannot be applied.")
    if int(proposal.get("change_count", 0)) <= 0:
        raise RuntimeError("Proposal has no changes to apply.")
    workspace_root = Path(proposal["workspace_root"])
    applied = []
    for change in proposal.get("allowed_changes", []):
        rel = change["path"]
        source = workspace_root / rel
        target = repo_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if change["status"] == "deleted":
            if target.exists():
                target.unlink()
        else:
            shutil.copyfile(source, target)
        applied.append(rel)
    proposal["status"] = "applied"
    proposal["applied_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()
    _write_json(proposal_path, proposal)
    return {"proposal_id": proposal_id, "applied_files": applied}


def proposal_status(config_path: Path) -> dict[str, Any]:
    runtime_root = resolve_runtime_root(config_path)
    root = self_edit_root(runtime_root)
    proposals = []
    if root.exists():
        for path in sorted(root.glob("*/proposal.json"), reverse=True):
            proposal = json.loads(path.read_text(encoding="utf-8"))
            review = _load_json(path.parent / "review.json")
            proposals.append(_proposal_summary(proposal, review))
    return {"proposal_count": len(proposals), "proposals": proposals}
