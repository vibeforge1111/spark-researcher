from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import spark_researcher.collective as collective_module
from collective_governor import (
    collective_absorb_governor_decision,
    collective_publish_governor_decision,
    collective_sync_governor_decision,
)
from spark_researcher.collective import absorb, publish_latest, sync_local_collective
from spark_researcher.paths import capsule_root, ledger_path


def _write_ledger_row(runtime_root: Path) -> None:
    row = {
        "run_id": "20260319-train",
        "created_at": "2026-03-19T12:00:00+00:00",
        "command_name": "train",
        "status": "ok",
        "metric_name": "score",
        "metric_value": 1.25,
        "baseline_value": 1.0,
        "verdict": "improved",
        "candidate_id": "baseline",
        "project_name": "toy-project",
    }
    ledger = ledger_path(runtime_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")


def _write_collective_index(repo_root: Path, source_repo: str) -> Path:
    collective_root = repo_root.parent / "autoresearch-collective"
    index_path = collective_root / "dashboard" / "public" / "data" / "collective.generated.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "repoDirectory": [{"repo": source_repo, "platform": "cpu"}],
                "capsuleLibrary": [
                    {
                        "id": "insight-1",
                        "repo": source_repo,
                        "verdict": "improved",
                        "title": "Improved score",
                        "summary": "Better training lane",
                        "metricName": "score",
                        "metricValue": 1.25,
                        "baselineValue": 1.0,
                        "delta": 0.25,
                        "createdAt": "2026-03-19T12:00:00+00:00",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return collective_root


def test_publish_latest_requires_governor_before_capsule_write(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_ledger_row(repo_root)

    with pytest.raises(RuntimeError, match="GovernorDecisionV1.*missing_governor_decision"):
        publish_latest(repo_root, repo_root)

    assert not capsule_root(repo_root).exists()


def test_publish_latest_rejects_governor_for_another_capability(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_ledger_row(repo_root)

    with pytest.raises(RuntimeError, match="governor_missing_matching_authorization"):
        publish_latest(repo_root, repo_root, governor_decision=collective_sync_governor_decision())

    assert not capsule_root(repo_root).exists()


def test_publish_latest_with_governed_decision_writes_capsule(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_ledger_row(repo_root)

    published = publish_latest(repo_root, repo_root, governor_decision=collective_publish_governor_decision())

    assert Path(published["markdown_path"]).exists()
    assert Path(published["manifest_path"]).exists()
    manifest = json.loads(Path(published["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["run_id"] == "20260319-train"
    assert manifest["verdict"] == "improved"


def test_sync_local_collective_requires_governor_before_config_write(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    collective_root = _write_collective_index(repo_root, "vibeforge1111/source-lab")
    config_path = collective_module._repo_sources_path(collective_root)

    with pytest.raises(RuntimeError, match="GovernorDecisionV1.*missing_governor_decision"):
        sync_local_collective(repo_root, tmp_path / "runtime")

    assert not config_path.exists()


def test_sync_local_collective_rejects_governor_for_another_capability(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    collective_root = _write_collective_index(repo_root, "vibeforge1111/source-lab")
    config_path = collective_module._repo_sources_path(collective_root)

    with pytest.raises(RuntimeError, match="governor_missing_matching_authorization"):
        sync_local_collective(repo_root, tmp_path / "runtime", governor_decision=collective_publish_governor_decision())

    assert not config_path.exists()


def test_sync_local_collective_with_governed_decision_registers_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    collective_root = _write_collective_index(repo_root, "vibeforge1111/source-lab")
    config_path = collective_module._repo_sources_path(collective_root)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="rebuilt\n", stderr="")

    monkeypatch.setattr(collective_module.subprocess, "run", fake_run)

    result = sync_local_collective(repo_root, tmp_path / "runtime", governor_decision=collective_sync_governor_decision())

    assert result["repo_registered"] is True
    assert config_path.exists()
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["sources"][0]["path"] == str(repo_root).replace("\\", "/")


def test_absorb_requires_governor_before_bundle_write(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    _write_collective_index(repo_root, "vibeforge1111/source-lab")

    with pytest.raises(RuntimeError, match="GovernorDecisionV1.*missing_governor_decision"):
        absorb(repo_root, runtime_root, source_repo="vibeforge1111/source-lab")

    assert not (runtime_root / "artifacts").exists()
    assert not (repo_root / ".autoresearch").exists()


def test_absorb_rejects_governor_for_another_capability(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    _write_collective_index(repo_root, "vibeforge1111/source-lab")

    with pytest.raises(RuntimeError, match="governor_missing_matching_authorization"):
        absorb(
            repo_root,
            runtime_root,
            source_repo="vibeforge1111/source-lab",
            governor_decision=collective_publish_governor_decision(),
        )

    assert not (runtime_root / "artifacts").exists()
    assert not (repo_root / ".autoresearch").exists()


def test_absorb_with_governed_decision_creates_review_pr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    _write_collective_index(repo_root, "vibeforge1111/source-lab")
    calls: list[list[str]] = []

    def fake_run_command(command: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        calls.append(list(command))
        stdout = ""
        if command[:2] == ["git", "-C"]:
            if "get-url" in command:
                stdout = "https://github.com/vibeforge1111/target-lab.git\n"
            elif "symbolic-ref" in command:
                stdout = "refs/remotes/origin/main\n"
        elif command[:3] == ["gh", "pr", "create"]:
            stdout = "https://github.com/vibeforge1111/target-lab/pull/7\n"
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(collective_module, "_run_command", fake_run_command)

    result = absorb(
        repo_root,
        runtime_root,
        source_repo="vibeforge1111/source-lab",
        governor_decision=collective_absorb_governor_decision(),
    )

    assert result["absorbed_count"] == 1
    assert Path(result["output_path"]).exists()
    assert result["pr_summary"]["mode"] == "draft_pr"
    assert result["pr_summary"]["target_repo"] == "vibeforge1111/target-lab"
    assert result["pr_summary"]["pr_url"] == "https://github.com/vibeforge1111/target-lab/pull/7"
    review_files = list((repo_root / ".autoresearch" / "absorbs").glob("*/absorbed-insights.json"))
    assert len(review_files) == 1
    assert any(command[:2] == ["gh", "pr"] and "--draft" in command for command in calls)
    assert any("push" in command for command in calls if command[:2] == ["git", "-C"])
