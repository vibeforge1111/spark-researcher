from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

for HARNESS_CORE_SRC in (
    Path(__file__).resolve().parents[2] / "spark-harness-core" / "src",
    Path.home() / ".spark" / "modules" / "spark-harness-core" / "source" / "src",
):
    if HARNESS_CORE_SRC.exists() and str(HARNESS_CORE_SRC) not in sys.path:
        sys.path.insert(0, str(HARNESS_CORE_SRC))
        break

from spark_harness_core import HarnessKernel, evidence_ref
from spark_researcher import self_edit
from spark_researcher.config import CommandSpec, MetricSpec, ProjectConfig, save_config
from spark_researcher.self_edit import (
    SELF_EDIT_APPLY_CAPABILITY_ID,
    SELF_EDIT_APPLY_TOOL_NAME,
    _apply_result_ledger_path,
    _proposal_path,
    _review_path,
    _workspace_dir,
    apply_proposal,
)


def _governor_decision(proposal_id: str, *, capability_id: str = SELF_EDIT_APPLY_CAPABILITY_ID) -> dict:
    kernel = HarnessKernel(surface="cli")
    action = kernel.proposed_action(
        capability_id=capability_id,
        action_type="edit_file",
        risk_tier="high",
        summary=f"Apply reviewed self-edit proposal {proposal_id}.",
        args_path=f"proposal:{proposal_id}",
        requires_confirmation=True,
    )
    evidence = [
        evidence_ref(
            "fresh_user_intent",
            "test",
            f"Fresh owner request to apply self-edit proposal {proposal_id}.",
            confidence=1.0,
        ),
        evidence_ref(
            "human_confirmation",
            "test",
            f"Governor decision is bound to self-edit proposal {proposal_id}.",
            confidence=1.0,
        )
    ]
    envelope = kernel.create_envelope(
        selected_move="execute_action",
        intent_summary=f"Apply reviewed self-edit proposal {proposal_id}.",
        raw_turn_summary=f"Owner explicitly approved self-edit proposal {proposal_id}.",
        evidence=evidence,
        proposed_actions=[action],
        authority_state="executable",
        risk_tier="high",
        confidence=1.0,
    )
    authorization = kernel.authorize(
        envelope,
        action,
        approval_ref=evidence_ref(
            "human_confirmation",
            "test",
            f"Owner approved proposal {proposal_id}.",
            confidence=1.0,
        ),
    )
    ledger = kernel.record_tool_call(
        envelope=envelope,
        action=action,
        authorization=authorization,
        tool_name=SELF_EDIT_APPLY_TOOL_NAME,
        status="not_started",
        output_path=f"proposal:{proposal_id}",
        summary=f"Self-edit proposal {proposal_id} is authorized but not applied yet.",
    )
    return kernel.governor_decision(
        envelope,
        authorizations=[authorization],
        tool_ledgers=[ledger],
        reply_style="compact_status",
        reply_instruction="Apply the reviewed self-edit proposal.",
    )


def _write_self_edit_fixture(repo_root: Path, proposal_id: str) -> tuple[Path, Path]:
    repo_root.mkdir(parents=True, exist_ok=True)
    config_path = repo_root / "spark-researcher.project.json"
    save_config(
        config_path,
        ProjectConfig(
            project_name="self-edit-test",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
            metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
        ),
    )
    target = repo_root / "README.md"
    target.write_text("old\n", encoding="utf-8")
    workspace_root = _workspace_dir(proposal_id)
    workspace_root.mkdir()
    (workspace_root / "README.md").write_text("new\n", encoding="utf-8")
    proposal = {
        "proposal_id": proposal_id,
        "status": "reviewed",
        "change_count": 1,
        "blocked_changes": [],
        "allowed_changes": [{"path": "README.md", "status": "modified"}],
        "mutable_targets": ["README.md"],
        "workspace_root": str(workspace_root),
    }
    proposal_path = _proposal_path(repo_root, proposal_id)
    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    review_path = _review_path(repo_root, proposal_id)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        json.dumps({"decision": "approve", "lineage_failures": ["a", "b", "c"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path, target


def test_git_output_error_omits_raw_stderr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    private_detail = f"fatal: cannot read {tmp_path / 'private-token-secret'}"
    monkeypatch.setattr(
        self_edit,
        "_git",
        lambda _repo_root, *_args: subprocess.CompletedProcess(["git", "status"], 1, "", private_detail),
    )

    with pytest.raises(RuntimeError) as error:
        self_edit._git_output(tmp_path, "status", "--porcelain")

    message = str(error.value)
    assert "Git status failed" in message
    assert private_detail not in message
    assert str(tmp_path) not in message


def test_apply_proposal_checks_remote_before_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    proposal_id = "proposal-1"
    config_path, target = _write_self_edit_fixture(tmp_path / "repo", proposal_id)

    monkeypatch.setattr("spark_researcher.self_edit.run_git_status", lambda repo_root: False)
    monkeypatch.setattr("spark_researcher.self_edit._current_branch", lambda repo_root: "main")
    monkeypatch.setattr("spark_researcher.self_edit._remote_exists", lambda repo_root: False)

    with pytest.raises(RuntimeError, match="origin"):
        apply_proposal(
            config_path,
            proposal_id,
            git_mode_override="main",
            push_override=True,
            governor_decision=_governor_decision(proposal_id),
        )

    assert target.read_text(encoding="utf-8") == "old\n"
    proposal = json.loads(_proposal_path(tmp_path / "repo", proposal_id).read_text(encoding="utf-8"))
    assert proposal["status"] == "reviewed"
    assert "applied_at" not in proposal


def test_apply_proposal_records_push_failure_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    proposal_id = "proposal-2"
    repo_root = tmp_path / "repo"
    config_path, target = _write_self_edit_fixture(repo_root, proposal_id)

    monkeypatch.setattr("spark_researcher.self_edit.run_git_status", lambda repo_root: False)
    monkeypatch.setattr("spark_researcher.self_edit._current_branch", lambda repo_root: "main")
    monkeypatch.setattr("spark_researcher.self_edit._remote_exists", lambda repo_root: True)
    monkeypatch.setattr("spark_researcher.self_edit._commit_paths", lambda repo_root, paths, message: "abc123")

    def _raise_push(repo_root: Path, branch_name: str, remote_name: str = "origin") -> None:
        raise RuntimeError("push broke")

    monkeypatch.setattr("spark_researcher.self_edit._push_branch", _raise_push)

    with pytest.raises(RuntimeError, match="push broke"):
        apply_proposal(
            config_path,
            proposal_id,
            git_mode_override="main",
            push_override=True,
            governor_decision=_governor_decision(proposal_id),
        )

    assert target.read_text(encoding="utf-8") == "new\n"
    proposal = json.loads(_proposal_path(repo_root, proposal_id).read_text(encoding="utf-8"))
    assert proposal["status"] == "applied_push_failed"
    assert proposal["git_commit_sha"] == "abc123"
    assert proposal["git_pushed"] is False
    assert proposal["apply_error"] == "push broke"
    assert proposal["authority"]["schema_version"] == "governor-decision-v1"
    assert proposal["apply_result_status"] == "failure"
    ledger = json.loads(_apply_result_ledger_path(repo_root, proposal_id).read_text(encoding="utf-8"))
    assert ledger["schema_version"] == "tool-call-ledger-v1"
    assert ledger["result"]["status"] == "failure"


def test_apply_proposal_requires_governor_before_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    proposal_id = "proposal-3"
    config_path, target = _write_self_edit_fixture(tmp_path / "repo", proposal_id)
    monkeypatch.setattr("spark_researcher.self_edit.run_git_status", lambda repo_root: False)

    with pytest.raises(RuntimeError, match="GovernorDecisionV1"):
        apply_proposal(config_path, proposal_id, git_mode_override="manual")

    assert target.read_text(encoding="utf-8") == "old\n"


def test_apply_proposal_rejects_governor_for_another_proposal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    proposal_id = "proposal-4"
    config_path, target = _write_self_edit_fixture(tmp_path / "repo", proposal_id)
    monkeypatch.setattr("spark_researcher.self_edit.run_git_status", lambda repo_root: False)

    with pytest.raises(RuntimeError, match="proposal_id_not_bound"):
        apply_proposal(config_path, proposal_id, git_mode_override="manual", governor_decision=_governor_decision("other-proposal"))

    assert target.read_text(encoding="utf-8") == "old\n"


def test_apply_proposal_rejects_copied_pre_execution_ledger(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    proposal_id = "proposal-copied-ledger"
    config_path, target = _write_self_edit_fixture(tmp_path / "repo", proposal_id)
    monkeypatch.setattr("spark_researcher.self_edit.run_git_status", lambda repo_root: False)

    governor_decision = _governor_decision(proposal_id)
    governor_decision["tool_ledgers"][0]["action_id"] = "action:copied-stale-ledger"
    governor_decision["tool_ledgers"][0]["authorization"]["action_id"] = "action:copied-stale-ledger"

    with pytest.raises(RuntimeError, match="governor_missing_matching_tool_ledger"):
        apply_proposal(config_path, proposal_id, git_mode_override="manual", governor_decision=governor_decision)

    assert target.read_text(encoding="utf-8") == "old\n"


def test_apply_proposal_records_success_result_ledger(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    proposal_id = "proposal-5"
    repo_root = tmp_path / "repo"
    config_path, target = _write_self_edit_fixture(repo_root, proposal_id)
    monkeypatch.setattr("spark_researcher.self_edit.run_git_status", lambda repo_root: False)
    monkeypatch.setattr("spark_researcher.self_edit._current_branch", lambda repo_root: "main")

    result = apply_proposal(config_path, proposal_id, git_mode_override="manual", governor_decision=_governor_decision(proposal_id))

    assert target.read_text(encoding="utf-8") == "new\n"
    assert result["applied_files"] == ["README.md"]
    proposal = json.loads(_proposal_path(repo_root, proposal_id).read_text(encoding="utf-8"))
    assert proposal["authority"]["decision_id"].startswith("governor-decision:")
    assert proposal["apply_result_status"] == "success"
    ledger = json.loads(_apply_result_ledger_path(repo_root, proposal_id).read_text(encoding="utf-8"))
    assert ledger["schema_version"] == "tool-call-ledger-v1"
    assert ledger["tool_name"] == SELF_EDIT_APPLY_TOOL_NAME
    assert ledger["result"]["status"] == "success"
