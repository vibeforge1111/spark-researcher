from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spark_researcher.adapters.base import adapter_request
from spark_researcher.adapters.exec import _default_command, _expand_command_template, _resolve_command, execute_advisory, execution_status


class AdapterExecTests(unittest.TestCase):
    def test_codex_default_command_uses_wrapper_when_available(self) -> None:
        with patch("spark_researcher.adapters.exec.shutil.which", side_effect=lambda name: "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" if name == "powershell" else None):
            command = _default_command("codex")
        self.assertTrue(command)
        self.assertEqual(command[0].lower(), "powershell")
        self.assertIn("codex_frontier_wrapper.ps1", command[5])

    def test_resolve_command_prefers_env_override(self) -> None:
        with patch.dict(os.environ, {"SPARK_RESEARCHER_ADAPTER_CODEX_COMMAND": "codex exec --json-out {response_path}"}, clear=False):
            command = _resolve_command("codex")
        self.assertEqual(command[:2], ["codex", "exec"])

    def test_resolve_command_rejects_env_override_to_unknown_executable(self) -> None:
        with patch.dict(os.environ, {"SPARK_RESEARCHER_ADAPTER_CODEX_COMMAND": "powershell -NoProfile -Command Invoke-Thing"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "not allowed"):
                _resolve_command("codex")

    def test_unknown_adapter_lists_known_adapters(self) -> None:
        with self.assertRaises(RuntimeError) as error:
            adapter_request("missing", "task", {})
        message = str(error.exception)
        self.assertIn("Unknown adapter: missing", message)
        self.assertIn("claude", message)
        self.assertIn("codex", message)

    def test_resolve_command_unknown_model_lists_supported_models(self) -> None:
        with self.assertRaises(RuntimeError) as error:
            _resolve_command("nonexistent")
        message = str(error.exception)
        self.assertIn("Unsupported execution model `nonexistent`", message)
        self.assertIn("claude", message)
        self.assertIn("codex", message)

    def test_generic_adapter_is_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {"SPARK_RESEARCHER_ADAPTER_GENERIC_COMMAND": "runner --input {request_path}"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "disabled by default"):
                _resolve_command("generic")

    def test_generic_adapter_requires_explicit_executable_allowlist(self) -> None:
        env = {
            "SPARK_RESEARCHER_ENABLE_GENERIC_ADAPTER": "1",
            "SPARK_RESEARCHER_ADAPTER_ALLOWED_EXECUTABLES": "runner",
            "SPARK_RESEARCHER_ADAPTER_GENERIC_COMMAND": "runner --input {request_path}",
        }
        with patch.dict(os.environ, env, clear=False):
            command = _resolve_command("generic")
        self.assertEqual(command[:2], ["runner", "--input"])

    def test_execution_status_marks_default_codex_source(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("spark_researcher.adapters.exec.shutil.which", side_effect=lambda name: "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" if name == "powershell" else None):
                status = execution_status()
        codex = next(item for item in status["providers"] if item["model"] == "codex")
        self.assertEqual(codex["source"], "default")
        self.assertTrue(codex["configured"])

    def test_expand_command_template_rejects_unknown_placeholders(self) -> None:
        with self.assertRaisesRegex(RuntimeError, r"\{malicious_path\}"):
            _expand_command_template(
                ["codex", "exec", "--json-out", "{response_path}", "--extra", "{malicious_path}"],
                {"response_path": "response.json"},
            )

    def test_expand_command_template_allows_known_placeholders_inside_args(self) -> None:
        command = _expand_command_template(
            ["codex", "exec", "--json-out={response_path}"],
            {"response_path": "response.json"},
        )

        self.assertEqual(command, ["codex", "exec", "--json-out=response.json"])

    def test_execute_advisory_dry_run_uses_default_codex_command(self) -> None:
        advisory = {
            "trace_id": "trace-1",
            "adapter_request": {
                "system_prompt": "system",
                "user_prompt": "user",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp)
            with patch.dict(os.environ, {}, clear=True):
                with patch("spark_researcher.adapters.exec.shutil.which", side_effect=lambda name: "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" if name == "powershell" else None):
                    result = execute_advisory(runtime_root, advisory=advisory, model="codex", dry_run=True)
                    self.assertTrue(result["dry_run"])
                    self.assertEqual(Path(result["system_prompt_path"]).read_text(encoding="utf-8"), "system")
                    self.assertEqual(Path(result["user_prompt_path"]).read_text(encoding="utf-8"), "user")
                    self.assertEqual(result["command"][0].lower(), "powershell")

    def test_execute_advisory_redacts_malformed_response_raw_output(self) -> None:
        advisory = {
            "trace_id": "trace-raw",
            "adapter_request": {
                "system_prompt": "system",
                "user_prompt": "user",
            },
        }

        def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            response_path = Path(command[command.index("--out") + 1])
            response_path.write_text(
                "adapter leaked Bearer sk-live-secret-1234567890abcdef and 12345:abcdefghijklmnopqrstuvwxyz",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        env = {
            "SPARK_RESEARCHER_ENABLE_GENERIC_ADAPTER": "1",
            "SPARK_RESEARCHER_ADAPTER_ALLOWED_EXECUTABLES": "runner",
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, env, clear=False), patch(
                "spark_researcher.adapters.exec.subprocess.run",
                side_effect=fake_run,
            ):
                result = execute_advisory(
                    Path(tmp),
                    advisory=advisory,
                    model="generic",
                    command_override=["runner", "--out", "{response_path}"],
                )

        raw_response = result["response"]["raw_response"]
        self.assertIn("[redacted]", raw_response)
        self.assertNotIn("sk-live-secret-1234567890abcdef", raw_response)
        self.assertNotIn("12345:abcdefghijklmnopqrstuvwxyz", raw_response)

    def test_execute_advisory_redacts_stdout_raw_response_fallback(self) -> None:
        advisory = {
            "trace_id": "trace-stdout",
            "adapter_request": {
                "system_prompt": "system",
                "user_prompt": "user",
            },
        }
        stdout = "stdout leaked sk-client-secret-1234567890abcdef"
        env = {
            "SPARK_RESEARCHER_ENABLE_GENERIC_ADAPTER": "1",
            "SPARK_RESEARCHER_ADAPTER_ALLOWED_EXECUTABLES": "runner",
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, env, clear=False), patch(
                "spark_researcher.adapters.exec.subprocess.run",
                return_value=subprocess.CompletedProcess(["runner"], 0, stdout=stdout, stderr=""),
            ):
                result = execute_advisory(
                    Path(tmp),
                    advisory=advisory,
                    model="generic",
                    command_override=["runner", "--no-response-file"],
                )

        raw_response = result["response"]["raw_response"]
        self.assertIn("[redacted]", raw_response)
        self.assertNotIn("sk-client-secret-1234567890abcdef", raw_response)


if __name__ == "__main__":
    unittest.main()
