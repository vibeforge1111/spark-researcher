from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("args", "expected_config_path"),
    [
        (["run", "--config", "missing.json", "--command", "train"], "missing.json"),
        (["memory", "status", "--config", "missing.json"], "missing.json"),
        (["summary"], "spark-researcher.project.json"),
    ],
)
def test_missing_config_returns_structured_guidance_without_traceback(
    tmp_path: Path,
    args: list[str],
    expected_config_path: str,
) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-m", "spark_researcher.cli", *args],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    combined_output = result.stdout + result.stderr
    assert result.returncode == 1
    assert "Traceback" not in combined_output
    assert result.stderr == ""

    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error_code"] == "config_file_not_found"
    assert payload["config_path"] == expected_config_path
    assert payload["error"] == "Config file not found."
    assert "spark-researcher init" in payload["next_action"]


def test_missing_external_config_does_not_leak_private_path_or_secret_like_material(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    private_parent = tmp_path.parent / "private-home-token-secret"
    private_config = private_parent / "sk-live-secret-project.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "spark_researcher.cli",
            "run",
            "--config",
            str(private_config),
            "--command",
            "train",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    combined_output = result.stdout + result.stderr
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert result.stderr == ""
    assert payload["ok"] is False
    assert payload["error_code"] == "config_file_not_found"
    assert payload["error"] == "Config file not found."
    assert payload["config_path"] == "<external-config>"
    assert "Traceback" not in combined_output
    assert "sk-live-secret" not in combined_output
    assert str(private_parent) not in combined_output
    assert str(private_config) not in combined_output


@pytest.mark.parametrize(
    "args",
    [
        ["advisory", "adapters"],
        ["optimizer", "status"],
        ["line-budget", "--repo-root", "."],
        ["self-edit", "profiles"],
    ],
)
def test_config_free_commands_still_work_without_project_file(tmp_path: Path, args: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-m", "spark_researcher.cli", *args],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Config file not found" not in result.stdout
    assert result.stderr == ""
