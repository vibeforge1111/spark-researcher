from __future__ import annotations

import os
from pathlib import Path

import pytest

from memory_governor import memory_governor_decision
from spark_researcher import obsidian
from spark_researcher.config import CommandSpec, MetricSpec, ProjectConfig
from spark_researcher.obsidian import vault_authority_refs
from spark_researcher.paths import vault_root


def _config() -> ProjectConfig:
    return ProjectConfig(
        project_name="demo",
        project_root=".",
        eval_metric="score",
        eval_goal="maximize",
        commands={"research": CommandSpec(args=["python", "-c", "print('ok')"])},
        metrics={"score": MetricSpec(pattern=r"score=(\d+)")},
    )


def test_copy_runtime_beliefs_tolerates_concurrent_stale_file_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_root = tmp_path / "runtime"
    source = runtime_root / "artifacts" / "beliefs"
    source.mkdir(parents=True)
    (source / "current.md").write_text("current\n", encoding="utf-8")
    output_root = tmp_path / "vault-beliefs"
    output_root.mkdir()
    stale = output_root / "stale.md"
    stale.write_text("stale\n", encoding="utf-8")
    original_unlink = Path.unlink

    def racing_unlink(path: Path, *args: object, **kwargs: object) -> None:
        if path == stale:
            original_unlink(path)
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", racing_unlink)

    written = obsidian.copy_runtime_beliefs(runtime_root, output_root)

    assert written == [str(output_root / "current.md")]
    assert not stale.exists()


def _build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pages: list[dict[str, str]],
    *,
    prepare_vault: object | None = None,
) -> tuple[dict[str, object], Path, Path]:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    config_path = repo_root / "spark-researcher.project.json"
    output_root = vault_root(runtime_root)
    if prepare_vault is not None:
        output_root.mkdir(parents=True)
        prepare_vault(output_root)

    monkeypatch.setattr(
        obsidian,
        "sync_memory",
        lambda *args, **kwargs: {"document_count": 0, "episode_count": 0, "kinds": {}, "outcomes": []},
    )
    monkeypatch.setattr(
        obsidian,
        "build_beliefs",
        lambda *args, **kwargs: {
            "belief_count": 0,
            "durable_belief_count": 0,
            "provisional_belief_count": 0,
            "contradiction_count": 0,
        },
    )
    monkeypatch.setattr(obsidian, "packet_status", lambda *args, **kwargs: {"packet_count": 0, "kinds": {}})
    monkeypatch.setattr(obsidian, "ledger_summary", lambda *args, **kwargs: {"run_count": 0, "best_by_metric": {}, "recent": []})
    monkeypatch.setattr(obsidian, "trace_status", lambda *args, **kwargs: {"research_signals": {}})
    monkeypatch.setattr(obsidian, "pending_queue_count", lambda *args, **kwargs: 0)
    monkeypatch.setattr(obsidian, "load_working_memory", lambda *args, **kwargs: {})
    monkeypatch.setattr(obsidian, "load_episode_memory", lambda *args, **kwargs: [])
    monkeypatch.setattr(obsidian, "chip_has_hook", lambda *args, **kwargs: True)
    monkeypatch.setattr(obsidian, "invoke_chip_hook", lambda *args, **kwargs: {"pages": pages})
    monkeypatch.setattr(obsidian, "copy_docs", lambda *args, **kwargs: [])
    monkeypatch.setattr(obsidian, "copy_runtime_beliefs", lambda *args, **kwargs: [])

    result = obsidian.build_vault(
        repo_root,
        runtime_root,
        _config(),
        config_path=config_path,
        governor_decision=memory_governor_decision(vault_authority_refs(repo_root, runtime_root, config_path)),
    )
    return result, runtime_root, output_root


def test_build_vault_rejects_parent_traversal_without_outside_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, runtime_root, _ = _build(
        tmp_path,
        monkeypatch,
        [{"path": "../escape.md", "content": "escaped"}],
    )

    assert not (runtime_root / "escape.md").exists()
    assert result["domain_page_count"] == 0


def test_build_vault_rejects_absolute_path_without_outside_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "absolute-escape.md"
    result, _, _ = _build(
        tmp_path,
        monkeypatch,
        [{"path": str(outside), "content": "escaped"}],
    )

    assert not outside.exists()
    assert result["domain_page_count"] == 0


def test_build_vault_rejects_sibling_prefix_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, runtime_root, _ = _build(
        tmp_path,
        monkeypatch,
        [{"path": "../obsidian-vault-escape/page.md", "content": "escaped"}],
    )

    assert not (runtime_root / "obsidian-vault-escape" / "page.md").exists()
    assert result["domain_page_count"] == 0


@pytest.mark.skipif(os.name != "posix", reason="symlink containment probe is POSIX-specific")
def test_build_vault_rejects_symlink_parent_without_outside_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()

    def prepare(output_root: Path) -> None:
        (output_root / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(RuntimeError, match="symbolic link"):
        _build(
            tmp_path,
            monkeypatch,
            [{"path": "linked/escape.md", "content": "escaped"}],
            prepare_vault=prepare,
        )

    assert not (outside / "escape.md").exists()


@pytest.mark.skipif(os.name != "posix", reason="symlink containment probe is POSIX-specific")
def test_build_vault_rejects_symlink_root_without_outside_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside-root"
    outside.mkdir()
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo_root.mkdir()
    runtime_root.mkdir()
    output_root = vault_root(runtime_root)
    output_root.symlink_to(outside, target_is_directory=True)
    config_path = repo_root / "spark-researcher.project.json"

    with pytest.raises(RuntimeError, match="symbolic link"):
        obsidian.build_vault(
            repo_root,
            runtime_root,
            _config(),
            config_path=config_path,
            governor_decision=memory_governor_decision(
                vault_authority_refs(repo_root, runtime_root, config_path)
            ),
        )

    assert list(outside.iterdir()) == []


def test_build_vault_writes_only_safe_pages_from_mixed_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, runtime_root, output_root = _build(
        tmp_path,
        monkeypatch,
        [
            {"path": "safe.md", "content": "safe"},
            {"path": "nested/also-safe.md", "content": "also safe"},
            {"path": "../escape.md", "content": "escaped"},
            {"path": "C:\\outside.md", "content": "windows escape"},
        ],
    )

    assert (output_root / "safe.md").read_text(encoding="utf-8") == "safe\n"
    assert (output_root / "nested" / "also-safe.md").read_text(encoding="utf-8") == "also safe\n"
    assert not (runtime_root / "escape.md").exists()
    assert not (output_root / "C:" / "outside.md").exists()
    assert result["domain_page_count"] == 2


def test_fallback_writer_rechecks_parent_containment_and_writes_atomically(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    root.mkdir()

    written = obsidian._write_vault_page_fallback(root, ("nested", "page.md"), "safe")

    assert written == root / "nested" / "page.md"
    assert written.read_text(encoding="utf-8") == "safe\n"
    assert not list((root / "nested").glob(".*.tmp"))

    if os.name == "posix":
        outside = tmp_path / "outside-fallback"
        outside.mkdir()
        (root / "linked-fallback").symlink_to(outside, target_is_directory=True)
        assert (
            obsidian._write_vault_page_fallback(
                root,
                ("linked-fallback", "escape.md"),
                "escaped",
            )
            is None
        )
        assert list(outside.iterdir()) == []
