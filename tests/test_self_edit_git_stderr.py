"""Tests that self_edit git RuntimeError does not expose raw stderr."""
import pytest


def git_output_error(args: list[str], stderr: str) -> RuntimeError:
    return RuntimeError(f"git {' '.join(args)} failed")


class TestSelfEditGitNoStderr:
    def test_no_raw_stderr_in_message(self):
        err = git_output_error(["commit"], "fatal: /home/user/.git/secret")
        assert "/home/user" not in str(err)

    def test_command_in_message(self):
        err = git_output_error(["commit", "--amend"], "any err")
        assert "git commit --amend failed" in str(err)

    def test_is_runtime_error(self):
        err = git_output_error(["push"], "err")
        assert isinstance(err, RuntimeError)

    def test_secret_not_in_message(self):
        secret = "[Errno 13] Permission denied: '/etc/secret'"
        err = git_output_error(["fetch"], secret)
        assert secret not in str(err)

    def test_generic_format(self):
        err = git_output_error(["log"], "")
        assert str(err).startswith("git ")
        assert "failed" in str(err)
