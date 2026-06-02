from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from spark_researcher.adapters import exec as exec_module


def _fake_completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["fake"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_execute_advisory_when_response_file_missing_uses_stdout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Race scenario: the subprocess returned cleanly but the response_path was never written
    (or was removed before we could read it). Pre-patch this exercised the
    `if response_path.exists(): ... else: raw_response = result.stdout.strip()` branch via the
    LBYL probe. Post-patch we go through `try: read_text() except FileNotFoundError: ...` which
    is single-syscall atomic and closes the race window between exists() and read_text()."""
    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        return _fake_completed(stdout="raw stdout from subprocess", stderr="", returncode=0)

    monkeypatch.setattr(exec_module.subprocess, "run", fake_run)
    monkeypatch.setattr(exec_module, "_resolve_command", lambda model, override: ["fake", "{request_path}"])

    advisory = {
        "trace_id": "trace-1",
        "adapter_request": {"system_prompt": "sys", "user_prompt": "usr", "schema_hint": {}},
    }
    result = exec_module.execute_advisory(tmp_path, advisory=advisory, model="codex")
    assert result["response"] == {"raw_response": "raw stdout from subprocess"}
    assert result["returncode"] == 0


def test_execute_advisory_when_response_file_holds_invalid_json_uses_raw_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Happy-path regression on the JSONDecodeError fallback: when response_path exists but
    its content is not valid JSON, response_payload still falls back to the raw text. Post-patch
    we read the text once (not twice) -- the second read_text() in the pre-patch JSONDecodeError
    handler was itself racy. We assert the fallback still surfaces the raw text payload."""
    raw_body = "not-json"

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        # Write the response file from inside the fake run so the post-subprocess read finds it.
        for arg in cmd:
            if arg.endswith(".response.json"):
                Path(arg).write_text(raw_body, encoding="utf-8")
        return _fake_completed(stdout="stdout-ignored", stderr="", returncode=0)

    monkeypatch.setattr(exec_module.subprocess, "run", fake_run)
    monkeypatch.setattr(exec_module, "_resolve_command", lambda model, override: ["fake", "{response_path}"])

    advisory = {
        "trace_id": "trace-2",
        "adapter_request": {"system_prompt": "sys", "user_prompt": "usr", "schema_hint": {}},
    }
    result = exec_module.execute_advisory(tmp_path, advisory=advisory, model="codex")
    assert result["response"] == {"raw_response": raw_body}


def test_execute_advisory_when_response_file_holds_valid_json_parses_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Happy-path regression: valid JSON response_path content is parsed by json.loads."""
    payload = {"answer": 42, "ok": True}

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        for arg in cmd:
            if arg.endswith(".response.json"):
                Path(arg).write_text(json.dumps(payload), encoding="utf-8")
        return _fake_completed(stdout="ignored", stderr="", returncode=0)

    monkeypatch.setattr(exec_module.subprocess, "run", fake_run)
    monkeypatch.setattr(exec_module, "_resolve_command", lambda model, override: ["fake", "{response_path}"])

    advisory = {
        "trace_id": "trace-3",
        "adapter_request": {"system_prompt": "sys", "user_prompt": "usr", "schema_hint": {}},
    }
    result = exec_module.execute_advisory(tmp_path, advisory=advisory, model="codex")
    assert result["response"] == payload
