from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

from memory_governor import memory_governor_decision
from spark_researcher.beliefs import build_beliefs
from spark_researcher.beliefs import beliefs_authority_refs
from spark_researcher.config import CommandSpec, MetricSpec, ProjectConfig, save_config
from spark_researcher import memory
from spark_researcher.memory import load_working_memory, sync_memory, sync_memory_authority_refs


def _write_config(repo_root: Path) -> Path:
    repo_root.mkdir(parents=True, exist_ok=True)
    config_path = repo_root / "spark-researcher.project.json"
    save_config(
        config_path,
        ProjectConfig(
            project_name="memory-test",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
            metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
        ),
    )
    return config_path


def test_build_beliefs_bounds_long_belief_filenames(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    _write_config(repo_root)
    ledger_path = runtime_root / "artifacts" / "ledger" / "runs.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    long_value = "trend-" + ("momentum-" * 24)
    rows = [
        {
            "run_id": "run-1",
            "project_name": "memory-test",
            "command_name": "research",
            "candidate_id": "candidate-a",
            "candidate_summary": "summary",
            "hypothesis": "hypothesis",
            "metric_name": "score",
            "metric_value": 12.0,
            "baseline_value": 10.0,
            "verdict": "improved",
            "applied_mutations": [{"name": "lane", "value": long_value}],
        },
        {
            "run_id": "run-2",
            "project_name": "memory-test",
            "command_name": "research",
            "candidate_id": "candidate-a",
            "candidate_summary": "summary",
            "hypothesis": "hypothesis",
            "metric_name": "score",
            "metric_value": 13.0,
            "baseline_value": 10.0,
            "verdict": "improved",
            "applied_mutations": [{"name": "lane", "value": long_value}],
        },
    ]
    ledger_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    manifest = build_beliefs(repo_root, runtime_root, governor_decision=memory_governor_decision(beliefs_authority_refs(repo_root, runtime_root)))

    belief = manifest["beliefs"][0]
    belief_path = Path(str(belief["path"]))
    assert belief_path.exists()
    assert belief_path.is_relative_to(runtime_root / "artifacts" / "beliefs")
    assert len(belief_path.stem) <= 80
    assert len(str(belief["belief_id"])) > len(belief_path.stem)


def test_sync_memory_dedupes_duplicate_chip_docs_and_bounds_paths(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    config_path = _write_config(repo_root)
    ledger_path = runtime_root / "artifacts" / "ledger" / "runs.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("", encoding="utf-8")

    long_slug = "benchmark-" + ("evidence-" * 24)

    monkeypatch.setattr("spark_researcher.memory.chip_has_hook", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "spark_researcher.memory.invoke_chip_hook",
        lambda *args, **kwargs: {
            "documents": [
                {
                    "kind": "startup_benchmark",
                    "title": "Benchmark Evidence",
                    "content": "# Evidence\nsame\n",
                    "slug": long_slug,
                    "memory_tier": "benchmark_evidence",
                },
                {
                    "kind": "startup_benchmark",
                    "title": "Benchmark Evidence",
                    "content": "# Evidence\nsame\n",
                    "slug": long_slug,
                    "memory_tier": "benchmark_evidence",
                },
                {
                    "kind": "startup_benchmark",
                    "title": "Benchmark Evidence Variant",
                    "content": "# Evidence\nvariant\n",
                    "slug": long_slug,
                    "memory_tier": "benchmark_evidence",
                },
            ]
        },
    )

    manifest = sync_memory(
        repo_root,
        runtime_root,
        goal="maximize",
        config_path=config_path,
        governor_decision=memory_governor_decision(sync_memory_authority_refs(repo_root, runtime_root, config_path)),
    )

    chip_documents = manifest["chip_documents"]
    assert len(chip_documents) == 2
    paths = [Path(str(item["path"])) for item in chip_documents]
    assert all(path.exists() for path in paths)
    assert len({str(path) for path in paths}) == 2
    assert all(len(path.stem) <= 82 for path in paths)


def test_load_working_memory_returns_empty_for_corrupt_json(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    working_path = runtime_root / "artifacts" / "memory" / "working-memory.json"
    working_path.parent.mkdir(parents=True)
    working_path.write_text("{not-json", encoding="utf-8")

    assert load_working_memory(runtime_root) == {}


def test_append_jsonl_uses_locked_file(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "runtime" / "artifacts" / "memory" / "episodes.jsonl"
    locked_paths: list[Path] = []

    @contextmanager
    def fake_locked_file(target: Path):
        locked_paths.append(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        yield

    monkeypatch.setattr(memory, "locked_file", fake_locked_file)

    memory._append_jsonl(path, {"event": "kept"})

    assert locked_paths == [path]
    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [{"event": "kept"}]
