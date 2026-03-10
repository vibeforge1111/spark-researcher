from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
import argparse
import re
from typing import Any

from .paths import capsule_root, ledger_path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")


def latest_metric_run(runtime_root: Path) -> dict[str, Any] | None:
    rows = read_jsonl(ledger_path(runtime_root))
    metric_rows = [row for row in rows if isinstance(row.get("metric_value"), (int, float))]
    return metric_rows[-1] if metric_rows else None


def publish_latest(repo_root: Path, runtime_root: Path) -> dict[str, Any]:
    run = latest_metric_run(runtime_root)
    if run is None:
        raise RuntimeError("No metric runs available to publish.")
    capsule_id = f"{now_stamp()}-{run.get('run_id')}"
    root = capsule_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "capsule_id": capsule_id,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "title": f"{run.get('project_name')} {run.get('candidate_id') or run.get('run_id')}",
        "summary": f"{run.get('verdict')} on {run.get('metric_name')}={run.get('metric_value')}",
        "metric_name": run.get("metric_name"),
        "metric_value": run.get("metric_value"),
        "baseline_value": run.get("baseline_value"),
        "verdict": run.get("verdict"),
        "run_id": run.get("run_id"),
        "artifact_paths": [run.get("run_dir"), run.get("log_path")],
    }
    markdown = "\n".join(
        [
            "---",
            *(f"{key}: {json.dumps(value) if isinstance(value, (dict, list)) else value}" for key, value in payload.items()),
            "export_kind: latest",
            "---",
            "",
            f"# {payload['title']}",
            "",
            payload["summary"],
            "",
            f"- metric: `{payload['metric_name']}` = `{payload['metric_value']}`",
            f"- baseline: `{payload['baseline_value']}`",
            f"- verdict: `{payload['verdict']}`",
            f"- run_id: `{payload['run_id']}`",
        ]
    )
    md_path = root / f"{capsule_id}.md"
    json_path = root / f"{capsule_id}.manifest.json"
    md_path.write_text(markdown + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"capsule_id": capsule_id, "markdown_path": str(md_path), "manifest_path": str(json_path)}


def collective_status(repo_root: Path, runtime_root: Path) -> dict[str, Any]:
    root = capsule_root(repo_root)
    sibling_collective = repo_root.parent / "autoresearch-collective"
    latest = latest_metric_run(runtime_root)
    return {
        "capsule_root": str(root),
        "capsule_count": len(list(root.glob("*.md"))) if root.exists() else 0,
        "latest_metric_run": latest.get("run_id") if latest else None,
        "collective_repo_present": sibling_collective.exists(),
        "collective_repo_path": str(sibling_collective),
    }


def _repo_sources_path(collective_root: Path) -> Path:
    return collective_root / "dashboard" / "config" / "repo-sources.local.json"


def _generated_index_path(collective_root: Path) -> Path:
    return collective_root / "dashboard" / "public" / "data" / "collective.generated.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_repo_slug(repo_root: Path) -> str:
    path = repo_root / "AUTORESEARCH.md"
    if not path.exists():
        return repo_root.name
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("repo:"):
            return line.split(":", 1)[1].strip()
    return repo_root.name


def sync_local_collective(repo_root: Path, runtime_root: Path, *, label: str | None = None, rebuild: bool = True) -> dict[str, Any]:
    collective_root = repo_root.parent / "autoresearch-collective"
    if not collective_root.exists():
        raise RuntimeError(f"Collective repo not found: {collective_root}")
    config_path = _repo_sources_path(collective_root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _load_json(config_path) if config_path.exists() else {"sources": []}
    sources = list(payload.get("sources", []))
    repo_path_text = str(repo_root).replace("\\", "/")
    entry = next((item for item in sources if str(item.get("path", "")).replace("\\", "/") == repo_path_text), None)
    if entry is None:
        entry = {"kind": "repo", "label": label or repo_root.name, "path": repo_path_text}
        sources.append(entry)
    else:
        if label:
            entry["label"] = label
    payload["sources"] = sources
    config_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    commands_run = []
    if rebuild:
        for script_name in ("build-collective-data.mjs", "build-graph-data.mjs"):
            command = ["node", f"./scripts/{script_name}"]
            process = subprocess.run(
                command,
                cwd=str(collective_root / "dashboard"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            commands_run.append(
                {
                    "command": command,
                    "returncode": process.returncode,
                    "stdout_excerpt": process.stdout[:400],
                    "stderr_excerpt": process.stderr[:400],
                }
            )
            if process.returncode != 0:
                raise RuntimeError(f"Collective rebuild failed for {script_name}: {process.stderr.strip()}")
    generated = _load_json(_generated_index_path(collective_root))
    repo_slug = _manifest_repo_slug(repo_root)
    repo_connected = any(item.get("repo") == repo_slug for item in generated.get("repoDirectory", []))
    capsule_indexed = any(item.get("repo") == repo_slug for item in generated.get("capsuleLibrary", []))
    return {
        "collective_root": str(collective_root),
        "repo_sources_path": str(config_path),
        "repo_registered": True,
        "repo_connected": repo_connected,
        "capsule_indexed": capsule_indexed,
        "commands_run": commands_run,
        "collective_status": collective_status(repo_root, runtime_root),
    }


def _run_command(
    command: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd),
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()
        message = detail or f"Command failed: {' '.join(command)}"
        raise RuntimeError(message) from error


def _git_output(repo_root: Path, *args: str) -> str:
    result = _run_command(["git", "-C", str(repo_root), *args], cwd=repo_root)
    return result.stdout.strip()


def _repo_slug_from_remote(repo_root: Path) -> str | None:
    try:
        remote = _git_output(repo_root, "remote", "get-url", "origin")
    except RuntimeError:
        return None
    match = re.search(r"github\.com[:/](?P<slug>[^/]+/[^/.]+)(?:\.git)?$", remote)
    return match.group("slug") if match else None


def _default_base_branch(repo_root: Path) -> str:
    try:
        head = _git_output(repo_root, "symbolic-ref", "refs/remotes/origin/HEAD")
        if "/" in head:
            return head.rsplit("/", 1)[-1]
    except RuntimeError:
        pass
    try:
        current = _git_output(repo_root, "branch", "--show-current")
    except RuntimeError:
        current = ""
    if current and not current.startswith("absorb/"):
        return current
    return "main"


def _parse_frontmatter(raw: str) -> dict[str, Any]:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    payload: dict[str, Any] = {}
    current_key: str | None = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("  - ") and current_key is not None:
            payload.setdefault(current_key, [])
            payload[current_key].append(line[4:].strip())
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        parsed = value.strip()
        if parsed == "":
            payload[current_key] = []
            continue
        if parsed in {"true", "false"}:
            payload[current_key] = parsed == "true"
            continue
        try:
            payload[current_key] = json.loads(parsed)
        except json.JSONDecodeError:
            payload[current_key] = parsed
    return payload


def _load_manifest(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "AUTORESEARCH.md"
    return _parse_frontmatter(path.read_text(encoding="utf-8")) if path.exists() else {}


def _load_collective_index(repo_root: Path) -> tuple[Path, dict[str, Any]]:
    collective_root = repo_root.parent / "autoresearch-collective"
    path = collective_root / "dashboard" / "public" / "data" / "collective.generated.json"
    if not path.exists():
        raise FileNotFoundError(f"Could not locate collective.generated.json at {path}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "absorb"


def _ensure_clean_worktree(repo_root: Path) -> None:
    status = _git_output(repo_root, "status", "--porcelain")
    if status.strip():
        raise RuntimeError("Absorb draft PR requires a clean git worktree in the target repo.")


def _gh_auth_ready(repo_root: Path) -> None:
    if _run_command(["gh", "--version"], cwd=repo_root, check=False).returncode != 0:
        raise RuntimeError("`gh` is required for absorb draft PR creation.")
    auth = _run_command(["gh", "auth", "status"], cwd=repo_root, check=False)
    if auth.returncode != 0:
        raise RuntimeError("GitHub CLI is not authenticated. Run `gh auth login` first.")


def _source_repo_entry(collective_data: dict[str, Any], repo: str) -> dict[str, Any] | None:
    return next((entry for entry in collective_data.get("repoDirectory", []) if entry.get("repo") == repo), None)


def _target_platform_summary(manifest: dict[str, Any]) -> str:
    platforms = manifest.get("platforms")
    if isinstance(platforms, list) and platforms:
        return ", ".join(str(item) for item in platforms)
    if isinstance(platforms, str) and platforms:
        return platforms
    return "unknown"


def _source_platform_summary(entry: dict[str, Any] | None) -> str:
    if not entry:
        return "unknown"
    platform = entry.get("platform")
    return str(platform) if platform else "unknown"


def _fit_assessment(target_platform: str, source_platform: str) -> tuple[str, str]:
    if target_platform == "unknown" or source_platform == "unknown":
        return "uncertain", "Platform fit is unknown from current repo metadata."
    if target_platform == source_platform:
        return "compatible", f"Source and target both advertise `{target_platform}`."
    if any(tag in source_platform.lower() for tag in ("cpu", "universal", "lightweight-autoresearch")):
        return "compatible", f"Source advertises broadly compatible platform `{source_platform}`."
    return "uncertain", f"Source `{source_platform}` differs from target `{target_platform}`; review manually."


def _write_absorb_review_files(
    *,
    repo_root: Path,
    stamp: str,
    source_repo: str,
    payload: dict[str, Any],
) -> dict[str, Path]:
    review_root = repo_root / ".autoresearch" / "absorbs" / f"{stamp}-{source_repo.replace('/', '--')}"
    review_root.mkdir(parents=True, exist_ok=True)

    absorbed_path = review_root / "absorbed-insights.json"
    absorbed_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    manifest = _load_manifest(repo_root)
    target_repo = _repo_slug_from_remote(repo_root) or manifest.get("repo") or repo_root.name
    target_platform = _target_platform_summary(manifest)
    source_platform = _source_platform_summary(payload.get("source_repo_entry"))
    fit_status, fit_reason = _fit_assessment(target_platform, source_platform)
    best_delta = next((entry.get("delta") for entry in payload["insights"] if entry.get("delta") is not None), None)

    plan_path = review_root / "ABSORB_PLAN.md"
    review_path = review_root / "AI_REVIEW.md"
    pr_body_path = review_root / "PR_BODY.md"

    plan_path.write_text(
        "\n".join(
            [
                f"# Absorb Plan: {source_repo}",
                "",
                "This PR is a review checkpoint for external Insights before any code transfer.",
                "",
                f"- Source repo: `{source_repo}`",
                f"- Target repo: `{target_repo}`",
                f"- Absorbed insights: `{len(payload['insights'])}`",
                f"- Best observed delta: `{best_delta}`",
                f"- System fit: `{fit_status}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    review_path.write_text(
        "\n".join(
            [
                f"# AI Review: {source_repo}",
                "",
                "- Mode: `review_only`",
                f"- System fit: `{fit_status}`",
                f"- Reason: {fit_reason}",
                "- Security: no external code is applied automatically.",
                "- Human/agent review is still required before any implementation PR.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    pr_body_path.write_text(
        "\n".join(
            [
                f"## Absorb Review: {source_repo}",
                "",
                "This PR is a review-only absorb checkpoint.",
                "",
                f"- Source repo: `{source_repo}`",
                f"- Absorbed insights: `{len(payload['insights'])}`",
                f"- System fit: `{fit_status}`",
                f"- Best observed delta: `{best_delta}`",
                "",
                "Files added:",
                "- `absorbed-insights.json`",
                "- `ABSORB_PLAN.md`",
                "- `AI_REVIEW.md`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "folder": review_root,
        "absorbed_json": absorbed_path,
        "plan": plan_path,
        "review": review_path,
        "pr_body": pr_body_path,
    }


def absorb_merge_policy(repo_root: Path) -> str:
    value = str(_load_manifest(repo_root).get("absorb_merge_policy", "human_review")).strip().lower()
    return value if value in {"human_review", "agent_review", "automerge"} else "human_review"


def absorb(
    repo_root: Path,
    runtime_root: Path,
    *,
    source_repo: str,
    limit: int = 5,
    dry_run: bool = False,
    bundle_only: bool = False,
    merge_policy: str | None = None,
) -> dict[str, Any]:
    index_path, collective_data = _load_collective_index(repo_root)
    capsule_library = collective_data.get("capsuleLibrary", [])
    matching = [entry for entry in capsule_library if entry.get("repo") == source_repo and entry.get("verdict") == "improved"]
    matching.sort(key=lambda entry: str(entry.get("createdAt") or ""), reverse=True)
    absorbed = matching[: max(limit, 0)]
    if not absorbed:
        raise RuntimeError(f"No improved Insights available to absorb from `{source_repo}`.")

    absorb_root = runtime_root / "artifacts" / "collective-absorb" / source_repo.replace("/", "--")
    absorb_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    bundle_path = absorb_root / f"{stamp}-absorb.json"
    resolved_merge_policy = merge_policy or absorb_merge_policy(repo_root)
    payload = {
        "source_repo": source_repo,
        "absorbed_count": len(absorbed),
        "limit": limit,
        "created_at": datetime.now(UTC).isoformat(),
        "collective_index_path": str(index_path),
        "output_path": str(bundle_path),
        "merge_policy": resolved_merge_policy,
        "source_repo_entry": _source_repo_entry(collective_data, source_repo),
        "insights": [
            {
                "insight_id": entry.get("id"),
                "title": entry.get("title"),
                "summary": entry.get("summary"),
                "metric_name": entry.get("metricName"),
                "metric_value": entry.get("metricValue"),
                "baseline_value": entry.get("baselineValue"),
                "delta": entry.get("delta"),
                "verdict": entry.get("verdict"),
                "artifact_url": entry.get("artifactUrl"),
                "source_links": entry.get("sourceLinks", []),
            }
            for entry in absorbed
        ],
    }
    bundle_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if bundle_only:
        return {**payload, "pr_summary": None}

    base_branch = _default_base_branch(repo_root)
    target_repo = _repo_slug_from_remote(repo_root)
    if not target_repo:
        raise RuntimeError("Could not determine target GitHub repo from the origin remote.")
    branch = f"absorb/{stamp}-{_slugify(source_repo.split('/')[-1])}"

    if dry_run:
        return {
            **payload,
            "pr_summary": {
                "mode": "dry_run",
                "base_branch": base_branch,
                "target_repo": target_repo,
                "branch": branch,
                "title": f"absorb: review {source_repo} insights",
                "merge_policy": resolved_merge_policy,
            },
        }

    _ensure_clean_worktree(repo_root)
    _gh_auth_ready(repo_root)
    review_paths = _write_absorb_review_files(repo_root=repo_root, stamp=stamp, source_repo=source_repo, payload=payload)
    rel_paths = [str(path.relative_to(repo_root)) for path in review_paths.values() if path.is_file()]
    title = f"absorb: review {source_repo} insights"

    _run_command(["git", "-C", str(repo_root), "checkout", base_branch], cwd=repo_root)
    _run_command(["git", "-C", str(repo_root), "checkout", "-b", branch], cwd=repo_root)
    _run_command(["git", "-C", str(repo_root), "add", *rel_paths], cwd=repo_root)
    _run_command(["git", "-C", str(repo_root), "commit", "-m", title], cwd=repo_root)
    _run_command(["git", "-C", str(repo_root), "push", "-u", "origin", branch], cwd=repo_root)

    create_args = [
        "gh",
        "pr",
        "create",
        "--repo",
        target_repo,
        "--base",
        base_branch,
        "--head",
        branch,
        "--title",
        title,
        "--body-file",
        str(review_paths["pr_body"]),
    ]
    if resolved_merge_policy == "human_review":
        create_args.append("--draft")
    pr = _run_command(create_args, cwd=repo_root)
    pr_url = pr.stdout.strip() or None

    auto_merge_enabled = False
    auto_merge_error = None
    if resolved_merge_policy == "automerge" and pr_url:
        merge = _run_command(
            ["gh", "pr", "merge", "--repo", target_repo, "--auto", "--squash", pr_url],
            cwd=repo_root,
            check=False,
        )
        auto_merge_enabled = merge.returncode == 0
        if merge.returncode != 0:
            auto_merge_error = (merge.stderr or merge.stdout or "").strip() or "auto merge request failed"

    return {
        **payload,
        "pr_summary": {
            "mode": (
                "draft_pr"
                if resolved_merge_policy == "human_review"
                else "review_pr"
                if resolved_merge_policy == "agent_review"
                else "auto_pr"
            ),
            "base_branch": base_branch,
            "target_repo": target_repo,
            "branch": branch,
            "title": title,
            "pr_url": pr_url,
            "merge_policy": resolved_merge_policy,
            "auto_merge_enabled": auto_merge_enabled,
            "auto_merge_error": auto_merge_error,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Spark Researcher collective bridge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--config", default="spark-researcher.project.json")
    publish_parser.add_argument("--stdout", action="store_true")

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--config", default="spark-researcher.project.json")
    status_parser.add_argument("--stdout", action="store_true")

    sync_parser = subparsers.add_parser("sync-local")
    sync_parser.add_argument("--config", default="spark-researcher.project.json")
    sync_parser.add_argument("--label")
    sync_parser.add_argument("--skip-rebuild", action="store_true")
    sync_parser.add_argument("--stdout", action="store_true")

    absorb_parser = subparsers.add_parser("absorb")
    absorb_parser.add_argument("--config", default="spark-researcher.project.json")
    absorb_parser.add_argument("--repo", required=True)
    absorb_parser.add_argument("--limit", type=int, default=5)
    absorb_parser.add_argument("--dry-run", action="store_true")
    absorb_parser.add_argument("--bundle-only", action="store_true")
    absorb_parser.add_argument("--merge-policy", choices=["human_review", "agent_review", "automerge"])
    absorb_parser.add_argument("--stdout", action="store_true")

    args = parser.parse_args(argv)
    config_path = Path(args.config).resolve()
    repo_root = config_path.parent.resolve()
    runtime_root = repo_root

    if args.command == "publish":
        payload = publish_latest(repo_root, runtime_root)
    elif args.command == "status":
        payload = collective_status(repo_root, runtime_root)
    elif args.command == "sync-local":
        payload = sync_local_collective(repo_root, runtime_root, label=args.label, rebuild=not args.skip_rebuild)
    elif args.command == "absorb":
        payload = absorb(
            repo_root,
            runtime_root,
            source_repo=args.repo,
            limit=args.limit,
            dry_run=args.dry_run,
            bundle_only=args.bundle_only,
            merge_policy=args.merge_policy,
        )
    else:
        raise ValueError(f"Unknown command: {args.command}")

    if getattr(args, "stdout", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
