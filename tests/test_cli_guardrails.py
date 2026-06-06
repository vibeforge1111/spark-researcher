from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import spark_researcher.cli as cli

ROOT = Path(__file__).resolve().parents[1]


def run_cli(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "spark_researcher.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_autoloop_rejects_non_positive_max_passes() -> None:
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["autoloop", "--command", "train", "--continuous", "--max-passes", "0"])


def test_run_rejects_unknown_candidate_id_before_baseline_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "spark-researcher.project.json"
    config_path.write_text("{}", encoding="utf-8")
    called_run_once = False

    monkeypatch.setattr(sys, "argv", ["spark-researcher", "run", "--config", str(config_path), "--command", "train", "--candidate-id", "missing"])
    monkeypatch.setattr(cli, "load_config", lambda path: object())
    monkeypatch.setattr(cli, "merged_candidate_trials", lambda path, *, config: [SimpleNamespace(candidate_id="known")])

    def fake_run_once(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal called_run_once
        called_run_once = True
        return {"ok": True}

    monkeypatch.setattr(cli, "run_once", fake_run_once)

    with pytest.raises(SystemExit, match="Candidate id 'missing' was not found"):
        cli.main()
    assert called_run_once is False


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
    result = run_cli(tmp_path, args)

    combined_output = result.stdout + result.stderr
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert result.stderr == ""
    assert payload["ok"] is False
    assert payload["error_code"] == "config_file_not_found"
    assert payload["error"] == "Config file not found."
    assert payload["config_path"] == expected_config_path
    assert "spark-researcher init" in payload["next_action"]
    assert "Traceback" not in combined_output
    assert "No such file or directory" not in combined_output


def test_missing_external_config_does_not_leak_private_path_or_secret_like_material(tmp_path: Path) -> None:
    private_parent = tmp_path.parent / "private-home-token-secret"
    private_config = private_parent / "sk-live-secret-project.json"
    result = run_cli(
        tmp_path,
        [
            "run",
            "--config",
            str(private_config),
            "--command",
            "train",
        ],
    )

    combined_output = result.stdout + result.stderr
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert result.stderr == ""
    assert payload["ok"] is False
    assert payload["error_code"] == "config_file_not_found"
    assert payload["config_path"] == "<external-config>"
    assert "Traceback" not in combined_output
    assert "sk-live-secret" not in combined_output
    assert str(private_parent) not in combined_output
    assert str(private_config) not in combined_output


def test_missing_relative_secret_like_config_path_is_redacted(tmp_path: Path) -> None:
    result = run_cli(
        tmp_path,
        [
            "run",
            "--config",
            "private-token-secret/sk-live-secret-project.json",
            "--command",
            "train",
        ],
    )

    combined_output = result.stdout + result.stderr
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["config_path"] == "<redacted-config-path>"
    assert "private-token-secret" not in combined_output
    assert "sk-live-secret" not in combined_output


@pytest.mark.parametrize(
    "args",
    [
        ["advisory", "adapters"],
        ["optimizer", "status"],
        ["line-budget", "--repo-root", "."],
        ["self-edit", "profiles"],
        ["self-edit", "status"],
        ["collective", "status"],
        ["failures"],
    ],
)
def test_config_free_commands_still_work_without_project_file(tmp_path: Path, args: list[str]) -> None:
    result = run_cli(tmp_path, args)

    assert result.returncode == 0
    assert "Config file not found" not in result.stdout
    assert result.stderr == ""
