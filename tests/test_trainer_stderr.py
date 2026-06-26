"""Regression test for trainer stderr redaction in trainers.run_trainer.

Exercises the real ``run_trainer`` path (not a re-implemented dict) to confirm
that absolute filesystem paths emitted on a failing trainer's stderr are
redacted before being persisted into the trainer state / result.
"""
from __future__ import annotations

import sys
from pathlib import Path

from spark_researcher.config import TrainerSpec
from spark_researcher.trainers import _redact_stderr_excerpt, run_trainer


def test_redact_stderr_excerpt_strips_absolute_paths() -> None:
    raw = "Traceback: error in /home/alice/.spark/secret/run.py line 3\nC:\\Users\\bob\\x"
    redacted = _redact_stderr_excerpt(raw)
    assert "/home/alice" not in redacted
    assert "C:\\Users\\bob" not in redacted
    assert "<path>" in redacted


def test_run_trainer_redacts_paths_from_failing_stderr(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    runtime_root = tmp_path / "runtime"
    project_root.mkdir()
    runtime_root.mkdir()

    examples = project_root / "examples.jsonl"
    examples.write_text('{"x": 1}\n', encoding="utf-8")

    secret = "/home/secret-operator/.spark/keys"
    # A compile command that writes an absolute path to stderr then fails.
    spec = TrainerSpec(
        name="probe",
        examples_path="examples.jsonl",
        compile_command=[
            sys.executable,
            "-c",
            f"import sys; sys.stderr.write('boom at {secret}/run.py'); sys.exit(1)",
        ],
        min_examples=1,
        recompile_every=1,
        max_examples=10,
    )

    result = run_trainer(spec, project_root, runtime_root)

    assert result["last_status"] == "failed"
    # The excerpt is retained (observability) but the absolute path is gone.
    assert "stderr_excerpt" in result
    assert secret not in result["stderr_excerpt"]
    assert "<path>" in result["stderr_excerpt"]
