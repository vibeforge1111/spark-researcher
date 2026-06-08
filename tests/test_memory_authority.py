from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory_governor import memory_governor_decision
from spark_harness_core import HarnessKernel, evidence_ref
from spark_researcher.advisory import build_advisory
from spark_researcher.authority import (
    ADVISORY_EXECUTE_ACTION_TYPE,
    ADVISORY_EXECUTE_CAPABILITY_ID,
    ADVISORY_EXECUTE_TOOL_NAME,
    governor_decision_has_canonical_binding,
    MEMORY_WRITE_ACTION_TYPE,
    MEMORY_WRITE_CAPABILITY_ID,
    MEMORY_WRITE_TOOL_NAME,
)
from spark_researcher.beliefs import build_beliefs
from spark_researcher.config import CommandSpec, MetricSpec, ProjectConfig, load_config, save_config
from spark_researcher.memory import (
    record_episode,
    search_memory,
    sync_memory,
    sync_memory_authority_refs,
    working_memory_authority_refs,
    write_working_memory,
)
from spark_researcher.obsidian import build_vault
from spark_researcher.packets import packet_status
from spark_researcher.paths import memory_root, resolve_runtime_root, vault_root


def _write_config(repo_root: Path) -> Path:
    repo_root.mkdir(parents=True, exist_ok=True)
    config_path = repo_root / "spark-researcher.project.json"
    save_config(
        config_path,
        ProjectConfig(
            project_name="memory-authority-test",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"research": CommandSpec(args=["python", "-c", "print('score: 1')"])},
            metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
        ),
    )
    return config_path


def _write_ledger(runtime_root: Path) -> None:
    ledger_path = runtime_root / "artifacts" / "ledger" / "runs.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "run_id": "run-1",
        "project_name": "memory-authority-test",
        "command_name": "research",
        "candidate_id": "candidate-a",
        "candidate_summary": "summary",
        "hypothesis": "improve scoring",
        "metric_name": "score",
        "metric_value": 2.0,
        "baseline_value": 1.0,
        "verdict": "improved",
        "applied_mutations": [{"name": "lane", "value": "authority"}],
    }
    ledger_path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def _advisory_governor_decision() -> dict:
    kernel = HarnessKernel(surface="cli")
    action = kernel.proposed_action(
        capability_id=ADVISORY_EXECUTE_CAPABILITY_ID,
        action_type=ADVISORY_EXECUTE_ACTION_TYPE,
        risk_tier="medium",
        summary="Execute a Spark Researcher advisory.",
        args_path="advisory:test",
        requires_confirmation=True,
    )
    fresh_intent = evidence_ref(
        "fresh_user_intent",
        "test",
        "Fresh owner request for advisory execution.",
        confidence=1.0,
    )
    approval = evidence_ref(
        "human_confirmation",
        "test",
        "Owner approved advisory execution.",
        confidence=1.0,
    )
    envelope = kernel.create_envelope(
        selected_move="execute_action",
        intent_summary="Execute Spark Researcher advisory.",
        raw_turn_summary="Owner requested advisory execution.",
        evidence=[fresh_intent, approval],
        proposed_actions=[action],
        authority_state="executable",
        risk_tier="medium",
        confidence=1.0,
    )
    authorization = kernel.authorize(envelope, action, approval_ref=approval)
    ledger = kernel.record_tool_call(
        envelope=envelope,
        action=action,
        authorization=authorization,
        tool_name=ADVISORY_EXECUTE_TOOL_NAME,
        status="not_started",
        output_path="advisory:test",
        summary="Advisory execution is authorized but not started.",
    )
    return kernel.governor_decision(envelope, authorizations=[authorization], tool_ledgers=[ledger])


def test_working_memory_requires_memory_governor_before_write(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="missing_governor_decision"):
        write_working_memory(tmp_path, kind="test", focus="no write", status="blocked")

    assert not (memory_root(tmp_path) / "working.json").exists()


def test_memory_write_constants_match_domain_chip_memory_contract() -> None:
    assert MEMORY_WRITE_TOOL_NAME == "domain-chip-memory.memory.write"
    assert MEMORY_WRITE_CAPABILITY_ID == "capability:domain-chip-memory:memory.write"
    assert MEMORY_WRITE_ACTION_TYPE == "memory.write"


def test_working_memory_rejects_stale_memory_governor_binding(tmp_path: Path) -> None:
    stale = memory_governor_decision(("spark-researcher.memory.working:other-runtime",))

    with pytest.raises(RuntimeError, match="authority_binding_missing"):
        write_working_memory(
            tmp_path,
            kind="test",
            focus="stale authority",
            status="blocked",
            governor_decision=stale,
        )

    assert not (memory_root(tmp_path) / "working.json").exists()


def test_working_memory_accepts_bound_memory_governor(tmp_path: Path) -> None:
    payload = write_working_memory(
        tmp_path,
        kind="test",
        focus="bound authority",
        status="accepted",
        governor_decision=memory_governor_decision(working_memory_authority_refs(tmp_path)),
    )

    assert payload["focus"] == "bound authority"
    assert (memory_root(tmp_path) / "working.json").exists()


def test_working_memory_rejects_unmarked_local_governor_shape(tmp_path: Path) -> None:
    decision = memory_governor_decision(working_memory_authority_refs(tmp_path))
    decision["evidence"] = [
        item
        for item in decision["evidence"]
        if item.get("source") != "issuer:spark-harness-core/governor"
    ]

    assert governor_decision_has_canonical_binding(decision) is False
    with pytest.raises(RuntimeError, match="canonical_governor_binding_missing"):
        write_working_memory(
            tmp_path,
            kind="test",
            focus="unmarked authority",
            status="blocked",
            governor_decision=decision,
        )

    assert not (memory_root(tmp_path) / "working.json").exists()


def test_episode_requires_memory_governor_before_write(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="missing_governor_decision"):
        record_episode(tmp_path, kind="test", title="No write", summary="blocked", status="blocked")

    assert not (memory_root(tmp_path) / "episodes.jsonl").exists()


def test_sync_memory_requires_memory_governor_before_materialization(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    config_path = _write_config(repo_root)
    _write_ledger(runtime_root)

    with pytest.raises(RuntimeError, match="missing_governor_decision"):
        sync_memory(repo_root, runtime_root, goal="maximize", config_path=config_path)

    assert not (memory_root(runtime_root) / "documents").exists()


def test_sync_memory_rejects_non_memory_governor(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    config_path = _write_config(repo_root)
    _write_ledger(runtime_root)

    with pytest.raises(RuntimeError, match="governor_missing_matching_authorization"):
        sync_memory(
            repo_root,
            runtime_root,
            goal="maximize",
            config_path=config_path,
            governor_decision=_advisory_governor_decision(),
        )

    assert not (memory_root(runtime_root) / "documents").exists()


def test_sync_memory_rejects_stale_memory_governor_binding(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    config_path = _write_config(repo_root)
    _write_ledger(runtime_root)
    stale = memory_governor_decision(("spark-researcher.memory.sync:other-runtime",))

    with pytest.raises(RuntimeError, match="authority_binding_missing"):
        sync_memory(
            repo_root,
            runtime_root,
            goal="maximize",
            config_path=config_path,
            governor_decision=stale,
        )

    assert not (memory_root(runtime_root) / "documents").exists()


def test_sync_memory_rejects_copied_memory_governor_ledger(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    config_path = _write_config(repo_root)
    _write_ledger(runtime_root)
    decision = memory_governor_decision(sync_memory_authority_refs(repo_root, runtime_root, config_path))
    decision["tool_ledgers"][0]["action_id"] = "copied-action"

    with pytest.raises(RuntimeError, match="governor_missing_matching_tool_ledger"):
        sync_memory(
            repo_root,
            runtime_root,
            goal="maximize",
            config_path=config_path,
            governor_decision=decision,
        )

    assert not (memory_root(runtime_root) / "documents").exists()


def test_beliefs_and_obsidian_require_memory_governor(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    config_path = _write_config(repo_root)
    _write_ledger(runtime_root)

    with pytest.raises(RuntimeError, match="missing_governor_decision"):
        build_beliefs(repo_root, runtime_root)
    with pytest.raises(RuntimeError, match="missing_governor_decision"):
        build_vault(repo_root, runtime_root, load_config(config_path), config_path=config_path)

    assert not (runtime_root / "artifacts" / "beliefs").exists()
    assert not vault_root(runtime_root).exists()


def test_read_paths_do_not_materialize_memory_without_governor(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    config_path = _write_config(repo_root)
    _write_ledger(runtime_root)

    assert search_memory(repo_root, runtime_root, "authority", goal="maximize", config_path=config_path) == []
    assert packet_status(config_path)["packet_count"] == 0

    assert not (memory_root(runtime_root) / "documents").exists()
    assert not (memory_root(runtime_root) / "manifest.json").exists()
    config_runtime_root = resolve_runtime_root(config_path)
    assert not (memory_root(config_runtime_root) / "documents").exists()
    assert not (memory_root(config_runtime_root) / "manifest.json").exists()


def test_advisory_build_does_not_write_working_memory_without_governor(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    config_path = _write_config(repo_root)
    runtime_root = resolve_runtime_root(config_path)

    advisory = build_advisory(config_path, "draft guidance about authority", model="generic")

    assert advisory["task"] == "draft guidance about authority"
    assert not (memory_root(runtime_root) / "working.json").exists()


def test_sync_memory_accepts_memory_governor(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    config_path = _write_config(repo_root)
    _write_ledger(runtime_root)

    manifest = sync_memory(
        repo_root,
        runtime_root,
        goal="maximize",
        config_path=config_path,
        governor_decision=memory_governor_decision(sync_memory_authority_refs(repo_root, runtime_root, config_path)),
    )

    assert manifest["document_count"] >= 1
    assert (memory_root(runtime_root) / "documents" / "INDEX.md").exists()
