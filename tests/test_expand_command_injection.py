from __future__ import annotations

import shlex
from pathlib import Path

import pytest

from spark_researcher.self_edit import expand_command


def _expand(parts: list[str], ws: str = "/workspace", rp: str = "/req.json", lm: str = "/last.txt"):
    return expand_command(
        parts,
        workspace_root=Path(ws),
        request_path=Path(rp),
        last_message_path=Path(lm),
    )


class TestExpandCommandInjection:
    def test_normal_workspace_path_standalone_arg(self) -> None:
        cmd, env = _expand(["--cd", "{workspace}"], ws="/home/user/project")
        assert cmd == ["--cd", "/home/user/project"]
        assert env["SPARK_WORKSPACE"] == "/home/user/project"

    def test_workspace_path_with_spaces_standalone_arg(self) -> None:
        """Spaces in a standalone {workspace} arg must pass through unchanged (shell=False is safe)."""
        cmd, env = _expand(["{workspace}"], ws="/home/user/my project")
        assert cmd == ["/home/user/my project"]
        assert env["SPARK_WORKSPACE"] == "/home/user/my project"

    def test_workspace_path_with_spaces_embedded_is_quoted(self) -> None:
        """When {workspace} is embedded in a longer string, shlex.quote protects against spaces."""
        cmd, env = _expand(["run {workspace}/script.py"], ws="/home/user/my project")
        # The embedded value must be shell-quoted
        assert shlex.quote("/home/user/my project") in cmd[0]
        assert "/home/user/my project" not in cmd[0]  # raw unquoted form must not appear embedded

    def test_workspace_path_with_semicolon_embedded_does_not_inject(self) -> None:
        """; in an embedded workspace path must not allow command injection."""
        cmd, env = _expand(["bash -c 'run {workspace}'"], ws="/path;malicious")
        # The semicolon must be quoted so bash treats it as a literal char, not separator
        assert ";malicious" not in cmd[0] or shlex.quote("/path;malicious") in cmd[0]
        # The raw value must not appear unquoted when embedded
        assert "/path;malicious" not in cmd[0]

    def test_workspace_path_with_ampersand_embedded_does_not_inject(self) -> None:
        """&& in an embedded workspace path must not allow command injection."""
        cmd, env = _expand(["sh -c 'cd {workspace}'"], ws="/path&&injected")
        assert "&&injected" not in cmd[0] or shlex.quote("/path&&injected") in cmd[0]

    def test_normal_workspace_path_embedded_still_works(self) -> None:
        cmd, env = _expand(["--workdir={workspace}"], ws="/safe/path")
        assert "/safe/path" in cmd[0]

    def test_path_env_vars_are_always_populated(self) -> None:
        """subprocess must receive SPARK_WORKSPACE etc. as env vars regardless of template."""
        _, env = _expand(["spark-codex"], ws="/ws", rp="/req", lm="/lm")
        assert env["SPARK_WORKSPACE"] == "/ws"
        assert env["SPARK_REQUEST"] == "/req"
        assert env["SPARK_LAST_MESSAGE"] == "/lm"

    def test_request_path_with_spaces_standalone(self) -> None:
        cmd, env = _expand(["{request}"], rp="/home/user/my req.json")
        assert cmd == ["/home/user/my req.json"]

    def test_last_message_path_with_spaces_standalone(self) -> None:
        cmd, env = _expand(["{last_message}"], lm="/home/user/my last.txt")
        assert cmd == ["/home/user/my last.txt"]

    def test_empty_parts_returns_empty(self) -> None:
        cmd, env = _expand([])
        assert cmd == []
        assert "SPARK_WORKSPACE" in env

    def test_no_placeholder_part_unchanged(self) -> None:
        cmd, env = _expand(["--flag", "value"])
        assert cmd == ["--flag", "value"]

    def test_multiple_placeholders_in_one_part(self) -> None:
        """Multiple placeholders in one embedded arg are all quoted."""
        cmd, env = _expand(
            ["sh", "-c", "run {workspace} --req={request}"],
            ws="/ws;evil",
            rp="/req path",
        )
        # Neither raw metachar should appear unquoted in the embedded arg
        assert ";evil" not in cmd[2] or shlex.quote("/ws;evil") in cmd[2]
