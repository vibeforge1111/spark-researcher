"""Tests that chip hook no-output error does not expose output path."""
import pytest


def no_output_error(hook: str, output_path: str) -> RuntimeError:
    return RuntimeError(f"Chip hook `{hook}` did not produce an output file")


class TestChipsOutputPathNotExposed:
    def test_no_output_path_in_error(self):
        err = no_output_error("evaluate", "/home/user/.spark/chips/evaluate/output.json")
        assert "/home/user" not in str(err)

    def test_hook_name_in_error(self):
        err = no_output_error("suggest", "/any/path.json")
        assert "suggest" in str(err)

    def test_generic_message(self):
        err = no_output_error("evaluate", "/path")
        assert "did not produce an output file" in str(err)

    def test_is_runtime_error(self):
        err = no_output_error("packets", "/path")
        assert isinstance(err, RuntimeError)

    def test_secret_path_not_leaked(self):
        secret = "/etc/secret/output.json"
        err = no_output_error("evaluate", secret)
        assert secret not in str(err)
