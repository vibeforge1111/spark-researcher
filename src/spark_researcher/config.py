from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MetricSpec:
    pattern: str
    kind: str = "float"


@dataclass
class CommandSpec:
    args: list[str]
    cwd: str = "."
    kind: str = "train-once"
    log_name: str = "command.log"


@dataclass
class MutationSpec:
    name: str
    file: str
    pattern: str
    template: str
    description: str = ""
    value_step: str = ""
    value_range: list[str] = field(default_factory=list)


@dataclass
class CandidateTrial:
    candidate_id: str
    candidate_summary: str = ""
    hypothesis: str = ""
    mutations: dict[str, str] = field(default_factory=dict)
    commands: list[str] = field(default_factory=list)


@dataclass
class TrainerSpec:
    name: str
    examples_path: str
    compile_command: list[str]
    min_examples: int = 20
    recompile_every: int = 10
    max_examples: int = 96


@dataclass
class SelfEditSpec:
    command: list[str] = field(default_factory=list)
    mutable_targets: list[str] = field(default_factory=list)
    prompt_preamble: str = ""
    git_mode: str = "manual"
    auto_push: bool = False
    branch_prefix: str = "self-edit/"
    main_branch: str = "main"
    commit_message_template: str = "Apply self-edit proposal {proposal_id}"


@dataclass
class MemorySpec:
    backend: str = "local"


@dataclass
class ChipSpec:
    path: str = ""
    manifest: str = "spark-chip.json"


@dataclass
class IntentSpec:
    goal: str = ""
    outcome: str = ""
    success_criteria: list[str] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)
    frontier_mode: str = "relaxed"
    resource_modes: list[str] = field(default_factory=lambda: ["packets", "memory", "web"])
    notes: str = ""


@dataclass
class GuardrailSpec:
    max_loop_iterations: int = 8
    consecutive_discard_limit: int = 3
    near_best_tolerance: float = 0.03
    require_clean_git_for_self_edit: bool = True
    require_human_approval_for_self_edit: bool = True
    blocked_command_fragments: list[str] = field(default_factory=list)


@dataclass
class ProjectConfig:
    project_name: str
    project_root: str
    eval_metric: str
    eval_goal: str
    commands: dict[str, CommandSpec]
    metrics: dict[str, MetricSpec]
    workspace_excludes: list[str] = field(default_factory=list)
    mutable_parameters: list[MutationSpec] = field(default_factory=list)
    candidate_trials: list[CandidateTrial] = field(default_factory=list)
    trainers: list[TrainerSpec] = field(default_factory=list)
    mutable_targets: list[str] = field(default_factory=list)
    memory: MemorySpec = field(default_factory=MemorySpec)
    chip: ChipSpec = field(default_factory=ChipSpec)
    intent: IntentSpec = field(default_factory=IntentSpec)
    self_edit: SelfEditSpec = field(default_factory=SelfEditSpec)
    guardrails: GuardrailSpec = field(default_factory=GuardrailSpec)


def _command_to_payload(spec: CommandSpec) -> dict[str, object]:
    return {
        "args": list(spec.args),
        "cwd": spec.cwd,
        "kind": spec.kind,
        "log_name": spec.log_name,
    }


def _metric_to_payload(spec: MetricSpec) -> dict[str, object]:
    return {
        "pattern": spec.pattern,
        "kind": spec.kind,
    }


def _candidate_to_payload(spec: CandidateTrial) -> dict[str, object]:
    return {
        "candidate_id": spec.candidate_id,
        "candidate_summary": spec.candidate_summary,
        "hypothesis": spec.hypothesis,
        "mutations": dict(spec.mutations),
        "commands": list(spec.commands),
    }


def _trainer_to_payload(spec: TrainerSpec) -> dict[str, object]:
    return {
        "name": spec.name,
        "examples_path": spec.examples_path,
        "compile_command": list(spec.compile_command),
        "min_examples": spec.min_examples,
        "recompile_every": spec.recompile_every,
        "max_examples": spec.max_examples,
    }


def config_to_payload(config: ProjectConfig) -> dict[str, object]:
    return {
        "project_name": config.project_name,
        "project_root": config.project_root,
        "eval_metric": config.eval_metric,
        "eval_goal": config.eval_goal,
        "commands": {name: _command_to_payload(spec) for name, spec in config.commands.items()},
        "metrics": {name: _metric_to_payload(spec) for name, spec in config.metrics.items()},
        "workspace_excludes": list(config.workspace_excludes),
        "mutable_parameters": [asdict(item) for item in config.mutable_parameters],
        "candidate_trials": [_candidate_to_payload(item) for item in config.candidate_trials],
        "trainers": [_trainer_to_payload(item) for item in config.trainers],
        "mutable_targets": list(config.mutable_targets),
        "memory": {
            "backend": config.memory.backend,
        },
        "chip": {
            "path": config.chip.path,
            "manifest": config.chip.manifest,
        },
        "intent": {
            "goal": config.intent.goal,
            "outcome": config.intent.outcome,
            "success_criteria": list(config.intent.success_criteria),
            "search_queries": list(config.intent.search_queries),
            "frontier_mode": config.intent.frontier_mode,
            "resource_modes": list(config.intent.resource_modes),
            "notes": config.intent.notes,
        },
        "self_edit": {
            "command": list(config.self_edit.command),
            "mutable_targets": list(config.self_edit.mutable_targets),
            "prompt_preamble": config.self_edit.prompt_preamble,
            "git_mode": config.self_edit.git_mode,
            "auto_push": config.self_edit.auto_push,
            "branch_prefix": config.self_edit.branch_prefix,
            "main_branch": config.self_edit.main_branch,
            "commit_message_template": config.self_edit.commit_message_template,
        },
        "guardrails": {
            "max_loop_iterations": config.guardrails.max_loop_iterations,
            "consecutive_discard_limit": config.guardrails.consecutive_discard_limit,
            "near_best_tolerance": config.guardrails.near_best_tolerance,
            "require_clean_git_for_self_edit": config.guardrails.require_clean_git_for_self_edit,
            "require_human_approval_for_self_edit": config.guardrails.require_human_approval_for_self_edit,
            "blocked_command_fragments": list(config.guardrails.blocked_command_fragments),
        },
    }


def save_config(path: Path, config: ProjectConfig) -> None:
    payload = config_to_payload(config)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def self_edit_policy(config: ProjectConfig) -> dict[str, object]:
    return {
        "git_mode": config.self_edit.git_mode,
        "auto_push": config.self_edit.auto_push,
        "branch_prefix": config.self_edit.branch_prefix,
        "main_branch": config.self_edit.main_branch,
        "commit_message_template": config.self_edit.commit_message_template,
        "mutable_targets": list(config.self_edit.mutable_targets),
        "backend_command": list(config.self_edit.command),
    }


def memory_policy(config: ProjectConfig) -> dict[str, object]:
    return {
        "backend": config.memory.backend,
    }


def intent_policy(config: ProjectConfig) -> dict[str, object]:
    return {
        "goal": config.intent.goal,
        "outcome": config.intent.outcome,
        "success_criteria": list(config.intent.success_criteria),
        "search_queries": list(config.intent.search_queries),
        "frontier_mode": config.intent.frontier_mode,
        "resource_modes": list(config.intent.resource_modes),
        "notes": config.intent.notes,
        "active": bool(config.intent.goal.strip() or config.intent.outcome.strip()),
    }


def update_memory_policy(config: ProjectConfig, *, backend: str | None = None) -> ProjectConfig:
    if backend is not None:
        config.memory.backend = str(backend)
    return config


def update_self_edit_policy(
    config: ProjectConfig,
    *,
    git_mode: str | None = None,
    auto_push: bool | None = None,
    branch_prefix: str | None = None,
    main_branch: str | None = None,
    commit_message_template: str | None = None,
) -> ProjectConfig:
    if git_mode is not None:
        config.self_edit.git_mode = str(git_mode)
    if auto_push is not None:
        config.self_edit.auto_push = bool(auto_push)
    if branch_prefix is not None:
        config.self_edit.branch_prefix = str(branch_prefix)
    if main_branch is not None:
        config.self_edit.main_branch = str(main_branch)
    if commit_message_template is not None:
        config.self_edit.commit_message_template = str(commit_message_template)
    return config


def update_intent_policy(
    config: ProjectConfig,
    *,
    goal: str | None = None,
    outcome: str | None = None,
    success_criteria: list[str] | None = None,
    search_queries: list[str] | None = None,
    frontier_mode: str | None = None,
    resource_modes: list[str] | None = None,
    notes: str | None = None,
) -> ProjectConfig:
    if goal is not None:
        config.intent.goal = str(goal)
    if outcome is not None:
        config.intent.outcome = str(outcome)
    if success_criteria is not None:
        config.intent.success_criteria = [str(item) for item in success_criteria]
    if search_queries is not None:
        config.intent.search_queries = [str(item) for item in search_queries]
    if frontier_mode is not None:
        config.intent.frontier_mode = str(frontier_mode)
    if resource_modes is not None:
        config.intent.resource_modes = [str(item) for item in resource_modes]
    if notes is not None:
        config.intent.notes = str(notes)
    return config


def load_config(path: Path) -> ProjectConfig:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    commands = {
        name: CommandSpec(
            args=list(spec["args"]),
            cwd=str(spec.get("cwd", ".")),
            kind=str(spec.get("kind", "train-once")),
            log_name=str(spec.get("log_name", f"{name}.log")),
        )
        for name, spec in payload["commands"].items()
    }
    metrics = {
        name: MetricSpec(pattern=str(spec["pattern"]), kind=str(spec.get("kind", "float")))
        for name, spec in payload["metrics"].items()
    }
    mutable_parameters = [
        MutationSpec(
            name=str(item["name"]),
            file=str(item["file"]),
            pattern=str(item["pattern"]),
            template=str(item["template"]),
            description=str(item.get("description", "")),
            value_step=str(item.get("value_step", "")),
            value_range=[str(part) for part in item.get("value_range", [])],
        )
        for item in payload.get("mutable_parameters", [])
    ]
    candidate_trials = [
        CandidateTrial(
            candidate_id=str(item["candidate_id"]),
            candidate_summary=str(item.get("candidate_summary", "")),
            hypothesis=str(item.get("hypothesis", "")),
            mutations={key: str(value) for key, value in item.get("mutations", {}).items()},
            commands=[str(part) for part in item.get("commands", [])],
        )
        for item in payload.get("candidate_trials", [])
    ]
    trainers = [
        TrainerSpec(
            name=str(item["name"]),
            examples_path=str(item["examples_path"]),
            compile_command=[str(part) for part in item.get("compile_command", [])],
            min_examples=int(item.get("min_examples", 20)),
            recompile_every=int(item.get("recompile_every", 10)),
            max_examples=int(item.get("max_examples", 96)),
        )
        for item in payload.get("trainers", [])
    ]
    self_edit_payload = payload.get("self_edit", {})
    memory_payload = payload.get("memory", {})
    guardrail_payload = payload.get("guardrails", {})
    chip_payload = payload.get("chip", {})
    intent_payload = payload.get("intent", {})
    return ProjectConfig(
        project_name=str(payload["project_name"]),
        project_root=str(payload.get("project_root", ".")),
        eval_metric=str(payload["eval_metric"]),
        eval_goal=str(payload.get("eval_goal", "minimize")),
        commands=commands,
        metrics=metrics,
        workspace_excludes=[str(item) for item in payload.get("workspace_excludes", [])],
        mutable_parameters=mutable_parameters,
        candidate_trials=candidate_trials,
        trainers=trainers,
        mutable_targets=[str(item) for item in payload.get("mutable_targets", [])],
        memory=MemorySpec(
            backend=str(memory_payload.get("backend", "local")),
        ),
        chip=ChipSpec(
            path=str(chip_payload.get("path", "")),
            manifest=str(chip_payload.get("manifest", "spark-chip.json")),
        ),
        intent=IntentSpec(
            goal=str(intent_payload.get("goal", "")),
            outcome=str(intent_payload.get("outcome", "")),
            success_criteria=[str(item) for item in intent_payload.get("success_criteria", [])],
            search_queries=[str(item) for item in intent_payload.get("search_queries", [])],
            frontier_mode=str(intent_payload.get("frontier_mode", "relaxed")),
            resource_modes=[str(item) for item in intent_payload.get("resource_modes", ["packets", "memory", "web"])],
            notes=str(intent_payload.get("notes", "")),
        ),
        self_edit=SelfEditSpec(
            command=[str(part) for part in self_edit_payload.get("command", [])],
            mutable_targets=[str(item) for item in self_edit_payload.get("mutable_targets", payload.get("mutable_targets", []))],
            prompt_preamble=str(self_edit_payload.get("prompt_preamble", "")),
            git_mode=str(self_edit_payload.get("git_mode", "manual")),
            auto_push=bool(self_edit_payload.get("auto_push", False)),
            branch_prefix=str(self_edit_payload.get("branch_prefix", "self-edit/")),
            main_branch=str(self_edit_payload.get("main_branch", "main")),
            commit_message_template=str(
                self_edit_payload.get("commit_message_template", "Apply self-edit proposal {proposal_id}")
            ),
        ),
        guardrails=GuardrailSpec(
            max_loop_iterations=int(guardrail_payload.get("max_loop_iterations", 8)),
            consecutive_discard_limit=int(guardrail_payload.get("consecutive_discard_limit", 3)),
            near_best_tolerance=float(guardrail_payload.get("near_best_tolerance", 0.03)),
            require_clean_git_for_self_edit=bool(guardrail_payload.get("require_clean_git_for_self_edit", True)),
            require_human_approval_for_self_edit=bool(guardrail_payload.get("require_human_approval_for_self_edit", True)),
            blocked_command_fragments=[str(item) for item in guardrail_payload.get("blocked_command_fragments", [])],
        ),
    )


def resolve_project_root(config_path: Path, config: ProjectConfig) -> Path:
    project_root = Path(config.project_root)
    if not project_root.is_absolute():
        project_root = (config_path.parent / project_root).resolve()
    return project_root


def mutation_lookup(config: ProjectConfig) -> dict[str, MutationSpec]:
    return {item.name: item for item in config.mutable_parameters}


def trial_applies_to_command(trial: CandidateTrial, command_name: str) -> bool:
    return not trial.commands or command_name in trial.commands
