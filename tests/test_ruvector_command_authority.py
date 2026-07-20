from __future__ import annotations

from types import SimpleNamespace

import pytest

from spark_researcher import ruvector


@pytest.mark.parametrize(
    "raw_command",
    [
        "python -c pass",
        "bash -lc true",
        "npx unrelated-package",
        "npx ruvector brain search",
    ],
)
def test_ruvector_launcher_rejects_noncanonical_command_grammars(monkeypatch, raw_command: str) -> None:
    monkeypatch.setenv("SPARK_RUVECTOR_COMMAND", raw_command)

    with pytest.raises(RuntimeError, match=r"^RuVector launcher configuration is invalid\.$") as exc_info:
        ruvector._resolve_command()

    assert raw_command not in str(exc_info.value)


@pytest.mark.parametrize(
    ("raw_command", "expected"),
    [
        ("ruvector", ["ruvector"]),
        ("/opt/spark/bin/ruvector", ["/opt/spark/bin/ruvector"]),
        ("npx ruvector", ["npx", "ruvector"]),
    ],
)
def test_ruvector_launcher_accepts_only_supported_launcher_shapes(
    monkeypatch, raw_command: str, expected: list[str]
) -> None:
    monkeypatch.setenv("SPARK_RUVECTOR_COMMAND", raw_command)

    assert ruvector._resolve_command() == expected


def test_ruvector_search_uses_parent_json_option_and_terminates_query_options(monkeypatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setenv("SPARK_RUVECTOR_COMMAND", "npx ruvector")
    monkeypatch.setenv("PI", "test-identity")
    monkeypatch.setattr(ruvector.shutil, "which", lambda executable: f"/resolved/{executable}")

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout='{"results": []}', stderr="")

    monkeypatch.setattr(ruvector.subprocess, "run", fake_run)

    result = ruvector.run_search("--category secrets")

    assert captured["command"] == [
        "/resolved/npx",
        "ruvector",
        "brain",
        "--json",
        "search",
        "--",
        "--category secrets",
    ]
    assert result["query"] == "--category secrets"
    assert result["result_format"] == "json"
