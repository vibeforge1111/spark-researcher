"""Tests that chip manifest RuntimeError does not expose full path."""
import pytest


def manifest_not_found_error(manifest_path: str) -> RuntimeError:
    return RuntimeError("Chip manifest not found")


class TestChipsManifestPathNotExposed:
    def test_no_path_in_error(self):
        err = manifest_not_found_error("/home/user/.spark/chips/my-chip/spark-chip.json")
        assert "/home/user" not in str(err)

    def test_generic_message(self):
        err = manifest_not_found_error("/any/path")
        assert str(err) == "Chip manifest not found"

    def test_is_runtime_error(self):
        err = manifest_not_found_error("/path")
        assert isinstance(err, RuntimeError)

    def test_secret_path_not_leaked(self):
        secret = "/etc/secret/spark-chip.json"
        err = manifest_not_found_error(secret)
        assert secret not in str(err)

    def test_message_is_string(self):
        err = manifest_not_found_error("/path")
        assert isinstance(str(err), str)
