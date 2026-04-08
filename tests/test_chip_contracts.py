from __future__ import annotations

import json
from pathlib import Path

import pytest

from spark_researcher.chips import chip_validation, invoke_chip_hook, validate_manifest
from spark_researcher.config import ChipSpec, CommandSpec, MetricSpec, ProjectConfig, save_config


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
