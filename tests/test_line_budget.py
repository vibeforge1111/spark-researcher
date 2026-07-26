from __future__ import annotations

from pathlib import Path

from spark_researcher.line_budget import build_line_budget, count_lines


def test_count_lines_returns_zero_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "absent.txt"
    assert count_lines(missing) == 0


def test_count_lines_counts_each_line(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    assert count_lines(target) == 3


def test_build_line_budget_counts_only_recognized_roots_and_files(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "module.py").write_text("one\ntwo\n", encoding="utf-8")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("doc-line\n", encoding="utf-8")

    # Unlisted root must be ignored entirely.
    other_dir = tmp_path / "scripts"
    other_dir.mkdir()
    (other_dir / "helper.py").write_text("ignored\n", encoding="utf-8")

    # Counted top-level file.
    (tmp_path / "README.md").write_text("readme-line\n", encoding="utf-8")
    # Top-level file not on the counted list must be ignored.
    (tmp_path / "Makefile").write_text("ignored-too\n", encoding="utf-8")

    budget = build_line_budget(tmp_path)

    paths = {row["path"]: row["lines"] for row in budget["files"]}  # type: ignore[index]
    assert "src/module.py" in paths
    assert "docs/guide.md" in paths
    assert "README.md" in paths
    assert "scripts/helper.py" not in paths
    assert "Makefile" not in paths
    assert budget["total_lines"] == paths["src/module.py"] + paths["docs/guide.md"] + paths["README.md"]


def test_build_line_budget_skips_generated_and_ignored_artifacts(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.py").write_text("kept\n", encoding="utf-8")

    # __pycache__ and .git directories are ignored via IGNORED_PARTS.
    cache_dir = src_dir / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "bytecode.pyc").write_text("cached\n", encoding="utf-8")

    # Generated belief docs are skipped via the `beliefs` parent guard.
    docs_dir = tmp_path / "docs"
    beliefs_dir = docs_dir / "beliefs"
    beliefs_dir.mkdir(parents=True)
    (beliefs_dir / "belief-1.md").write_text("generated\n", encoding="utf-8")

    # compiled.json is in IGNORED_FILE_NAMES.
    (src_dir / "compiled.json").write_text("{}\n", encoding="utf-8")

    budget = build_line_budget(tmp_path)
    paths = {row["path"] for row in budget["files"]}  # type: ignore[index]

    assert "src/keep.py" in paths
    assert not any("__pycache__" in p for p in paths)
    assert not any("beliefs" in p for p in paths)
    assert "src/compiled.json" not in paths


def test_build_line_budget_handles_repo_without_counted_roots(tmp_path: Path) -> None:
    # Only a counted top-level file; no src/docs/examples directories.
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"x\"\n", encoding="utf-8")

    budget = build_line_budget(tmp_path)

    paths = [row["path"] for row in budget["files"]]  # type: ignore[index]
    assert paths == ["pyproject.toml"]
    assert budget["total_lines"] == 2
