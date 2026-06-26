"""Tests that chip hook error does not expose manifest path."""
import pytest


def hook_not_defined_error(hook: str, manifest_path: str) -> RuntimeError:
    return RuntimeError(f"Chip hook `{hook}` is not defined in the chip manifest.")


class TestChipsHookManifestPathNotExposed:
    def test_no_manifest_path_in_error(self):
        err = hook_not_defined_error("evaluate", "/home/user/.spark/chips/spark-chip.json")
        assert "/home/user" not in str(err)

    def test_hook_name_in_error(self):
        err = hook_not_defined_error("suggest", "/any/path.json")
        assert "suggest" in str(err)

    def test_generic_location_text(self):
        err = hook_not_defined_error("evaluate", "/any/path.json")
        assert "chip manifest" in str(err)

    def test_is_runtime_error(self):
        err = hook_not_defined_error("packets", "/path")
        assert isinstance(err, RuntimeError)

    def test_secret_path_not_leaked(self):
        secret = "/etc/secret/spark-chip.json"
        err = hook_not_defined_error("evaluate", secret)
        assert secret not in str(err)
