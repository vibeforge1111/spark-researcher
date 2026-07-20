from __future__ import annotations

import json
from pathlib import Path

from memory_governor import memory_governor_decision
from spark_researcher.beliefs import beliefs_authority_refs, build_beliefs
from spark_researcher.config import CommandSpec, MetricSpec, ProjectConfig, save_config


def _write_config(repo_root: Path) -> None:
    repo_root.mkdir(parents=True)
    save_config(
        repo_root / "spark-researcher.project.json",
        ProjectConfig(
            project_name="belief-resilience",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
            metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
        ),
    )


def _write_self_edit_pair(
    runtime_root: Path,
    proposal_id: str,
    *,
    proposal: str,
    review: str,
) -> None:
    root = runtime_root / "artifacts" / "self-edit" / proposal_id
    root.mkdir(parents=True)
    (root / "proposal.json").write_text(proposal, encoding="utf-8")
    (root / "review.json").write_text(review, encoding="utf-8")


def test_build_beliefs_skips_and_counts_corrupt_self_edit_artifacts(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    _write_config(repo_root)
    _write_self_edit_pair(
        runtime_root,
        "bad-proposal",
        proposal="PRIVATE_CORRUPT_PROPOSAL{",
        review=json.dumps({"decision": "approve"}),
    )
    _write_self_edit_pair(
        runtime_root,
        "bad-review",
        proposal=json.dumps({"proposal_id": "bad-review", "status": "pending_review"}),
        review="PRIVATE_CORRUPT_REVIEW{",
    )
    _write_self_edit_pair(
        runtime_root,
        "valid",
        proposal=json.dumps({"proposal_id": "valid", "status": "pending_review"}),
        review=json.dumps({"decision": "approve", "root_lesson": "keep valid evidence"}),
    )

    manifest = build_beliefs(
        repo_root,
        runtime_root,
        governor_decision=memory_governor_decision(beliefs_authority_refs(repo_root, runtime_root)),
    )

    assert manifest["belief_count"] == 1
    assert manifest["beliefs"][0]["belief_id"] == "self-edit-valid"
    assert manifest["invalid_self_edit_proposal_count"] == 1
    assert manifest["invalid_self_edit_review_count"] == 1
    assert manifest["invalid_self_edit_artifact_count"] == 2
    serialized = json.dumps(manifest, sort_keys=True)
    assert "PRIVATE_CORRUPT_PROPOSAL" not in serialized
    assert "PRIVATE_CORRUPT_REVIEW" not in serialized


def test_build_beliefs_treats_non_object_self_edit_json_as_invalid(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    _write_config(repo_root)
    _write_self_edit_pair(
        runtime_root,
        "array-proposal",
        proposal="[]",
        review=json.dumps({"decision": "approve"}),
    )

    manifest = build_beliefs(
        repo_root,
        runtime_root,
        governor_decision=memory_governor_decision(beliefs_authority_refs(repo_root, runtime_root)),
    )

    assert manifest["belief_count"] == 0
    assert manifest["invalid_self_edit_proposal_count"] == 1
    assert manifest["invalid_self_edit_review_count"] == 0
