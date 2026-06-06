from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


def preset_names() -> list[str]:
    return ["coding", "research", "content", "toy"]


def _base_payload(project_name: str, project_root: str, eval_metric: str, eval_goal: str) -> dict[str, object]:
    return {
        "project_name": project_name,
        "project_root": project_root,
        "eval_metric": eval_metric,
        "eval_goal": eval_goal,
        "commands": {
            "train": {
                "args": ["python", "train.py"],
                "cwd": ".",
                "kind": "train-once",
                "log_name": "train.log",
            }
        },
        "metrics": {
            eval_metric: {"pattern": rf"^{eval_metric}:\s+([0-9.]+)$", "kind": "float"},
            "training_seconds": {"pattern": r"^training_seconds:\s+([0-9.]+)$", "kind": "float"},
        },
        "mutable_parameters": [],
        "candidate_trials": [
            {
                "candidate_id": "baseline",
                "candidate_summary": "Run the current config without mutation.",
                "hypothesis": "The baseline defines the current local floor.",
                "mutations": {},
            }
        ],
        "trainers": [
            {
                "name": "default-compiler",
                "examples_path": "training_examples.jsonl",
                "compile_command": ["python", "trainer.py"],
                "min_examples": 3,
                "recompile_every": 2,
                "max_examples": 200,
            }
        ],
        "mutable_targets": [
            "src",
            "docs",
            "README.md",
            "pyproject.toml",
        ],
        "memory": {
            "backend": "local",
        },
        "self_edit": {
            "command": [],
            "mutable_targets": [
                "src",
                "docs",
                "README.md",
                "pyproject.toml",
            ],
            "prompt_preamble": "Keep the repo lightweight, transparent, and review-first.",
        },
        "guardrails": {
            "max_loop_iterations": 8,
            "consecutive_discard_limit": 3,
            "require_clean_git_for_self_edit": True,
            "require_human_approval_for_self_edit": True,
            "blocked_command_fragments": ["shutdown", "format", "reg delete", "Remove-Item", "del /f", "rm -rf"],
        },
    }


def build_preset(preset: str, project_name: str, project_root: str) -> dict[str, object]:
    key = preset.strip().lower()
    if key == "coding":
        payload = _base_payload(project_name, project_root, "test_score", "maximize")
        payload["commands"]["train"]["args"] = ["python", "run_eval.py"]
        payload["commands"]["train"]["log_name"] = "eval.log"
        payload["metrics"] = {
            "test_score": {"pattern": r"^test_score:\s+([0-9.]+)$", "kind": "float"},
            "training_seconds": {"pattern": r"^training_seconds:\s+([0-9.]+)$", "kind": "float"},
        }
        payload["candidate_trials"] = [
            {
                "candidate_id": "baseline",
                "candidate_summary": "Run the current coding evaluation path.",
                "hypothesis": "The current implementation defines the working baseline.",
                "mutations": {},
            }
        ]
        return payload
    if key == "research":
        payload = _base_payload(project_name, project_root, "val_loss", "minimize")
        payload["candidate_trials"] = [
            {
                "candidate_id": "baseline",
                "candidate_summary": "Run the current experiment config.",
                "hypothesis": "The current experiment config defines the local floor.",
                "mutations": {},
            }
        ]
        return payload
    if key == "content":
        payload = _base_payload(project_name, project_root, "quality_score", "maximize")
        payload["commands"]["train"]["args"] = ["python", "score_content.py"]
        payload["commands"]["train"]["log_name"] = "content.log"
        payload["metrics"] = {
            "quality_score": {"pattern": r"^quality_score:\s+([0-9.]+)$", "kind": "float"},
            "training_seconds": {"pattern": r"^training_seconds:\s+([0-9.]+)$", "kind": "float"},
        }
        payload["candidate_trials"] = [
            {
                "candidate_id": "baseline",
                "candidate_summary": "Run the current content scoring path.",
                "hypothesis": "The current prompt/system defines the working baseline.",
                "mutations": {},
            }
        ]
        return payload
    if key == "toy":
        payload = _base_payload(project_name, project_root, "val_loss", "minimize")
        payload["candidate_trials"] = [
            {
                "candidate_id": "baseline",
                "candidate_summary": "Run the current config without mutation.",
                "hypothesis": "The baseline defines the current local floor.",
                "mutations": {},
            },
            {
                "candidate_id": "lr-0003",
                "candidate_summary": "Move learning rate toward the known optimum.",
                "hypothesis": "A lower learning rate should improve val_loss.",
                "mutations": {"learning_rate": "0.0003"},
            },
            {
                "candidate_id": "wd-002",
                "candidate_summary": "Move weight decay toward the known optimum.",
                "hypothesis": "A slightly higher weight decay should improve val_loss.",
                "mutations": {"weight_decay": "0.02"},
            },
        ]
        payload["mutable_parameters"] = [
            {
                "name": "learning_rate",
                "file": "config.json",
                "pattern": "\"learning_rate\":\\s*[0-9.]+",
                "template": "\"learning_rate\": {value}",
                "description": "Local file-based learning-rate mutation.",
                "value_step": "0.0001",
                "value_range": ["0.0001", "0.0005"],
            },
            {
                "name": "weight_decay",
                "file": "config.json",
                "pattern": "\"weight_decay\":\\s*[0-9.]+",
                "template": "\"weight_decay\": {value}",
                "description": "Local file-based weight-decay mutation.",
                "value_step": "0.01",
                "value_range": ["0.01", "0.03"],
            },
        ]
        payload["trainers"] = [
            {
                "name": "toy-compiler",
                "examples_path": "training_examples.jsonl",
                "compile_command": ["python", "trainer.py"],
                "min_examples": 3,
                "recompile_every": 2,
                "max_examples": 200,
            }
        ]
        payload["mutable_targets"] = [
            "train.py",
            "trainer.py",
            "config.json",
            "training_examples.jsonl",
            "spark-researcher.project.json",
        ]
        payload["self_edit"] = {
            "command": [],
            "mutable_targets": list(payload["mutable_targets"]),
            "prompt_preamble": "Keep the project lightweight, transparent, and review-first.",
        }
        return payload
    raise RuntimeError(f"Unknown preset: {preset!r}. Known presets: coding, research, content, toy.")


def _preset_readme(preset: str, project_name: str) -> str:
    key = preset.strip().lower()
    if key == "toy":
        return dedent(
            f"""\
            # {project_name}

            Preset: `toy`

            This preset is runnable immediately.

            From this directory:

            - run `spark-researcher run --command train --config spark-researcher.project.json`
            - run `spark-researcher autoloop --command train --rounds 3 --suggest-limit 3 --config spark-researcher.project.json`
            - run `spark-researcher memory sync --config spark-researcher.project.json`
            - run `spark-researcher obsidian build --config spark-researcher.project.json`

            What to expect:

            - lower `val_loss` is better
            - the optimum is near `learning_rate=0.0003`
            - the optimum is also near `weight_decay=0.02`
            """
        )
    return dedent(
        f"""\
        # {project_name}

        Preset: `{preset}`

        Next steps:

        - replace the command args with the real project entrypoint
        - tighten mutable targets before enabling self-edit
        - add candidate trials with one mutation per hypothesis
        - run `spark-researcher run --command train --config spark-researcher.project.json`
        """
    )


def _write_toy_files(target_dir: Path) -> None:
    (target_dir / "train.py").write_text(
        dedent(
            """\
            from __future__ import annotations

            import json
            from pathlib import Path


            def main() -> None:
                config = json.loads(Path("config.json").read_text(encoding="utf-8"))
                learning_rate = float(config["learning_rate"])
                weight_decay = float(config["weight_decay"])
                val_loss = 1.0 + ((learning_rate - 0.0003) ** 2) * 1000000 + abs(weight_decay - 0.02) * 5
                print(f"val_loss: {val_loss:.6f}")
                print("training_seconds: 5.0")


            if __name__ == "__main__":
                main()
            """
        ),
        encoding="utf-8",
    )
    (target_dir / "trainer.py").write_text(
        dedent(
            """\
            from __future__ import annotations

            import json
            from pathlib import Path


            def main() -> None:
                examples_path = Path("training_examples.jsonl")
                compiled_path = Path("compiled.json")
                count = 0
                if examples_path.exists():
                    count = sum(1 for line in examples_path.read_text(encoding="utf-8").splitlines() if line.strip())
                payload = {"compiled_examples": count, "status": "ok"}
                compiled_path.write_text(json.dumps(payload, indent=2) + "\\n", encoding="utf-8")
                print(f"compiled_examples: {count}")


            if __name__ == "__main__":
                main()
            """
        ),
        encoding="utf-8",
    )
    (target_dir / "config.json").write_text(
        json.dumps({"learning_rate": 0.001, "weight_decay": 0.01}, indent=2) + "\n",
        encoding="utf-8",
    )
    (target_dir / "training_examples.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"inputs": {"x": 1}, "outputs": {"y": 2}, "outcome": {"score": 1}}),
                json.dumps({"inputs": {"x": 2}, "outputs": {"y": 4}, "outcome": {"score": 1}}),
                json.dumps({"inputs": {"x": 3}, "outputs": {"y": 6}, "outcome": {"score": 1}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def init_project(target_dir: Path, *, preset: str, project_name: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    config_path = target_dir / "spark-researcher.project.json"
    if config_path.exists():
        raise FileExistsError(f"Config already exists: {config_path}")
    payload = build_preset(preset, project_name, ".")
    config_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if preset.strip().lower() == "toy":
        _write_toy_files(target_dir)
    readme_path = target_dir / "SPARK_RESEARCHER_PRESET.md"
    readme_path.write_text(_preset_readme(preset, project_name), encoding="utf-8")
    return config_path
