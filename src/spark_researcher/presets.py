from __future__ import annotations

import json
from pathlib import Path


def preset_names() -> list[str]:
    return ["coding", "research", "content"]


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
            eval_metric: {"pattern": rf"^{eval_metric}:\\s+([0-9.]+)$", "kind": "float"},
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
    raise RuntimeError(f"Unknown preset: {preset}")


def init_project(target_dir: Path, *, preset: str, project_name: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    config_path = target_dir / "spark-researcher.project.json"
    if config_path.exists():
        raise FileExistsError(f"Config already exists: {config_path}")
    payload = build_preset(preset, project_name, ".")
    config_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme_path = target_dir / "SPARK_RESEARCHER_PRESET.md"
    readme_path.write_text(
        "\n".join(
            [
                f"# {project_name}",
                "",
                f"Preset: `{preset}`",
                "",
                "Next steps:",
                "",
                "- replace the command args with the real project entrypoint",
                "- tighten mutable targets before enabling self-edit",
                "- add candidate trials with one mutation per hypothesis",
                "- run `spark-researcher run --command train --config spark-researcher.project.json`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return config_path
