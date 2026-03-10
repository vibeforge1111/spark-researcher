from __future__ import annotations

from pathlib import Path


IGNORED_PARTS = {"__pycache__", ".git", ".venv", "artifacts", "obsidian-vault", ".pytest_cache"}
IGNORED_FILE_NAMES = {"compiled.json"}


COUNTED_ROOTS = ("src", "docs", "examples")
COUNTED_FILES = ("README.md", "pyproject.toml", "AUTORESEARCH.md", "spark-researcher.project.json")


def count_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines()) if path.exists() else 0


def build_line_budget(repo_root: Path) -> dict[str, object]:
    rows = []
    total = 0
    for root_name in COUNTED_ROOTS:
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            ignored_part = any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in path.parts)
            generated_doc = path.parent.name == "beliefs"
            if path.is_file() and not ignored_part and not generated_doc and path.name not in IGNORED_FILE_NAMES:
                lines = count_lines(path)
                rows.append({"path": str(path.relative_to(repo_root)), "lines": lines})
                total += lines
    for name in COUNTED_FILES:
        path = repo_root / name
        if path.exists():
            lines = count_lines(path)
            rows.append({"path": name, "lines": lines})
            total += lines
    return {"total_lines": total, "files": rows}
