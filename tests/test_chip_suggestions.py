from __future__ import annotations

import json
from pathlib import Path

from spark_researcher.candidates import suggest_trials
from spark_researcher.config import ChipSpec, CommandSpec, MetricSpec, ProjectConfig, save_config


def _write_reasoning_chip_fixture(chip_root: Path, *, response_payload: dict) -> Path:
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
                    "suggest": ["python", "hook.py"],
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


def test_suggest_trials_respects_chip_owned_zero_suggestion_guidance(monkeypatch, tmp_path: Path) -> None:
    config_path = _write_reasoning_chip_fixture(
        tmp_path / "chip",
        response_payload={
            "suggestions": [],
            "reasons": [
                "The queue is exhausted. Deepen source-grounded doctrine before generating more trials."
            ],
            "progression": {
                "state": "research_needed",
                "reason": "Need more doctrine coverage before new benchmark candidates.",
            },
        },
    )

    def fail_frontier(*args, **kwargs):
        raise AssertionError("frontier fallback should not run when the chip already returned next-step guidance")

    monkeypatch.setattr("spark_researcher.candidates.frontier_suggest", fail_frontier)

    packet = suggest_trials(config_path, "research", limit=3)

    assert packet["source"] == "chip"
    assert packet["suggestion_count"] == 0
    assert packet["reasons"] == [
        "The queue is exhausted. Deepen source-grounded doctrine before generating more trials."
    ]
    assert packet["progression"] == {
        "state": "research_needed",
        "reason": "Need more doctrine coverage before new benchmark candidates.",
    }
