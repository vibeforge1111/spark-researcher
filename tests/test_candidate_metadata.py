from __future__ import annotations

import json
from pathlib import Path

from spark_researcher.candidates import append_suggestions, suggest_trials
from spark_researcher.config import ChipSpec, CommandSpec, MetricSpec, ProjectConfig, save_config
from spark_researcher.trial_queue import load_queue_trials


def _write_suggesting_chip_fixture(chip_root: Path, *, response_payload: dict) -> Path:
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


def test_suggest_trials_preserves_candidate_metadata(tmp_path: Path) -> None:
    config_path = _write_suggesting_chip_fixture(
        tmp_path / "chip",
        response_payload={
            "suggestions": [
                {
                    "candidate_id": "specialization-path-candidate",
                    "candidate_summary": "Preserve planner metadata.",
                    "hypothesis": "Bridge metadata should survive the runtime suggestion packet.",
                    "mutations": {
                        "candidate_content": "candidate-improves\n",
                    },
                    "metadata": {
                        "specialization_path": {
                            "selected_target_index": 1,
                            "selected_target_path": "prompts/startup-operator-secondary.md",
                            "selected_target_reason": "Secondary doctrine target",
                            "mutation_intent": {
                                "summary": "Tighten the secondary doctrine prompt without widening the mutation surface.",
                                "guardrails": [
                                    "Keep the edit scoped to the selected prompt file.",
                                    "Do not introduce new benchmark-facing rules.",
                                ],
                            },
                        }
                    },
                }
            ],
            "reasons": ["Preserve planner-owned targeting context."],
        },
    )

    packet = suggest_trials(config_path, "research", limit=1)

    assert packet["suggestion_count"] == 1
    assert packet["suggestions"][0]["metadata"] == {
        "specialization_path": {
            "selected_target_index": 1,
            "selected_target_path": "prompts/startup-operator-secondary.md",
            "selected_target_reason": "Secondary doctrine target",
            "mutation_intent": {
                "summary": "Tighten the secondary doctrine prompt without widening the mutation surface.",
                "guardrails": [
                    "Keep the edit scoped to the selected prompt file.",
                    "Do not introduce new benchmark-facing rules.",
                ],
            },
        }
    }


def test_append_suggestions_persists_candidate_metadata_to_queue(tmp_path: Path) -> None:
    config_path = _write_suggesting_chip_fixture(tmp_path / "chip", response_payload={"suggestions": []})

    result = append_suggestions(
        config_path,
        [
            {
                "candidate_id": "specialization-path-candidate",
                "candidate_summary": "Queue metadata",
                "hypothesis": "Queued metadata should survive round-tripping.",
                "mutations": {"candidate_content": "candidate-improves\n"},
                "metadata": {
                    "specialization_path": {
                        "selected_target_index": 0,
                        "selected_target_path": "prompts/startup-operator.md",
                        "selected_target_reason": "Primary doctrine target",
                        "mutation_intent": {
                            "summary": "Refine the governing doctrine prompt while preserving the existing benchmark loop.",
                            "guardrails": [
                                "Edit only the declared target.",
                                "Preserve benchmark compatibility.",
                            ],
                        },
                    }
                },
            }
        ],
        command_name="research",
    )

    assert result["appended_count"] == 1
    queue_trials = load_queue_trials(config_path)
    assert len(queue_trials) == 1
    assert queue_trials[0].metadata == {
        "specialization_path": {
            "selected_target_index": 0,
            "selected_target_path": "prompts/startup-operator.md",
            "selected_target_reason": "Primary doctrine target",
            "mutation_intent": {
                "summary": "Refine the governing doctrine prompt while preserving the existing benchmark loop.",
                "guardrails": [
                    "Edit only the declared target.",
                    "Preserve benchmark compatibility.",
                ],
            },
        }
    }
