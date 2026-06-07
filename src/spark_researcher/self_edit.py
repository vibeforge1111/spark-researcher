from __future__ import annotations

import difflib
import copy
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import load_config
from .paths import IGNORED_NAMES, resolve_runtime_root, self_edit_root
from .tracing import start_trace


SELF_EDIT_APPLY_TOOL_NAME = "spark-researcher.self_edit.apply"
SELF_EDIT_APPLY_CAPABILITY_ID = "capability:spark-researcher:self-edit.apply"
SELF_EDIT_APPLY_ACTION_TYPE = "edit_file"


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")


BUILTIN_BACKEND_PROFILES = {
    "codex-exec": {
        "description": "Run Codex CLI non-interactively against the copied workspace.",
        "command": [
            "codex",
            "--ask-for-approval",
            "never",
            "--sandbox",
            "workspace-write",
            "exec",
            "--cd",
            "{workspace}",
            "--skip-git-repo-check",
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


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _proposal_dir(runtime_root: Path, proposal_id: str) -> Path:
    return self_edit_root(runtime_root) / proposal_id


def _workspace_dir(proposal_id: str) -> Path:
    return Path(tempfile.gettempdir()) / "spark-researcher-self-edit" / proposal_id / "workspace"


def _proposal_path(runtime_root: Path, proposal_id: str) -> Path:
    return _proposal_dir(runtime_root, proposal_id) / "proposal.json"


def _review_path(runtime_root: Path, proposal_id: str) -> Path:
    return _proposal_dir(runtime_root, proposal_id) / "review.json"


def _apply_result_ledger_path(runtime_root: Path, proposal_id: str) -> Path:
    return _proposal_dir(runtime_root, proposal_id) / "apply-result-ledger.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _harness_artifact_ref(kind: str, path_or_uri: str, summary: str) -> dict[str, Any]:
    return {
        "id": f"artifact:self-edit-apply-{now_stamp()}",
        "kind": kind,
        "path_or_uri": path_or_uri,
        "redaction_class": "metadata_only",
        "summary": summary,
    }


def _harness_trace_ref(summary: str) -> dict[str, Any]:
    return {
        "id": f"trace:self-edit-apply-{now_stamp()}",
        "redaction_class": "metadata_only",
        "summary": summary,
    }


def _contains_string(value: Any, needle: str) -> bool:
    if isinstance(value, str):
        return needle in value
    if isinstance(value, dict):
        return any(_contains_string(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_contains_string(item, needle) for item in value)
    return False


def _harness_core_source_candidates() -> list[Path]:
    candidates: list[Path] = []
    spark_home = os.environ.get("SPARK_HOME")
    if spark_home:
        candidates.append(Path(spark_home).expanduser() / "modules" / "spark-harness-core" / "source" / "src")
    candidates.append(Path.home() / ".spark" / "modules" / "spark-harness-core" / "source" / "src")
    return candidates


def _load_harness_kernel_class() -> type[Any]:
    try:
        from spark_harness_core import HarnessKernel

        return HarnessKernel
    except ModuleNotFoundError:
        pass

    for candidate in _harness_core_source_candidates():
        if not (candidate / "spark_harness_core" / "__init__.py").exists():
            continue
        candidate_text = str(candidate)
        if candidate_text not in sys.path:
            sys.path.insert(0, candidate_text)
        try:
            from spark_harness_core import HarnessKernel

            return HarnessKernel
        except ModuleNotFoundError:
            continue
    raise RuntimeError("spark_harness_core_unavailable")


def _self_edit_apply_action_id(decision: dict[str, Any]) -> str | None:
    envelope = decision.get("envelope") if isinstance(decision.get("envelope"), dict) else {}
    proposed_actions = envelope.get("proposed_actions") if isinstance(envelope.get("proposed_actions"), list) else []
    for action in proposed_actions:
        if not isinstance(action, dict):
            continue
        if action.get("capability_id") != SELF_EDIT_APPLY_CAPABILITY_ID:
            continue
        action_id = str(action.get("action_id") or "")
        return action_id or None
    return None


def _verify_self_edit_apply_governor(decision: dict[str, Any]) -> dict[str, Any]:
    HarnessKernel = _load_harness_kernel_class()
    kernel = HarnessKernel(surface=str(decision.get("surface") or "cli"))
    verifier = getattr(kernel, "verify_governor_execution_authority", None)
    if not callable(verifier):
        return {"allowed": False, "reason_codes": ["harness_core_governor_verifier_unavailable"]}
    return verifier(
        decision,
        expected_capability_id=SELF_EDIT_APPLY_CAPABILITY_ID,
        expected_action_type=SELF_EDIT_APPLY_ACTION_TYPE,
        tool_name=SELF_EDIT_APPLY_TOOL_NAME,
        action_id=_self_edit_apply_action_id(decision),
    )


def _matching_self_edit_authorization(decision: dict[str, Any], *, action_id: str | None = None) -> dict[str, Any] | None:
    turn_id = str(decision.get("turn_id") or "")
    for authorization in decision.get("authorizations", []):
        if (
            isinstance(authorization, dict)
            and authorization.get("schema_version") == "authorization-decision-v1"
            and authorization.get("capability_id") == SELF_EDIT_APPLY_CAPABILITY_ID
            and authorization.get("verdict") == "allow"
            and str(authorization.get("turn_id") or "") == turn_id
            and str(authorization.get("action_id") or "")
            and (action_id is None or str(authorization.get("action_id") or "") == action_id)
            and str(authorization.get("decision_id") or "")
        ):
            return authorization
    return None


def _matching_self_edit_ledger(decision: dict[str, Any], *, authorization: dict[str, Any]) -> dict[str, Any] | None:
    turn_id = str(decision.get("turn_id") or "")
    authorization_action_id = str(authorization.get("action_id") or "")
    authorization_decision_id = str(authorization.get("decision_id") or "")
    for ledger in decision.get("tool_ledgers", []):
        if (
            isinstance(ledger, dict)
            and ledger.get("schema_version") == "tool-call-ledger-v1"
            and str(ledger.get("turn_id") or "") == turn_id
            and str(ledger.get("action_id") or "") == authorization_action_id
            and ledger.get("tool_name") == SELF_EDIT_APPLY_TOOL_NAME
            and ledger.get("capability_id") == SELF_EDIT_APPLY_CAPABILITY_ID
        ):
            result = ledger.get("result") if isinstance(ledger.get("result"), dict) else {}
            ledger_authorization = ledger.get("authorization") if isinstance(ledger.get("authorization"), dict) else {}
            if (
                result.get("status") == "not_started"
                and ledger_authorization.get("verdict") == "allow"
                and str(ledger_authorization.get("turn_id") or "") == turn_id
                and str(ledger_authorization.get("action_id") or "") == authorization_action_id
                and str(ledger_authorization.get("capability_id") or "") == SELF_EDIT_APPLY_CAPABILITY_ID
                and str(ledger_authorization.get("decision_id") or "") == authorization_decision_id
            ):
                return ledger
    return None


def _validate_self_edit_apply_governor(decision: dict[str, Any], *, proposal_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    boundary = decision.get("execution_boundary") if isinstance(decision.get("execution_boundary"), dict) else {}
    envelope = decision.get("envelope") if isinstance(decision.get("envelope"), dict) else {}
    action_authority = envelope.get("action_authority") if isinstance(envelope.get("action_authority"), dict) else {}
    proposed_actions = envelope.get("proposed_actions") if isinstance(envelope.get("proposed_actions"), list) else []

    if decision.get("schema_version") != "governor-decision-v1":
        errors.append("schema_version_not_governor_decision_v1")
    if decision.get("outcome") != "execute":
        errors.append("outcome_not_execute")
    if decision.get("authority_state") != "executable":
        errors.append("authority_state_not_executable")
    if boundary.get("action_authorized") is not True:
        errors.append("execution_boundary_not_authorized")
    if boundary.get("legacy_authority_demoted") is not True:
        errors.append("legacy_authority_not_demoted")
    if boundary.get("requires_human_confirmation") is not True:
        errors.append("human_confirmation_not_required")
    if envelope.get("schema_version") != "turn-intent-envelope-vnext":
        errors.append("envelope_not_vnext")
    if action_authority.get("state") != "executable":
        errors.append("envelope_authority_not_executable")
    if not any(isinstance(action, dict) and action.get("capability_id") == SELF_EDIT_APPLY_CAPABILITY_ID for action in proposed_actions):
        errors.append("self_edit_apply_action_missing")
    if not _contains_string(decision, proposal_id):
        errors.append("proposal_id_not_bound_to_governor_decision")

    try:
        verification = _verify_self_edit_apply_governor(decision)
    except RuntimeError as exc:
        verification = {"allowed": False, "reason_codes": [str(exc) or "harness_core_governor_verifier_failed"]}
    for reason in verification.get("reason_codes", []):
        reason_text = str(reason)
        if reason_text and reason_text not in errors:
            errors.append(reason_text)

    verification_action_id = str(verification.get("action_id") or "") or _self_edit_apply_action_id(decision)
    authorization = _matching_self_edit_authorization(decision, action_id=verification_action_id)
    if not authorization:
        errors.append("allow_authorization_missing")
    else:
        approval = authorization.get("approval") if isinstance(authorization.get("approval"), dict) else {}
        if approval.get("required") is not True or approval.get("status") != "approved":
            errors.append("approved_human_confirmation_missing")

    ledger = _matching_self_edit_ledger(decision, authorization=authorization) if authorization else None
    if not ledger:
        errors.append("pre_execution_tool_ledger_missing")

    if errors:
        raise RuntimeError("Self-edit apply requires GovernorDecisionV1 authority: " + ", ".join(errors))
    return authorization or {}, ledger or {}


def _finalize_self_edit_apply_ledger(
    source_ledger: dict[str, Any],
    *,
    status: str,
    output_path: Path,
    summary: str,
    error_path: Path | None = None,
) -> dict[str, Any]:
    ledger = copy.deepcopy(source_ledger)
    verdict = "passed" if status == "success" else "failed" if status == "failure" else "pending"
    lifecycle = [dict(item) for item in ledger.get("lifecycle", []) if isinstance(item, dict)]
    execute_stage = {"stage": "execute", "at": _iso_now(), "verdict": verdict}
    if lifecycle and lifecycle[-1].get("stage") == "execute":
        lifecycle[-1] = execute_stage
    else:
        lifecycle.append(execute_stage)
    result = {
        "status": status,
        "summary": summary,
        "sanitized_output_ref": _harness_artifact_ref("tool_output", str(output_path), summary),
    }
    if error_path is not None:
        result["error_ref"] = _harness_artifact_ref("tool_error", str(error_path), "Sanitized self-edit apply error reference.")
    ledger["lifecycle"] = lifecycle
    ledger["result"] = result
    ledger["trace"] = _harness_trace_ref(f"Final ledger for {SELF_EDIT_APPLY_TOOL_NAME}.")
    return ledger


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


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _git_output(repo_root: Path, *args: str) -> str:
    result = _git(repo_root, *args)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _current_branch(repo_root: Path) -> str:
    return _git_output(repo_root, "branch", "--show-current")


def _remote_exists(repo_root: Path, remote_name: str = "origin") -> bool:
    result = _git(repo_root, "remote", "get-url", remote_name)
    return result.returncode == 0


def _checkout_branch(repo_root: Path, branch_name: str, *, create: bool) -> None:
    if create:
        _git_output(repo_root, "checkout", "-b", branch_name)
    else:
        _git_output(repo_root, "checkout", branch_name)


def _commit_paths(repo_root: Path, paths: list[str], message: str) -> str:
    _git_output(repo_root, "add", *paths)
    result = _git(repo_root, "commit", "-m", message)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        detail = stderr or stdout
        raise RuntimeError(detail or "git commit failed")
    return _git_output(repo_root, "rev-parse", "HEAD")


def _push_branch(repo_root: Path, branch_name: str, remote_name: str = "origin") -> None:
    _git_output(repo_root, "push", "-u", remote_name, branch_name)


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
    trace = start_trace(runtime_root, kind="self_edit_propose", name=prompt[:80], attributes={"dry_run": dry_run, "backend_profile": backend_profile})
    mutable_targets = config.self_edit.mutable_targets or config.mutable_targets
    if not mutable_targets:
        trace.finish(status="error", attributes={"error": "No mutable targets declared for self edit."})
        raise RuntimeError("No mutable targets declared for self edit.")
    if config.guardrails.require_clean_git_for_self_edit and run_git_status(repo_root):
        trace.finish(status="error", attributes={"error": "Git worktree must be clean before self-edit proposals."})
        raise RuntimeError("Git worktree must be clean before self-edit proposals.")
    proposal_id = f"{now_stamp()}-self-edit"
    proposal_root = self_edit_root(runtime_root) / proposal_id
    workspace_root = _workspace_dir(proposal_id)
    # Use atomic creation to prevent TOCTOU race on predictable temp path
    try:
        os.makedirs(workspace_root, exist_ok=False)
    except FileExistsError:
        shutil.rmtree(workspace_root)
        os.makedirs(workspace_root, exist_ok=False)
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
    elif status == "pending_review" and not allowed_changes:
        status = "no_changes"
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
        "trace_id": trace.trace_id,
        "trace_path": str(trace.path),
        "command": command,
        "mutable_targets": mutable_targets,
        "change_count": len(allowed_changes),
        "allowed_changes": allowed_changes,
        "blocked_changes": blocked_changes,
    }
    _write_json(proposal_root / "proposal.json", proposal)
    write_text(proposal_root / "diff.txt", "\n\n".join(change["diff"] for change in allowed_changes + blocked_changes if change["diff"]))
    trace.finish(status="ok", attributes={"status": status, "change_count": len(allowed_changes), "blocked_change_count": len(blocked_changes)})
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
    trace = start_trace(runtime_root, kind="self_edit_review", name=proposal_id, attributes={"decision": decision})
    proposal = _load_json(_proposal_path(runtime_root, proposal_id))
    if not proposal:
        trace.finish(status="error", attributes={"error": f"Unknown proposal: {proposal_id}"})
        raise FileNotFoundError(f"Unknown proposal: {proposal_id}")
    normalized_decision = decision.strip().lower()
    if normalized_decision not in {"approve", "defer", "reject"}:
        trace.finish(status="error", attributes={"error": "Decision must be approve, defer, or reject."})
        raise RuntimeError("Decision must be approve, defer, or reject.")
    lineage = [item.strip() for item in lineage_failures if item.strip()]
    if normalized_decision == "approve" and len(lineage) != 3:
        trace.finish(status="error", attributes={"error": "Approved self-edit proposals require exactly 3 lineage failures."})
        raise RuntimeError("Approved self-edit proposals require exactly 3 lineage failures.")
    if normalized_decision == "approve" and proposal.get("blocked_changes"):
        trace.finish(status="error", attributes={"error": "Cannot approve a proposal with blocked changes."})
        raise RuntimeError("Cannot approve a proposal with blocked changes.")
    if normalized_decision == "approve" and int(proposal.get("change_count", 0)) <= 0:
        trace.finish(status="error", attributes={"error": "Cannot approve a proposal with no changes."})
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
        "trace_id": trace.trace_id,
        "trace_path": str(trace.path),
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
    trace.finish(status="ok", attributes={"decision": normalized_decision, "change_count": proposal.get("change_count", 0)})
    return {"proposal": _proposal_summary(proposal, review), "review": review}


def apply_proposal(
    config_path: Path,
    proposal_id: str,
    *,
    git_mode_override: str | None = None,
    push_override: bool | None = None,
    branch_name_override: str | None = None,
    commit_message_override: str | None = None,
    governor_decision_path: Path | None = None,
    governor_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    repo_root = config_path.parent.resolve()
    runtime_root = resolve_runtime_root(config_path)
    trace = start_trace(runtime_root, kind="self_edit_apply", name=proposal_id)
    if config.guardrails.require_clean_git_for_self_edit and run_git_status(repo_root):
        trace.finish(status="error", attributes={"error": "Git worktree must be clean before applying a self-edit proposal."})
        raise RuntimeError("Git worktree must be clean before applying a self-edit proposal.")
    proposal_path = _proposal_path(runtime_root, proposal_id)
    if not proposal_path.exists():
        trace.finish(status="error", attributes={"error": f"Unknown proposal: {proposal_id}"})
        raise FileNotFoundError(f"Unknown proposal: {proposal_id}")
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    if governor_decision is None:
        if governor_decision_path is None:
            trace.finish(status="error", attributes={"error": "Self-edit apply requires GovernorDecisionV1 authority."})
            raise RuntimeError("Self-edit apply requires a GovernorDecisionV1 file.")
        if not governor_decision_path.exists():
            trace.finish(status="error", attributes={"error": f"GovernorDecisionV1 file not found: {governor_decision_path}"})
            raise FileNotFoundError(f"GovernorDecisionV1 file not found: {governor_decision_path}")
        governor_decision = json.loads(governor_decision_path.read_text(encoding="utf-8"))
    authorization, pre_execution_ledger = _validate_self_edit_apply_governor(governor_decision, proposal_id=proposal_id)
    authority_summary = {
        "schema_version": governor_decision.get("schema_version"),
        "decision_id": governor_decision.get("decision_id"),
        "authorization_decision_id": authorization.get("decision_id"),
        "pre_execution_ledger_id": pre_execution_ledger.get("ledger_id"),
        "tool_name": SELF_EDIT_APPLY_TOOL_NAME,
        "capability_id": SELF_EDIT_APPLY_CAPABILITY_ID,
        "governor_decision_path": str(governor_decision_path) if governor_decision_path else "<in-memory>",
    }
    apply_ledger_path = _apply_result_ledger_path(runtime_root, proposal_id)
    review = _load_json(_review_path(runtime_root, proposal_id))
    if not review:
        trace.finish(status="error", attributes={"error": "Proposal must be reviewed before apply."})
        raise RuntimeError("Proposal must be reviewed before apply.")
    if review.get("decision") != "approve":
        trace.finish(status="error", attributes={"error": "Only approved proposals can be applied."})
        raise RuntimeError("Only approved proposals can be applied.")
    if len(review.get("lineage_failures", [])) != 3:
        raise RuntimeError("Approved proposals must keep exactly 3 lineage failures.")
    if proposal.get("blocked_changes"):
        trace.finish(status="error", attributes={"error": "Proposal contains out-of-scope edits and cannot be applied."})
        raise RuntimeError("Proposal contains out-of-scope edits and cannot be applied.")
    if int(proposal.get("change_count", 0)) <= 0:
        trace.finish(status="error", attributes={"error": "Proposal has no changes to apply."})
        raise RuntimeError("Proposal has no changes to apply.")
    if run_git_status(repo_root):
        trace.finish(status="error", attributes={"error": "Git worktree must be clean before applying a self-edit proposal."})
        raise RuntimeError("Git worktree must be clean before applying a self-edit proposal.")
    workspace_root = Path(proposal["workspace_root"])
    git_mode = str(git_mode_override or config.self_edit.git_mode or "manual").strip().lower()
    if git_mode not in {"manual", "branch", "main"}:
        raise RuntimeError(f"Unsupported self-edit git mode: {git_mode}")
    branch_name = _current_branch(repo_root)
    original_branch = branch_name
    created_branch = False
    if git_mode == "branch":
        branch_name = str(branch_name_override or f"{config.self_edit.branch_prefix}{proposal_id}").replace("\\", "/")
        _checkout_branch(repo_root, branch_name, create=True)
        created_branch = True
    elif git_mode == "main":
        target_main = str(config.self_edit.main_branch or "main")
        if branch_name != target_main:
            raise RuntimeError(f"Direct main mode requires current branch '{target_main}', found '{branch_name}'.")
    should_push = bool(config.self_edit.auto_push if push_override is None else push_override)
    if git_mode in {"branch", "main"} and should_push and not _remote_exists(repo_root):
        trace.finish(status="error", attributes={"error": "Cannot auto-push because git remote 'origin' is not configured."})
        raise RuntimeError("Cannot auto-push because git remote 'origin' is not configured.")
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
    commit_sha = None
    pushed = False
    commit_message = None
    try:
        if git_mode in {"branch", "main"}:
            commit_message = str(
                commit_message_override
                or config.self_edit.commit_message_template
                or "Apply self-edit proposal {proposal_id}"
            ).format(proposal_id=proposal_id)
            commit_sha = _commit_paths(repo_root, applied, commit_message)
            if should_push:
                _push_branch(repo_root, _current_branch(repo_root))
                pushed = True
    except Exception as exc:
        result_ledger = _finalize_self_edit_apply_ledger(
            pre_execution_ledger,
            status="failure",
            output_path=proposal_path,
            error_path=proposal_path,
            summary=f"Self-edit proposal {proposal_id} failed during apply; see sanitized proposal status.",
        )
        _write_json(apply_ledger_path, result_ledger)
        proposal["status"] = "applied_push_failed" if commit_sha and should_push and not pushed else "apply_failed"
        proposal["git_mode"] = git_mode
        proposal["git_branch"] = _current_branch(repo_root)
        proposal["git_commit_sha"] = commit_sha
        proposal["git_pushed"] = pushed
        proposal["apply_trace_id"] = trace.trace_id
        proposal["apply_trace_path"] = str(trace.path)
        proposal["apply_error"] = str(exc)
        proposal["authority"] = authority_summary
        proposal["apply_result_ledger_path"] = str(apply_ledger_path)
        proposal["apply_result_ledger_id"] = result_ledger.get("ledger_id")
        proposal["apply_result_status"] = "failure"
        _write_json(proposal_path, proposal)
        trace.finish(
            status="error",
            attributes={"git_mode": git_mode, "applied_file_count": len(applied), "pushed": pushed, "error": str(exc)},
        )
        raise
    proposal["git_mode"] = git_mode
    proposal["git_branch"] = _current_branch(repo_root)
    proposal["git_commit_sha"] = commit_sha
    proposal["git_pushed"] = pushed
    proposal["apply_trace_id"] = trace.trace_id
    proposal["apply_trace_path"] = str(trace.path)
    result_ledger = _finalize_self_edit_apply_ledger(
        pre_execution_ledger,
        status="success",
        output_path=proposal_path,
        summary=f"Self-edit proposal {proposal_id} applied {len(applied)} file(s).",
    )
    _write_json(apply_ledger_path, result_ledger)
    proposal["authority"] = authority_summary
    proposal["apply_result_ledger_path"] = str(apply_ledger_path)
    proposal["apply_result_ledger_id"] = result_ledger.get("ledger_id")
    proposal["apply_result_status"] = "success"
    proposal.pop("apply_error", None)
    _write_json(proposal_path, proposal)
    trace.finish(status="ok", attributes={"git_mode": git_mode, "applied_file_count": len(applied), "pushed": pushed})
    return {
        "proposal_id": proposal_id,
        "applied_files": applied,
        "git_mode": git_mode,
        "branch": _current_branch(repo_root),
        "original_branch": original_branch,
        "created_branch": created_branch,
        "commit_message": commit_message,
        "commit_sha": commit_sha,
        "pushed": pushed,
        "trace_id": trace.trace_id,
        "trace_path": str(trace.path),
    }


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
