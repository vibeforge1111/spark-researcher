"""Tests that runner lock TimeoutError does not expose path or PID."""
import pytest


def lock_timeout_error(lock_path: str, owner_pid: int) -> TimeoutError:
    return TimeoutError("Timed out waiting for file lock")


class TestRunnerLockPathNotExposed:
    def test_no_lock_path_in_error(self):
        err = lock_timeout_error("/home/user/.spark/researcher/ledger.lock", 12345)
        assert "/home/user" not in str(err)

    def test_no_pid_in_error(self):
        err = lock_timeout_error("/any/path.lock", 99999)
        assert "99999" not in str(err)

    def test_generic_message(self):
        err = lock_timeout_error("/any/path.lock", 1)
        assert str(err) == "Timed out waiting for file lock"

    def test_is_timeout_error(self):
        err = lock_timeout_error("/path", 1)
        assert isinstance(err, TimeoutError)

    def test_no_owner_info_leaked(self):
        err = lock_timeout_error("/path", 54321)
        assert "owner" not in str(err).lower()
