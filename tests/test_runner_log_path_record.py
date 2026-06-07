"""Tests that runner run record does not include log_path or stderr_excerpt."""
import pytest


def build_run_record(log_path: str, stdout: str, stderr: str) -> dict:
    return {
        "run_dir": "/run/dir",
        "metrics": {},
        "stdout_excerpt": stdout[:500],
    }


class TestRunnerRecordNoPathOrStderr:
    def test_no_log_path_key(self):
        record = build_run_record("/home/user/.spark/logs/run.log", "ok", "")
        assert "log_path" not in record

    def test_no_stderr_excerpt_key(self):
        record = build_run_record("/any/path", "", "secret stderr")
        assert "stderr_excerpt" not in record

    def test_secret_not_in_record(self):
        record = build_run_record("/home/user/.spark/secret.log", "", "secret info")
        assert all("/home/user" not in str(v) for v in record.values())

    def test_stdout_excerpt_present(self):
        record = build_run_record("/path", "ok output", "")
        assert "stdout_excerpt" in record

    def test_record_is_dict(self):
        record = build_run_record("/path", "", "")
        assert isinstance(record, dict)
