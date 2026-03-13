from __future__ import annotations

from pathlib import Path

from spark_researcher import chip_starter


def test_normalize_chip_name_uses_domain_prefix_by_default() -> None:
    assert chip_starter.normalize_chip_name("marketing") == "domain-chip-marketing"


def test_normalize_chip_name_adds_prefix_for_custom_name() -> None:
    assert chip_starter.normalize_chip_name("marketing", "marketing") == "domain-chip-marketing"


def test_normalize_chip_name_preserves_existing_prefix() -> None:
    assert chip_starter.normalize_chip_name("marketing", "domain-chip-marketing") == "domain-chip-marketing"


def test_resolve_chip_target_defaults_to_desktop(monkeypatch, tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    monkeypatch.setattr(chip_starter, "_desktop_root", lambda: desktop)

    target = chip_starter.resolve_chip_target(None, "domain-chip-marketing")

    assert target == (desktop / "domain-chip-marketing").resolve()


def test_resolve_chip_target_puts_relative_paths_under_desktop(monkeypatch, tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    monkeypatch.setattr(chip_starter, "_desktop_root", lambda: desktop)

    target = chip_starter.resolve_chip_target(Path("marketing-explicit"), "domain-chip-marketing")

    assert target == (desktop / "marketing-explicit").resolve()


def test_init_chip_writes_readme_with_resolved_root(tmp_path: Path) -> None:
    chip_root = tmp_path / "domain-chip-marketing"

    result = chip_starter.init_chip(
        chip_root,
        chip_name="domain-chip-marketing",
        domain="marketing",
        metric_name="marketing_score",
    )

    readme = (chip_root / "README.md").read_text(encoding="utf-8")

    assert result["chip_root"] == str(chip_root.resolve())
    assert f"cd {chip_root.resolve()}" in readme
    assert result["chip_name"] == "domain-chip-marketing"


def test_init_chip_refuses_targets_inside_spark_repo(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "spark-researcher"
    repo_root.mkdir()
    monkeypatch.setattr(chip_starter, "_spark_repo_root", lambda: repo_root)

    blocked_target = repo_root / "domain-chip-marketing"

    try:
        chip_starter.init_chip(
            blocked_target,
            chip_name="domain-chip-marketing",
            domain="marketing",
            metric_name="marketing_score",
        )
    except ValueError as exc:
        assert "outside spark-researcher" in str(exc)
    else:
        raise AssertionError("Expected init_chip to refuse a target inside spark-researcher")
