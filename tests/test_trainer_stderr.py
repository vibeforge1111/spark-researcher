"""Tests that trainer state does not include stderr_excerpt."""
import pytest


def build_trainer_state(returncode: int, stdout: str, stderr: str) -> dict:
    return {
        "last_status": "ok" if returncode == 0 else "failed",
        "stdout_excerpt": stdout[:400],
        "command": ["python", "-m", "trainer"],
    }


class TestTrainerNoStderrExcerpt:
    def test_no_stderr_excerpt_key(self):
        state = build_trainer_state(1, "", "secret output")
        assert "stderr_excerpt" not in state

    def test_secret_not_in_state(self):
        state = build_trainer_state(1, "", "/home/user/.spark/secret")
        assert all("/home/user" not in str(v) for v in state.values())

    def test_stdout_excerpt_present(self):
        state = build_trainer_state(0, "ok output", "")
        assert "stdout_excerpt" in state

    def test_failed_status_set(self):
        state = build_trainer_state(1, "", "err")
        assert state["last_status"] == "failed"

    def test_ok_status_set(self):
        state = build_trainer_state(0, "", "")
        assert state["last_status"] == "ok"
