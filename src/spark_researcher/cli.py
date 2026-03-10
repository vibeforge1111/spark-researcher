from __future__ import annotations

import argparse
import json
from pathlib import Path

from .beliefs import build_beliefs
from .collective import collective_status, publish_latest
from .collective import sync_local_collective
from .line_budget import build_line_budget
from .memory import memory_status, search_memory, sync_memory
from .obsidian import build_vault
from .paths import resolve_config_path, resolve_runtime_root
from .presets import init_project, preset_names
from .runner import ledger_summary, parse_overrides, run_loop, run_once
from .self_edit import apply_proposal, backend_profiles, proposal_status, propose, review_proposal
from .trainers import run_all_trainers, trainer_status


def print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def add_config_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default="spark-researcher.project.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="spark-researcher")
    sub = parser.add_subparsers(dest="action")

    init_parser = sub.add_parser("init")
    init_parser.add_argument("--path", required=True)
    init_parser.add_argument("--preset", choices=preset_names(), required=True)
    init_parser.add_argument("--project-name", required=True)

    run_parser = sub.add_parser("run")
    add_config_argument(run_parser)
    run_parser.add_argument("--command", dest="project_command", required=True)
    run_parser.add_argument("--candidate-id")
    run_parser.add_argument("--set", action="append")
    run_parser.add_argument("--dry-run", action="store_true")

    loop_parser = sub.add_parser("loop")
    add_config_argument(loop_parser)
    loop_parser.add_argument("--command", dest="project_command", required=True)
    loop_parser.add_argument("--limit", type=int)
    loop_parser.add_argument("--dry-run", action="store_true")

    trainer_parser = sub.add_parser("trainers")
    trainer_sub = trainer_parser.add_subparsers(dest="trainers_command")
    trainer_run = trainer_sub.add_parser("run")
    add_config_argument(trainer_run)
    trainer_run.add_argument("--dry-run", action="store_true")
    trainer_status_parser = trainer_sub.add_parser("status")
    add_config_argument(trainer_status_parser)

    memory_parser = sub.add_parser("memory")
    memory_sub = memory_parser.add_subparsers(dest="memory_command")
    memory_sync = memory_sub.add_parser("sync")
    add_config_argument(memory_sync)
    memory_search = memory_sub.add_parser("search")
    add_config_argument(memory_search)
    memory_search.add_argument("query")
    memory_search.add_argument("--limit", type=int, default=5)
    memory_status_parser = memory_sub.add_parser("status")
    add_config_argument(memory_status_parser)

    beliefs_parser = sub.add_parser("beliefs")
    beliefs_sub = beliefs_parser.add_subparsers(dest="beliefs_command")
    beliefs_build = beliefs_sub.add_parser("build")
    add_config_argument(beliefs_build)

    obsidian_parser = sub.add_parser("obsidian")
    obsidian_sub = obsidian_parser.add_subparsers(dest="obsidian_command")
    obsidian_build = obsidian_sub.add_parser("build")
    add_config_argument(obsidian_build)

    collective_parser = sub.add_parser("collective")
    collective_sub = collective_parser.add_subparsers(dest="collective_command")
    collective_publish = collective_sub.add_parser("publish")
    add_config_argument(collective_publish)
    collective_status_parser = collective_sub.add_parser("status")
    add_config_argument(collective_status_parser)
    collective_sync_parser = collective_sub.add_parser("sync-local")
    add_config_argument(collective_sync_parser)
    collective_sync_parser.add_argument("--label")
    collective_sync_parser.add_argument("--skip-rebuild", action="store_true")

    self_edit_parser = sub.add_parser("self-edit")
    self_edit_sub = self_edit_parser.add_subparsers(dest="self_edit_command")
    self_edit_propose = self_edit_sub.add_parser("propose")
    add_config_argument(self_edit_propose)
    self_edit_propose.add_argument("--prompt", required=True)
    self_edit_propose.add_argument("--backend-profile")
    self_edit_propose.add_argument("--backend-command", action="append")
    self_edit_propose.add_argument("--dry-run", action="store_true")
    self_edit_profiles = self_edit_sub.add_parser("profiles")
    self_edit_review = self_edit_sub.add_parser("review")
    add_config_argument(self_edit_review)
    self_edit_review.add_argument("--proposal-id", required=True)
    self_edit_review.add_argument("--decision", choices=["approve", "defer", "reject"], required=True)
    self_edit_review.add_argument("--root-lesson", required=True)
    self_edit_review.add_argument("--lineage-failure", action="append", default=[])
    self_edit_review.add_argument("--counterfactual", required=True)
    self_edit_review.add_argument("--ghost-check", required=True)
    self_edit_review.add_argument("--rollback-condition", required=True)
    self_edit_review.add_argument("--notes", default="")
    self_edit_apply = self_edit_sub.add_parser("apply")
    add_config_argument(self_edit_apply)
    self_edit_apply.add_argument("--proposal-id", required=True)
    self_edit_apply.add_argument("--git-mode", choices=["manual", "branch", "main"])
    self_edit_apply.add_argument("--push", action="store_true")
    self_edit_apply.add_argument("--no-push", action="store_true")
    self_edit_apply.add_argument("--branch-name")
    self_edit_apply.add_argument("--commit-message")
    self_edit_status = self_edit_sub.add_parser("status")
    add_config_argument(self_edit_status)

    summary_parser = sub.add_parser("summary")
    add_config_argument(summary_parser)

    budget_parser = sub.add_parser("line-budget")
    budget_parser.add_argument("--limit", type=int, default=6000)
    budget_parser.add_argument("--repo-root", default=".")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        return
    if args.action == "init":
        print_json({"config_path": str(init_project(Path(args.path).resolve(), preset=args.preset, project_name=args.project_name))})
        return
    if args.action == "line-budget":
        budget = build_line_budget(Path(args.repo_root).resolve())
        budget["limit"] = args.limit
        budget["within_limit"] = budget["total_lines"] <= args.limit
        print_json(budget)
        return
    config_path = resolve_config_path(getattr(args, "config", None))
    repo_root = config_path.parent.resolve()
    runtime_root = resolve_runtime_root(config_path)
    if args.action == "run":
        from .config import load_config

        config = load_config(config_path)
        trial = next((item for item in config.candidate_trials if item.candidate_id == args.candidate_id), None)
        print_json(run_once(config_path, args.project_command, trial=trial, overrides=parse_overrides(args.set), dry_run=args.dry_run))
        return
    if args.action == "loop":
        print_json(run_loop(config_path, args.project_command, dry_run=args.dry_run, limit=args.limit))
        return
    if args.action == "trainers":
        if args.trainers_command == "run":
            print_json(run_all_trainers(config_path, dry_run=args.dry_run))
            return
        print_json(trainer_status(config_path))
        return
    if args.action == "memory":
        if args.memory_command == "sync":
            print_json(sync_memory(runtime_root))
            return
        if args.memory_command == "search":
            print_json(search_memory(runtime_root, args.query, limit=args.limit))
            return
        print_json(memory_status(runtime_root))
        return
    if args.action == "beliefs":
        print_json(build_beliefs(repo_root, runtime_root))
        return
    if args.action == "obsidian":
        print_json(build_vault(repo_root, runtime_root))
        return
    if args.action == "collective":
        if args.collective_command == "publish":
            print_json(publish_latest(repo_root, runtime_root))
            return
        if args.collective_command == "sync-local":
            print_json(sync_local_collective(repo_root, runtime_root, label=args.label, rebuild=not args.skip_rebuild))
            return
        print_json(collective_status(repo_root, runtime_root))
        return
    if args.action == "self-edit":
        if args.self_edit_command == "propose":
            print_json(
                propose(
                    config_path,
                    args.prompt,
                    dry_run=args.dry_run,
                    command_override=args.backend_command,
                    backend_profile=args.backend_profile,
                )
            )
            return
        if args.self_edit_command == "profiles":
            print_json({"profiles": backend_profiles()})
            return
        if args.self_edit_command == "review":
            print_json(
                review_proposal(
                    config_path,
                    args.proposal_id,
                    decision=args.decision,
                    root_lesson=args.root_lesson,
                    lineage_failures=args.lineage_failure,
                    counterfactual=args.counterfactual,
                    ghost_improvement_check=args.ghost_check,
                    rollback_condition=args.rollback_condition,
                    notes=args.notes,
                )
            )
            return
        if args.self_edit_command == "apply":
            push_override = None
            if args.push and args.no_push:
                raise RuntimeError("Choose only one of --push or --no-push.")
            if args.push:
                push_override = True
            elif args.no_push:
                push_override = False
            print_json(
                apply_proposal(
                    config_path,
                    args.proposal_id,
                    git_mode_override=args.git_mode,
                    push_override=push_override,
                    branch_name_override=args.branch_name,
                    commit_message_override=args.commit_message,
                )
            )
            return
        print_json(proposal_status(config_path))
        return
    if args.action == "summary":
        print_json(ledger_summary(runtime_root))
        return


if __name__ == "__main__":
    main()
