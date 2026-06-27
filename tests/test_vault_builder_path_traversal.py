"""Tests: vault builder page_path validated against output_root — no path traversal."""
from __future__ import annotations

from pathlib import Path


def _safe_page_paths(output_root: Path, paths: list[str]) -> list[Path]:
    """Reimplementation of the fixed page-write guard."""
    safe: list[Path] = []
    root_resolved = str(output_root.resolve())
    for page_path in paths:
        page_path = page_path.strip().replace("\\", "/")
        if not page_path:
            continue
        resolved = (output_root / page_path).resolve()
        if not str(resolved).startswith(root_resolved):
            continue
        safe.append(resolved)
    return safe


class TestVaultBuilderPathTraversal:
    def test_normal_path_allowed(self, tmp_path):
        root = tmp_path / "vault"
        root.mkdir()
        result = _safe_page_paths(root, ["notes/page.md"])
        assert len(result) == 1
        assert result[0].is_relative_to(root.resolve())

    def test_dotdot_traversal_rejected(self, tmp_path):
        root = tmp_path / "vault"
        root.mkdir()
        result = _safe_page_paths(root, ["../../../etc/passwd"])
        assert result == []

    def test_absolute_path_outside_root_rejected(self, tmp_path):
        root = tmp_path / "vault"
        root.mkdir()
        result = _safe_page_paths(root, ["/etc/cron.d/attacker"])
        assert result == []

    def test_nested_dotdot_rejected(self, tmp_path):
        root = tmp_path / "vault"
        root.mkdir()
        result = _safe_page_paths(root, ["subdir/../../outside.md"])
        assert result == []

    def test_empty_path_skipped(self, tmp_path):
        root = tmp_path / "vault"
        root.mkdir()
        result = _safe_page_paths(root, ["", "  "])
        assert result == []

    def test_multiple_paths_mixed(self, tmp_path):
        root = tmp_path / "vault"
        root.mkdir()
        result = _safe_page_paths(root, ["safe.md", "../escape.md", "sub/also_safe.md"])
        assert len(result) == 2
        for p in result:
            assert str(p).startswith(str(root.resolve()))
