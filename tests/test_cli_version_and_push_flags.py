from __future__ import annotations

import pytest

from spark_researcher import __version__
from spark_researcher.cli import build_parser


def test_cli_version_is_available_without_a_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        build_parser().parse_args(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out.strip() == f"spark-researcher {__version__}"


@pytest.mark.parametrize(
    "arguments",
    [
        ["self-edit", "policy", "--push", "--no-push"],
        [
            "self-edit",
            "apply",
            "--proposal-id",
            "proposal-1",
            "--governor-decision",
            "decision.json",
            "--push",
            "--no-push",
        ],
    ],
)
def test_push_overrides_are_parser_level_mutually_exclusive(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        build_parser().parse_args(arguments)

    assert raised.value.code == 2


@pytest.mark.parametrize("flag,expected", [("--push", (True, False)), ("--no-push", (False, True))])
def test_policy_accepts_each_push_override_individually(flag: str, expected: tuple[bool, bool]) -> None:
    parsed = build_parser().parse_args(["self-edit", "policy", flag])

    assert (parsed.push, parsed.no_push) == expected
