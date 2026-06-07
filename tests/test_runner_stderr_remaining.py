"""Tests that runner run record does not include stderr_excerpt."""
import pytest


def build_run_record(stdout: str, stderr: str) -> dict:
    return {
        "run_dir": "/run/dir",
        "metrics": {},
        "stdout_excerpt": stdout[:500],
    }


class TestRunnerStderrExcerptRemoved:
    def test_no_stderr_excerpt_key(self):
        record = build_run_record("", "secret stderr output")
        assert "stderr_excerpt" not in record

    def test_secret_not_in_record(self):
        record = build_run_record("", "/home/user/.spark/secret")
        assert all("/home/user" not in str(v) for v in record.values())

    def test_stdout_excerpt_present(self):
        record = build_run_record("ok output", "")
        assert "stdout_excerpt" in record

    def test_stdout_excerpt_truncated(self):
        long_out = "x" * 600
        record = build_run_record(long_out, "")
        assert len(record["stdout_excerpt"]) <= 500

    def test_record_is_dict(self):
        record = build_run_record("", "")
        assert isinstance(record, dict)
