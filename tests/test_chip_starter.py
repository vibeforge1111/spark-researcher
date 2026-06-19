from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import json

for HARNESS_CORE_SRC in (
    Path(__file__).resolve().parents[2] / "spark-harness-core" / "src",
    Path.home() / ".spark" / "modules" / "spark-harness-core" / "source" / "src",
):
    if HARNESS_CORE_SRC.exists() and str(HARNESS_CORE_SRC) not in sys.path:
        sys.path.insert(0, str(HARNESS_CORE_SRC))
        break

from spark_harness_core import HarnessKernel, evidence_ref
from spark_researcher import chip_starter
from spark_researcher.authority import CHIP_CREATE_ACTION_TYPE, CHIP_CREATE_CAPABILITY_ID, CHIP_CREATE_TOOL_NAME
from spark_researcher.chips import validate_manifest


def _chip_create_governor_decision(chip_name: str = "domain-chip-marketing") -> dict:
    kernel = HarnessKernel(surface="cli")
    action = kernel.proposed_action(
        capability_id=CHIP_CREATE_CAPABILITY_ID,
        action_type=CHIP_CREATE_ACTION_TYPE,
        risk_tier="medium",
        summary=f"Create Spark Researcher domain chip scaffold {chip_name}.",
        args_path=f"chip:{chip_name}",
        requires_confirmation=True,
    )
    fresh_intent = evidence_ref(
        "fresh_user_intent",
        "test",
        f"Fresh owner request to create domain chip scaffold {chip_name}.",
        confidence=1.0,
    )
    approval = evidence_ref(
        "human_confirmation",
        "test",
        f"Owner approved chip scaffold creation for {chip_name}.",
        confidence=1.0,
    )
    envelope = kernel.create_envelope(
        selected_move="execute_action",
        intent_summary=f"Create domain chip scaffold {chip_name}.",
        raw_turn_summary=f"Owner explicitly requested Researcher chip scaffold {chip_name}.",
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
        tool_name=CHIP_CREATE_TOOL_NAME,
        status="not_started",
        output_path=f"chip:{chip_name}",
        summary=f"Researcher chip scaffold {chip_name} is authorized but not created.",
    )
    return kernel.governor_decision(
        envelope,
        authorizations=[authorization],
        tool_ledgers=[ledger],
        reply_style="compact_status",
        reply_instruction="Create the governed chip scaffold.",
    )


def _subprocess_env(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(repo_root / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path + (os.pathsep + existing if existing else "")
    return env


def test_normalize_chip_name_uses_domain_prefix_by_default() -> None:
    assert chip_starter.normalize_chip_name("marketing") == "domain-chip-marketing"


def test_normalize_chip_name_adds_prefix_for_custom_name() -> None:
    assert chip_starter.normalize_chip_name("marketing", "marketing") == "domain-chip-marketing"


def test_normalize_chip_name_preserves_existing_prefix() -> None:
    assert chip_starter.normalize_chip_name("marketing", "domain-chip-marketing") == "domain-chip-marketing"


def test_resolve_chip_target_defaults_to_spark_chip_parent(monkeypatch, tmp_path: Path) -> None:
    chip_parent = tmp_path / ".spark" / "chips"
    monkeypatch.setattr(chip_starter, "_default_chip_parent", lambda: chip_parent)

    target = chip_starter.resolve_chip_target(None, "domain-chip-marketing")

    assert target == (chip_parent / "domain-chip-marketing").resolve()


def test_resolve_chip_target_puts_relative_paths_under_spark_chip_parent(monkeypatch, tmp_path: Path) -> None:
    chip_parent = tmp_path / ".spark" / "chips"
    monkeypatch.setattr(chip_starter, "_default_chip_parent", lambda: chip_parent)

    target = chip_starter.resolve_chip_target(Path("marketing-explicit"), "domain-chip-marketing")

    assert target == (chip_parent / "marketing-explicit").resolve()


def test_init_chip_writes_readme_with_resolved_root(tmp_path: Path) -> None:
    chip_root = tmp_path / "domain-chip-marketing"

    result = chip_starter.init_chip(
        chip_root,
        chip_name="domain-chip-marketing",
        domain="marketing",
        metric_name="marketing_score",
        governor_decision=_chip_create_governor_decision(),
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
    assert result["authority"]["allowed"] is True
    assert result["authority"]["tool_name"] == CHIP_CREATE_TOOL_NAME


def test_init_chip_requires_governor_before_creating_target(tmp_path: Path) -> None:
    chip_root = tmp_path / "domain-chip-marketing"

    try:
        chip_starter.init_chip(
            chip_root,
            chip_name="domain-chip-marketing",
            domain="marketing",
            metric_name="marketing_score",
        )
    except RuntimeError as exc:
        assert "missing_governor_decision" in str(exc)
    else:
        raise AssertionError("Expected chip creation to require Governor authority")

    assert not chip_root.exists()


def test_init_chip_rejects_wrong_governor_before_creating_target(tmp_path: Path) -> None:
    chip_root = tmp_path / "domain-chip-marketing"
    governor_decision = _chip_create_governor_decision()
    governor_decision["tool_ledgers"][0]["tool_name"] = "researcher.chip.preview"

    try:
        chip_starter.init_chip(
            chip_root,
            chip_name="domain-chip-marketing",
            domain="marketing",
            metric_name="marketing_score",
            governor_decision=governor_decision,
        )
    except RuntimeError as exc:
        assert "governor_missing_matching_tool_ledger" in str(exc)
    else:
        raise AssertionError("Expected chip creation to reject non-matching Governor authority")

    assert not chip_root.exists()


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


def test_crypto_manifest_frontier_shape_validates(tmp_path: Path) -> None:
    manifest = json.loads(chip_starter._crypto_manifest("domain-chip-trading-crypto", "domain_chip_trading_crypto"))

    result = validate_manifest(manifest, tmp_path / "spark-chip.json")

    assert result["valid"] is True
    assert "frontier" in manifest
    assert "allowed_mutations" not in manifest
    assert "asset_universe" in manifest["frontier"]["allowed_mutations"]
    assert manifest["frontier"]["open_mutation_fields"] == ["asset_universe"]


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
        env=_subprocess_env(repo_root),
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "outside spark-researcher" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_chips_init_returns_standalone_bootstrap_steps(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    governor_path = tmp_path / "chip-create-governor.json"
    governor_path.write_text(
        json.dumps(_chip_create_governor_decision("domain-chip-bootstrap"), indent=2),
        encoding="utf-8",
    )

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
            "--governor-decision",
            str(governor_path),
        ],
        cwd=repo_root,
        env=_subprocess_env(repo_root),
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
    assert payload["authority"]["allowed"] is True
    assert payload["authority"]["tool_name"] == CHIP_CREATE_TOOL_NAME


def test_cli_chips_init_requires_governor_before_creating_target(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    chip_root = tmp_path / "bootstrap-chip"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "spark_researcher.cli",
            "chips",
            "init",
            "--path",
            str(chip_root),
            "--domain",
            "bootstrap",
            "--metric-name",
            "bootstrap_score",
        ],
        cwd=repo_root,
        env=_subprocess_env(repo_root),
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "missing_governor_decision" in result.stderr
    assert "Traceback" not in result.stderr
    assert not chip_root.exists()
