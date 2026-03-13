from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import adapter_status, execute_advisory, execution_status
from .advisory import build_advisory
from .beliefs import build_beliefs
from .candidates import append_suggestions, run_autoloop, run_continuous_autoloop, suggest_trials
from .chip_starter import init_chip, normalize_chip_name, resolve_chip_target
from .chips import chip_status, chip_validation
from .collective import absorb, collective_status, publish_latest, sync_local_collective
from .config import intent_policy, load_config, memory_policy, save_config, self_edit_policy, update_intent_policy, update_memory_policy, update_self_edit_policy
from .failures import surprise_status
from .intent import build_intent_brief
from .line_budget import build_line_budget
from .memory import memory_status, search_memory, sync_memory
from .obsidian import build_vault
from .optimizer import export_advisory_dataset, optimizer_status
from .outcomes import log_advisory_outcome, review_advisory_outcomes
from .packets import packet_status, search_packets
from .paths import resolve_config_path, resolve_runtime_root
from .presets import init_project, preset_names
from .research import execute_with_research
from .runner import ledger_summary, parse_overrides, run_loop, run_once
from .self_edit import apply_proposal, backend_profiles, proposal_status, propose, review_proposal
from .tracing import trace_status
from .trial_queue import merged_candidate_trials
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

    autoloop_parser = sub.add_parser("autoloop")
    add_config_argument(autoloop_parser)
    autoloop_parser.add_argument("--command", dest="project_command", required=True)
    autoloop_parser.add_argument("--rounds", type=int, default=3)
    autoloop_parser.add_argument("--suggest-limit", type=int, default=3)
    autoloop_parser.add_argument("--dry-run", action="store_true")
    autoloop_parser.add_argument("--no-apply-suggestions", action="store_true")
    autoloop_parser.add_argument("--continuous", action="store_true")
    autoloop_parser.add_argument("--pause-seconds", type=int, default=60)

    candidates_parser = sub.add_parser("candidates")
    candidates_sub = candidates_parser.add_subparsers(dest="candidates_command")
    candidates_suggest = candidates_sub.add_parser("suggest")
    add_config_argument(candidates_suggest)
    candidates_suggest.add_argument("--command", dest="project_command", required=True)
    candidates_suggest.add_argument("--limit", type=int, default=3)
    candidates_apply = candidates_sub.add_parser("apply")
    add_config_argument(candidates_apply)
    candidates_apply.add_argument("--command", dest="project_command", required=True)
    candidates_apply.add_argument("--limit", type=int, default=3)

    packets_parser = sub.add_parser("packets")
    packets_sub = packets_parser.add_subparsers(dest="packets_command")
    packets_status_parser = packets_sub.add_parser("status")
    add_config_argument(packets_status_parser)
    packets_search_parser = packets_sub.add_parser("search")
    add_config_argument(packets_search_parser)
    packets_search_parser.add_argument("query")
    packets_search_parser.add_argument("--limit", type=int, default=5)
    packets_search_parser.add_argument("--domain")

    advisory_parser = sub.add_parser("advisory")
    advisory_sub = advisory_parser.add_subparsers(dest="advisory_command")
    advisory_build_parser = advisory_sub.add_parser("build")
    add_config_argument(advisory_build_parser)
    advisory_build_parser.add_argument("--task", required=True)
    advisory_build_parser.add_argument("--model", choices=["claude", "codex", "openclaw", "generic"], default="generic")
    advisory_build_parser.add_argument("--limit", type=int, default=4)
    advisory_build_parser.add_argument("--domain")
    advisory_adapters_parser = advisory_sub.add_parser("adapters")
    advisory_providers_parser = advisory_sub.add_parser("providers")
    advisory_execute_parser = advisory_sub.add_parser("execute")
    add_config_argument(advisory_execute_parser)
    advisory_execute_parser.add_argument("--task", required=True)
    advisory_execute_parser.add_argument("--model", choices=["claude", "codex", "openclaw", "generic"], required=True)
    advisory_execute_parser.add_argument("--limit", type=int, default=4)
    advisory_execute_parser.add_argument("--domain")
    advisory_execute_parser.add_argument("--command", action="append")
    advisory_execute_parser.add_argument("--dry-run", action="store_true")
    advisory_execute_parser.add_argument("--no-verify", action="store_true")
    advisory_log_parser = advisory_sub.add_parser("log")
    add_config_argument(advisory_log_parser)
    advisory_log_parser.add_argument("--task", required=True)
    advisory_log_parser.add_argument("--model", required=True)
    advisory_log_parser.add_argument("--status", choices=["ok", "mixed", "fail"], required=True)
    advisory_log_parser.add_argument("--packet-id", action="append", default=[])
    advisory_log_parser.add_argument("--score", type=float)
    advisory_log_parser.add_argument("--notes", default="")
    advisory_log_parser.add_argument("--domain")
    advisory_review_parser = advisory_sub.add_parser("review")
    add_config_argument(advisory_review_parser)

    optimizer_parser = sub.add_parser("optimizer")
    optimizer_sub = optimizer_parser.add_subparsers(dest="optimizer_command")
    optimizer_sub.add_parser("status")
    optimizer_sub.add_parser("export-advisory-dataset")

    chips_parser = sub.add_parser("chips")
    chips_sub = chips_parser.add_subparsers(dest="chips_command")
    chips_init_parser = chips_sub.add_parser("init")
    chips_init_parser.add_argument("--path")
    chips_init_parser.add_argument("--chip-name")
    chips_init_parser.add_argument("--domain", required=True)
    chips_init_parser.add_argument("--metric-name", default="quality_score")
    chips_init_parser.add_argument("--goal", choices=["maximize", "minimize"], default="maximize")
    chips_init_parser.add_argument("--package-name")
    chips_init_parser.add_argument("--preset", choices=["generic", "crypto-trading", "xcontent"], default="generic")
    chips_status_parser = chips_sub.add_parser("status")
    add_config_argument(chips_status_parser)
    chips_validate_parser = chips_sub.add_parser("validate")
    add_config_argument(chips_validate_parser)

    intent_parser = sub.add_parser("intent")
    intent_sub = intent_parser.add_subparsers(dest="intent_command")
    intent_show = intent_sub.add_parser("show")
    add_config_argument(intent_show)
    intent_set = intent_sub.add_parser("set")
    add_config_argument(intent_set)
    intent_set.add_argument("--goal")
    intent_set.add_argument("--outcome")
    intent_set.add_argument("--success-criterion", action="append", default=None)
    intent_set.add_argument("--search-query", action="append", default=None)
    intent_set.add_argument("--frontier-mode", choices=["bounded", "relaxed", "open"])
    intent_set.add_argument("--resource", action="append", default=None)
    intent_set.add_argument("--notes")
    intent_clear = intent_sub.add_parser("clear")
    add_config_argument(intent_clear)

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
    memory_search.add_argument("--backend", choices=["local", "ruvector"])
    memory_status_parser = memory_sub.add_parser("status")
    add_config_argument(memory_status_parser)
    memory_status_parser.add_argument("--backend", choices=["local", "ruvector"])
    memory_policy_parser = memory_sub.add_parser("backend-policy")
    add_config_argument(memory_policy_parser)
    memory_policy_parser.add_argument("--backend", choices=["local", "ruvector"])

    failures_parser = sub.add_parser("failures")
    add_config_argument(failures_parser)
    failures_parser.add_argument("--limit", type=int, default=10)

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
    collective_absorb_parser = collective_sub.add_parser("absorb")
    add_config_argument(collective_absorb_parser)
    collective_absorb_parser.add_argument("--repo", required=True)
    collective_absorb_parser.add_argument("--limit", type=int, default=5)
    collective_absorb_parser.add_argument("--dry-run", action="store_true")
    collective_absorb_parser.add_argument("--bundle-only", action="store_true")
    collective_absorb_parser.add_argument("--merge-policy", choices=["human_review", "agent_review", "automerge"])

    self_edit_parser = sub.add_parser("self-edit")
    self_edit_sub = self_edit_parser.add_subparsers(dest="self_edit_command")
    self_edit_propose = self_edit_sub.add_parser("propose")
    add_config_argument(self_edit_propose)
    self_edit_propose.add_argument("--prompt", required=True)
    self_edit_propose.add_argument("--backend-profile")
    self_edit_propose.add_argument("--backend-command", action="append")
    self_edit_propose.add_argument("--dry-run", action="store_true")
    self_edit_profiles = self_edit_sub.add_parser("profiles")
    self_edit_policy_parser = self_edit_sub.add_parser("policy")
    add_config_argument(self_edit_policy_parser)
    self_edit_policy_parser.add_argument("--git-mode", choices=["manual", "branch", "main"])
    self_edit_policy_parser.add_argument("--push", action="store_true")
    self_edit_policy_parser.add_argument("--no-push", action="store_true")
    self_edit_policy_parser.add_argument("--branch-prefix")
    self_edit_policy_parser.add_argument("--main-branch")
    self_edit_policy_parser.add_argument("--commit-message-template")
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
    budget_parser.add_argument("--limit", type=int, default=11000)
    budget_parser.add_argument("--repo-root", default=".")

    return parser


def _handle_advisory(args: argparse.Namespace, *, config_path: Path, runtime_root: Path) -> None:
    if args.advisory_command == "adapters":
        print_json(adapter_status())
        return
    if args.advisory_command == "providers":
        print_json(execution_status())
        return
    if args.advisory_command == "execute":
        advisory = build_advisory(config_path, args.task, model=args.model, limit=args.limit, domain=args.domain)
        executor = execute_advisory if args.no_verify else execute_with_research
        print_json(
            executor(
                runtime_root,
                advisory=advisory,
                model=args.model,
                command_override=args.command,
                dry_run=args.dry_run,
            )
        )
        return
    if args.advisory_command == "log":
        print_json(
            log_advisory_outcome(
                runtime_root,
                task=args.task,
                model=args.model,
                status=args.status,
                packet_ids=args.packet_id,
                score=args.score,
                notes=args.notes,
                domain=args.domain or "generic",
            )
        )
        return
    if args.advisory_command == "review":
        print_json(review_advisory_outcomes(runtime_root))
        return
    print_json(build_advisory(config_path, args.task, model=args.model, limit=args.limit, domain=args.domain))


def _handle_intent(args: argparse.Namespace, *, config_path: Path) -> None:
    config = load_config(config_path)
    if args.intent_command == "clear":
        update_intent_policy(
            config,
            goal="",
            outcome="",
            success_criteria=[],
            search_queries=[],
            frontier_mode="relaxed",
            resource_modes=["packets", "memory", "web"],
            notes="",
        )
        save_config(config_path, config)
        print_json({"config_path": str(config_path), "intent": intent_policy(config), "brief": build_intent_brief(config_path)})
        return
    if args.intent_command == "set":
        update_intent_policy(
            config,
            goal=args.goal,
            outcome=args.outcome,
            success_criteria=args.success_criterion,
            search_queries=args.search_query,
            frontier_mode=args.frontier_mode,
            resource_modes=args.resource,
            notes=args.notes,
        )
        save_config(config_path, config)
        print_json({"config_path": str(config_path), "intent": intent_policy(config), "brief": build_intent_brief(config_path)})
        return
    print_json({"config_path": str(config_path), "intent": intent_policy(config), "brief": build_intent_brief(config_path)})


def _handle_memory(args: argparse.Namespace, *, config_path: Path, repo_root: Path, runtime_root: Path) -> None:
    config = load_config(config_path)
    selected_backend = getattr(args, "backend", None) or config.memory.backend
    if args.memory_command == "backend-policy":
        updated = args.backend is not None
        if updated:
            update_memory_policy(config, backend=args.backend)
            save_config(config_path, config)
        print_json({"config_path": str(config_path), "updated": updated, "policy": memory_policy(config)})
        return
    if args.memory_command == "sync":
        print_json(sync_memory(repo_root, runtime_root, goal=config.eval_goal, config_path=config_path))
        return
    if args.memory_command == "search":
        print_json(
            search_memory(
                repo_root,
                runtime_root,
                args.query,
                limit=args.limit,
                backend=selected_backend,
                goal=config.eval_goal,
                config_path=config_path,
            )
        )
        return
    print_json(
        memory_status(
            repo_root,
            runtime_root,
            backend=selected_backend,
            configured_backend=config.memory.backend,
            goal=config.eval_goal,
            config_path=config_path,
        )
    )


def _handle_collective(args: argparse.Namespace, *, repo_root: Path, runtime_root: Path) -> None:
    if args.collective_command == "publish":
        print_json(publish_latest(repo_root, runtime_root))
        return
    if args.collective_command == "sync-local":
        print_json(sync_local_collective(repo_root, runtime_root, label=args.label, rebuild=not args.skip_rebuild))
        return
    if args.collective_command == "absorb":
        print_json(
            absorb(
                repo_root,
                runtime_root,
                source_repo=args.repo,
                limit=args.limit,
                dry_run=args.dry_run,
                bundle_only=args.bundle_only,
                merge_policy=args.merge_policy,
            )
        )
        return
    print_json(collective_status(repo_root, runtime_root))


def _handle_self_edit(args: argparse.Namespace, *, config_path: Path) -> None:
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
    if args.self_edit_command == "policy":
        config = load_config(config_path)
        push_override = None
        if args.push and args.no_push:
            raise RuntimeError("Choose only one of --push or --no-push.")
        if args.push:
            push_override = True
        elif args.no_push:
            push_override = False
        has_updates = any(
            value is not None
            for value in (
                args.git_mode,
                push_override,
                args.branch_prefix,
                args.main_branch,
                args.commit_message_template,
            )
        )
        if has_updates:
            update_self_edit_policy(
                config,
                git_mode=args.git_mode,
                auto_push=push_override,
                branch_prefix=args.branch_prefix,
                main_branch=args.main_branch,
                commit_message_template=args.commit_message_template,
            )
            save_config(config_path, config)
        print_json({"config_path": str(config_path), "updated": has_updates, "policy": self_edit_policy(config)})
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
        config = load_config(config_path)
        trials = merged_candidate_trials(config_path, config=config)
        trial = next((item for item in trials if item.candidate_id == args.candidate_id), None)
        print_json(run_once(config_path, args.project_command, trial=trial, overrides=parse_overrides(args.set), dry_run=args.dry_run))
        return
    if args.action == "loop":
        print_json(run_loop(config_path, args.project_command, dry_run=args.dry_run, limit=args.limit))
        return
    if args.action == "autoloop":
        runner = run_continuous_autoloop if args.continuous else run_autoloop
        kwargs = {
            "rounds": args.rounds,
            "suggest_limit": args.suggest_limit,
            "dry_run": args.dry_run,
            "apply_suggestions": not args.no_apply_suggestions,
        }
        if args.continuous:
            kwargs["pause_seconds"] = args.pause_seconds
        print_json(runner(config_path, args.project_command, **kwargs))
        return
    if args.action == "candidates":
        if args.candidates_command == "apply":
            packet = suggest_trials(config_path, args.project_command, limit=args.limit)
            print_json({"suggestions": packet, "apply": append_suggestions(config_path, packet["suggestions"])})
            return
        print_json(suggest_trials(config_path, args.project_command, limit=args.limit))
        return
    if args.action == "packets":
        if args.packets_command == "search":
            print_json(search_packets(config_path, args.query, limit=args.limit, domain=args.domain))
            return
        print_json(packet_status(config_path))
        return
    if args.action == "advisory":
        _handle_advisory(args, config_path=config_path, runtime_root=runtime_root)
        return
    if args.action == "optimizer":
        if args.optimizer_command == "export-advisory-dataset":
            print_json(export_advisory_dataset(runtime_root))
            return
        print_json(optimizer_status())
        return
    if args.action == "chips":
        if args.chips_command == "init":
            chip_name = normalize_chip_name(args.domain, args.chip_name)
            target_dir = resolve_chip_target(Path(args.path), chip_name) if args.path else resolve_chip_target(None, chip_name)
            try:
                print_json(
                    init_chip(
                        target_dir,
                        chip_name=chip_name,
                        domain=args.domain,
                        metric_name=args.metric_name,
                        goal=args.goal,
                        package_name=args.package_name,
                        preset=args.preset,
                    )
                )
            except ValueError as exc:
                raise SystemExit(str(exc))
            return
        if args.chips_command == "validate":
            print_json(chip_validation(config_path))
            return
        print_json(chip_status(config_path))
        return
    if args.action == "intent":
        _handle_intent(args, config_path=config_path)
        return
    if args.action == "trainers":
        if args.trainers_command == "run":
            print_json(run_all_trainers(config_path, dry_run=args.dry_run))
            return
        print_json(trainer_status(config_path))
        return
    if args.action == "memory":
        _handle_memory(args, config_path=config_path, repo_root=repo_root, runtime_root=runtime_root)
        return
    if args.action == "failures":
        print_json(surprise_status(runtime_root, limit=args.limit))
        return
    if args.action == "beliefs":
        print_json(build_beliefs(repo_root, runtime_root))
        return
    if args.action == "obsidian":
        print_json(build_vault(repo_root, runtime_root, load_config(config_path), config_path=config_path))
        return
    if args.action == "collective":
        _handle_collective(args, repo_root=repo_root, runtime_root=runtime_root)
        return
    if args.action == "self-edit":
        _handle_self_edit(args, config_path=config_path)
        return
    if args.action == "summary":
        print_json(
            {
                "ledger": ledger_summary(runtime_root, goal=load_config(config_path).eval_goal),
                "traces": trace_status(runtime_root),
            }
        )
        return


if __name__ == "__main__":
    main()
