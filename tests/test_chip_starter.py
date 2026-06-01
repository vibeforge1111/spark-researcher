from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import json

from spark_researcher import chip_starter


def test_normalize_chip_name_uses_domain_prefix_by_default() -> None:
    assert chip_starter.normalize_chip_name("marketing") == "domain-chip-marketing"


def test_normalize_chip_name_adds_prefix_for_custom_name() -> None:
    assert chip_starter.normalize_chip_name("marketing", "marketing") == "domain-chip-marketing"


def test_normalize_chip_name_preserves_existing_prefix() -> None:
    assert chip_starter.normalize_chip_name("marketing", "domain-chip-marketing") == "domain-chip-marketing"


def test_resolve_chip_target_defaults_to_desktop(monkeypatch, tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    monkeypatch.setattr(chip_starter, "_desktop_root", lambda: desktop)

    target = chip_starter.resolve_chip_target(None, "domain-chip-marketing")

    assert target == (desktop / "domain-chip-marketing").resolve()


def test_resolve_chip_target_puts_relative_paths_under_desktop(monkeypatch, tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    monkeypatch.setattr(chip_starter, "_desktop_root", lambda: desktop)

    target = chip_starter.resolve_chip_target(Path("marketing-explicit"), "domain-chip-marketing")

    assert target == (desktop / "marketing-explicit").resolve()


def test_init_chip_writes_readme_with_resolved_root(tmp_path: Path) -> None:
    chip_root = tmp_path / "domain-chip-marketing"

    result = chip_starter.init_chip(
        chip_root,
        chip_name="domain-chip-marketing",
        domain="marketing",
        metric_name="marketing_score",
    )

    readme = (chip_root / "README.md").read_text(encoding="utf-8")

    assert result["chip_root"] == str(chip_root.resolve())
    assert f"cd {chip_root.resolve()}" in readme
    assert result["chip_name"] == "domain-chip-marketing"
    assert result["next_steps"][0] == f"cd {chip_root.resolve()}"
    assert "git init" in result["next_steps"]
    assert any("chips validate --config" in step for step in result["next_steps"])
    assert "docs/CHIP_SYSTEMS.md" in readme
    assert "python -m pip install -e ..\\spark-researcher" in readme
    assert "$env:PYTHONPATH='..\\spark-researcher\\src;src'" in readme


def test_preset_readmes_reference_chip_systems_and_relative_spark_repo() -> None:
    crypto_readme = chip_starter._crypto_readme("domain-chip-trading-crypto", "domain_chip_trading_crypto", Path("..\\domain-chip-trading-crypto"))
    xcontent_readme = chip_starter._xcontent_readme("domain-chip-xcontent", "domain_chip_xcontent", Path("..\\domain-chip-xcontent"))

    assert "docs/CHIP_SYSTEMS.md" in crypto_readme
    assert "docs/CHIPS.md" in crypto_readme
    assert "python -m pip install -e ..\\spark-researcher" in crypto_readme
    assert "$env:PYTHONPATH='..\\spark-researcher\\src;src'" in crypto_readme

    assert "docs/CHIP_SYSTEMS.md" in xcontent_readme
    assert "docs/CHIPS.md" in xcontent_readme
    assert "python -m pip install -e ..\\spark-researcher" in xcontent_readme
    assert "$env:PYTHONPATH='..\\spark-researcher\\src;src'" in xcontent_readme


def test_xcontent_watchtower_handles_scalar_best_by_metric_values() -> None:
    namespace: dict[str, object] = {}
    exec(chip_starter._xcontent_cli("domain_chip_xcontent_test"), namespace)

    watchtower = namespace["watchtower"]
    assert callable(watchtower)

    response = watchtower(
        {
            "summary": {
                "run_count": 11,
                "best_by_metric": {
                    "engagement_quality_score": 0.95,
                    "grok_relevance_score": 0.678,
                },
            }
        }
    )

    assert isinstance(response, dict)
    pages = response["pages"]
    assert isinstance(pages, list)
    home = pages[0]["content"]
    assert "- best engagement_quality: `0.95`" in home
    assert "- best grok_relevance: `0.678`" in home


def test_init_chip_refuses_targets_inside_spark_repo(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "spark-researcher"
    repo_root.mkdir()
    monkeypatch.setattr(chip_starter, "_spark_repo_root", lambda: repo_root)

    blocked_target = repo_root / "domain-chip-marketing"

    try:
        chip_starter.init_chip(
            blocked_target,
            chip_name="domain-chip-marketing",
            domain="marketing",
            metric_name="marketing_score",
        )
    except ValueError as exc:
        assert "outside spark-researcher" in str(exc)
    else:
        raise AssertionError("Expected init_chip to refuse a target inside spark-researcher")


def test_cli_chips_init_refusal_is_clean() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    blocked_target = repo_root / "domain-chip-bad"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "spark_researcher.cli",
            "chips",
            "init",
            "--path",
            str(blocked_target),
            "--domain",
            "bad",
            "--metric-name",
            "bad_score",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "outside spark-researcher" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_chips_init_returns_standalone_bootstrap_steps(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "spark_researcher.cli",
            "chips",
            "init",
            "--path",
            str(tmp_path / "bootstrap-chip"),
            "--domain",
            "bootstrap",
            "--metric-name",
            "bootstrap_score",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["chip_name"] == "domain-chip-bootstrap"
    assert payload["chip_root"] == str((tmp_path / "bootstrap-chip").resolve())
    assert payload["next_steps"][0] == f"cd {(tmp_path / 'bootstrap-chip').resolve()}"
    assert "git init" in payload["next_steps"]
    assert any("chips validate --config" in step for step in payload["next_steps"])


def test_cli_unknown_candidate_id_is_user_friendly(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    config_path = repo_root / "spark-researcher.project.json"
    config_path.write_text(
        json.dumps(
            {
                "project_name": "demo",
                "project_root": ".",
                "eval_metric": "test_score",
                "eval_goal": "maximize",
                "commands": {
                    "train": {
                        "args": ["python", "-c", "print('test_score: 1')"],
                        "cwd": ".",
                        "kind": "train-once",
                        "log_name": "train.log",
                    }
                },
                "metrics": {"test_score": {"pattern": r"^test_score:\\s+([0-9.]+)$", "kind": "float"}},
                "mutable_parameters": [],
                "candidate_trials": [{"candidate_id": "baseline", "candidate_summary": "", "hypothesis": "", "mutations": {}}],
                "trainers": [],
                "mutable_targets": [],
                "memory": {"backend": "local"},
                "self_edit": {"command": [], "mutable_targets": [], "prompt_preamble": ""},
                "guardrails": {
                    "max_loop_iterations": 1,
                    "consecutive_discard_limit": 1,
                    "require_clean_git_for_self_edit": True,
                    "require_human_approval_for_self_edit": True,
                    "blocked_command_fragments": [],
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "spark_researcher.cli",
            "run",
            "--command",
            "train",
            "--candidate-id",
            "definitely-not-real",
            "--config",
            str(config_path),
            "--dry-run",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Unknown candidate_id" in result.stderr
    assert "candidates --command" in result.stderr
    assert "Traceback" not in result.stderr
