from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from pathlib import Path

import pytest

from spark_researcher.chips import chip_validation, invoke_chip_hook, validate_manifest
from spark_researcher.config import ChipSpec, CommandSpec, MetricSpec, ProjectConfig, save_config


def test_chip_validation_unconfigured_output_omits_local_schema_path(tmp_path: Path) -> None:
    config_path = tmp_path / "spark-researcher.project.json"
    config_path.write_text(
        json.dumps(
            {
                "project_name": "no-chip",
                "project_root": ".",
                "eval_metric": "score",
                "eval_goal": "maximize",
                "commands": {"research": {"args": ["python", "-c", "print('noop')"]}},
                "metrics": {"score": {"pattern": r"^score:\s+([0-9.]+)$"}},
                "chip": {"path": "", "manifest": "spark-chip.json"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = chip_validation(config_path)

    assert result["configured"] is False
    assert result["valid"] is False
    assert "schema_path" not in result
    assert result["schema_version"] == "spark-chip.v1"
    assert result["io_protocol"] == "spark-hook-io.v1"


def test_validate_manifest_rejects_misplaced_frontier_keys(tmp_path: Path) -> None:
    manifest = {
        "schema_version": "spark-chip.v1",
        "io_protocol": "spark-hook-io.v1",
        "chip_name": "domain-chip-trading-crypto",
        "domain": "trading",
        "version": "0.1.0",
        "description": "Test chip",
        "capabilities": ["evaluate", "packets"],
        "commands": {
            "evaluate": ["python", "hook.py"],
            "packets": ["python", "hook.py"],
        },
        "allowed_mutations": {"lane": ["trend"]},
        "open_mutation_fields": ["lane"],
    }

    result = validate_manifest(manifest, tmp_path / "spark-chip.json")

    assert result["valid"] is False
    assert any("must live under the `frontier` object" in error for error in result["errors"])


def _write_chip_fixture(chip_root: Path, *, response_payload: dict) -> Path:
    chip_root.mkdir(parents=True, exist_ok=True)
    (chip_root / "response.json").write_text(json.dumps(response_payload), encoding="utf-8")
    (chip_root / "hook.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "import argparse",
                "import json",
                "from pathlib import Path",
                "",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--input', required=True)",
                "parser.add_argument('--output', required=True)",
                "args = parser.parse_args()",
                "payload = json.loads((Path(__file__).parent / 'response.json').read_text(encoding='utf-8'))",
                "Path(args.output).write_text(json.dumps(payload), encoding='utf-8')",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (chip_root / "spark-chip.json").write_text(
        json.dumps(
            {
                "schema_version": "spark-chip.v1",
                "io_protocol": "spark-hook-io.v1",
                "chip_name": "domain-chip-test",
                "domain": "testing",
                "version": "0.1.0",
                "description": "Test chip",
                "capabilities": ["packets"],
                "commands": {
                    "packets": ["python", "hook.py"],
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    config_path = chip_root / "spark-researcher.project.json"
    save_config(
        config_path,
        ProjectConfig(
            project_name="domain-chip-test",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
            metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
            chip=ChipSpec(path=".", manifest="spark-chip.json"),
        ),
    )
    return config_path


def _write_src_layout_chip_fixture(chip_root: Path, *, response_payload: dict) -> Path:
    package_root = chip_root / "src" / "domain_chip_test"
    package_root.mkdir(parents=True, exist_ok=True)
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    (chip_root / "response.json").write_text(json.dumps(response_payload), encoding="utf-8")
    (package_root / "cli.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "import argparse",
                "import json",
                "from pathlib import Path",
                "",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--input', required=True)",
                "parser.add_argument('--output', required=True)",
                "args = parser.parse_args()",
                "payload = json.loads((Path(__file__).resolve().parents[2] / 'response.json').read_text(encoding='utf-8'))",
                "Path(args.output).write_text(json.dumps(payload), encoding='utf-8')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (chip_root / "spark-chip.json").write_text(
        json.dumps(
            {
                "schema_version": "spark-chip.v1",
                "io_protocol": "spark-hook-io.v1",
                "chip_name": "domain-chip-test",
                "domain": "testing",
                "version": "0.1.0",
                "description": "Test chip",
                "capabilities": ["suggest"],
                "commands": {
                    "suggest": ["python", "-m", "domain_chip_test.cli"],
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    config_path = chip_root / "spark-researcher.project.json"
    save_config(
        config_path,
        ProjectConfig(
            project_name="domain-chip-test",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
            metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
            chip=ChipSpec(path=".", manifest="spark-chip.json"),
        ),
    )
    return config_path


def test_invoke_chip_hook_rejects_invalid_packet_documents(tmp_path: Path) -> None:
    config_path = _write_chip_fixture(
        tmp_path / "chip",
        response_payload={
            "documents": [
                {
                    "kind": "benchmark_evidence",
                    "content": "missing title should fail",
                }
            ]
        },
    )

    with pytest.raises(RuntimeError, match=r"documents\[0\]\.title"):
        invoke_chip_hook(config_path, "packets", {"ledger_rows": [], "outcomes": [], "documents_root": str(tmp_path / "docs")})


def test_invoke_chip_hook_accepts_well_formed_packet_documents(tmp_path: Path) -> None:
    config_path = _write_chip_fixture(
        tmp_path / "chip",
        response_payload={
            "documents": [
                {
                    "kind": "benchmark_evidence",
                    "title": "Benchmark packet",
                    "content": "# Benchmark packet",
                    "slug": "benchmark-packet",
                    "memory_tier": "benchmark_evidence",
                }
            ]
        },
    )

    response = invoke_chip_hook(config_path, "packets", {"ledger_rows": [], "outcomes": [], "documents_root": str(tmp_path / "docs")})

    assert response["documents"][0]["title"] == "Benchmark packet"


def test_invoke_chip_hook_missing_hook_lists_defined_hooks(tmp_path: Path) -> None:
    config_path = _write_chip_fixture(
        tmp_path / "chip",
        response_payload={
            "documents": [
                {
                    "kind": "benchmark_evidence",
                    "title": "Unused",
                    "content": "# Unused",
                }
            ]
        },
    )

    with pytest.raises(RuntimeError) as error:
        invoke_chip_hook(config_path, "suggest", {"limit": 1})

    message = str(error.value)
    assert "Chip hook `suggest` is not defined" in message
    assert "Defined hooks: `packets`." in message


def test_invoke_chip_hook_supports_src_layout_module_commands(tmp_path: Path) -> None:
    config_path = _write_src_layout_chip_fixture(
        tmp_path / "chip",
        response_payload={
            "suggestions": [
                {
                    "candidate_id": "trend-ema-btceth-4h",
                    "mutations": {"strategy_id": "ema_pullback_long"},
                }
            ]
        },
    )

    response = invoke_chip_hook(config_path, "suggest", {"limit": 1, "command_name": "research"})

    assert response["suggestions"][0]["candidate_id"] == "trend-ema-btceth-4h"


def test_invoke_chip_hook_uses_bounded_utf8_subprocess(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = _write_chip_fixture(
        tmp_path / "chip",
        response_payload={
            "documents": [
                {
                    "kind": "benchmark_evidence",
                    "title": "Bounded hook",
                    "content": "# Bounded hook",
                    "slug": "bounded-hook",
                    "memory_tier": "benchmark_evidence",
                }
            ]
        },
    )
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured["command"] = command
        captured["kwargs"] = kwargs
        output_path = Path(command[-1])
        output_path.write_text(
            json.dumps(
                {
                    "documents": [
                        {
                            "kind": "benchmark_evidence",
                            "title": "Bounded hook",
                            "content": "# Bounded hook",
                            "slug": "bounded-hook",
                            "memory_tier": "benchmark_evidence",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    response = invoke_chip_hook(config_path, "packets", {"ledger_rows": [], "outcomes": [], "documents_root": str(tmp_path / "docs")})

    assert response["documents"][0]["title"] == "Bounded hook"
    assert captured["kwargs"]["timeout"] == 300
    assert captured["kwargs"]["encoding"] == "utf-8"
    assert captured["kwargs"]["errors"] == "replace"


def test_invoke_chip_hook_failure_returns_public_safe_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = _write_chip_fixture(
        tmp_path / "chip",
        response_payload={
            "documents": [
                {
                    "kind": "benchmark_evidence",
                    "title": "Unused",
                    "content": "# Unused",
                }
            ]
        },
    )

    def fake_run(_command: list[str], **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=2, stdout="token=abc123", stderr="secret=should-not-appear")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as error:
        invoke_chip_hook(
            config_path,
            "packets",
            {"ledger_rows": [], "outcomes": [], "documents_root": str(tmp_path / "docs")},
        )

    message = str(error.value)
    assert "exit code 2" in message
    assert "local chip hook log" in message
    assert "secret=should-not-appear" not in message
    assert "token=abc123" not in message


def test_invoke_chip_hook_timeout_returns_public_safe_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = _write_chip_fixture(
        tmp_path / "chip",
        response_payload={
            "documents": [
                {
                    "kind": "benchmark_evidence",
                    "title": "Unused",
                    "content": "# Unused",
                }
            ]
        },
    )

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        raise subprocess.TimeoutExpired(command, timeout=300, output="token=abc123", stderr="secret=hidden")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as error:
        invoke_chip_hook(
            config_path,
            "packets",
            {"ledger_rows": [], "outcomes": [], "documents_root": str(tmp_path / "docs")},
        )

    message = str(error.value)
    assert "timed out after 300s" in message
    assert "token=abc123" not in message
    assert "secret=hidden" not in message


def test_chip_validation_rejects_missing_local_hook_paths(tmp_path: Path) -> None:
    chip_root = tmp_path / "chip"
    chip_root.mkdir(parents=True, exist_ok=True)
    (chip_root / "spark-chip.json").write_text(
        json.dumps(
            {
                "schema_version": "spark-chip.v1",
                "io_protocol": "spark-hook-io.v1",
                "chip_name": "domain-chip-test",
                "domain": "testing",
                "version": "0.1.0",
                "description": "Test chip",
                "capabilities": ["evaluate"],
                "commands": {
                    "evaluate": ["python", "missing_hook.py"],
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    config_path = chip_root / "spark-researcher.project.json"
    save_config(
        config_path,
        ProjectConfig(
            project_name="domain-chip-test",
            project_root=".",
            eval_metric="score",
            eval_goal="maximize",
            commands={"research": CommandSpec(args=["python", "-c", "print('noop')"])},
            metrics={"score": MetricSpec(pattern=r"^score:\s+([0-9.]+)$")},
            chip=ChipSpec(path=".", manifest="spark-chip.json"),
        ),
    )

    result = chip_validation(config_path)

    assert result["valid"] is False
    assert any("missing local path" in error for error in result["errors"])


def test_chip_validation_warns_about_unexcluded_local_state_dirs(tmp_path: Path) -> None:
    config_path = _write_chip_fixture(tmp_path / "chip", response_payload={"documents": []})
    local_state = tmp_path / "chip" / "localhost" / "paperclip-control-plane" / ".paperclip-data"
    local_state.mkdir(parents=True)

    result = chip_validation(config_path)

    assert result["valid"] is True
    assert any(".paperclip-data" in warning for warning in result["warnings"])
