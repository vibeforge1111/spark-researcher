from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

for HARNESS_CORE_SRC in (
    Path(__file__).resolve().parents[2] / "spark-harness-core" / "src",
    Path.home() / ".spark" / "modules" / "spark-harness-core" / "source" / "src",
):
    if HARNESS_CORE_SRC.exists() and str(HARNESS_CORE_SRC) not in sys.path:
        sys.path.insert(0, str(HARNESS_CORE_SRC))
        break

from spark_harness_core import HarnessKernel, evidence_ref
from spark_researcher.adapters.base import adapter_request
from spark_researcher.adapters.exec import _default_command, _expand_command_template, _resolve_command, execute_advisory, execution_public_summary, execution_status


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

    def test_execution_status_redacts_configured_command_arguments(self) -> None:
        env = {"SPARK_RESEARCHER_ADAPTER_CODEX_COMMAND": "codex --token SECRET_VALUE --json-out {response_path}"}
        with patch.dict(os.environ, env, clear=False):
            status = execution_status()

        encoded = repr(status)
        codex = next(item for item in status["providers"] if item["model"] == "codex")
        self.assertNotIn("SECRET_VALUE", encoded)
        self.assertNotIn("command", codex)
        self.assertEqual(codex["executable"], "codex")
        self.assertEqual(codex["arg_count"], 4)

    def test_execution_public_summary_omits_provider_response_text(self) -> None:
        result = {
            "model": "codex",
            "returncode": 0,
            "status": "ok",
            "decision": "approve",
            "request_path": "/SECRET_HOME/private/request.json",
            "response_path": "/SECRET_HOME/private/response.json",
            "stdout_path": "/SECRET_HOME/private/stdout.log",
            "stderr_path": "/SECRET_HOME/private/stderr.log",
            "trace_id": "trace-1",
            "trace_path": "/SECRET_HOME/private/trace.jsonl",
            "citations": [{"title": "source"}],
            "response": {"raw_response": "SECRET_PROVIDER_SENTINEL"},
            "command": ["codex", "--token", "SECRET_COMMAND_SENTINEL"],
        }

        summary = execution_public_summary(result)
        encoded = repr(summary)
        self.assertTrue(summary["has_response"])
        self.assertEqual(summary["status"], "ok")
        self.assertEqual(summary["decision"], "approve")
        self.assertEqual(summary["citation_count"], 1)
        self.assertEqual(summary["artifacts"]["response"], {"present": True, "name": "response.json"})
        self.assertNotIn("response", {key: value for key, value in summary.items() if key != "artifacts"})
        self.assertNotIn("command", summary)
        self.assertNotIn("SECRET_PROVIDER_SENTINEL", encoded)
        self.assertNotIn("SECRET_COMMAND_SENTINEL", encoded)
        self.assertNotIn("SECRET_HOME", encoded)

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

    def test_execute_advisory_requires_governor_before_subprocess_or_request_files(self) -> None:
        advisory = {"trace_id": "trace-1", "adapter_request": {"system_prompt": "system", "user_prompt": "user"}}
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp)
            with patch("spark_researcher.adapters.exec.subprocess.run") as run_mock:
                with self.assertRaisesRegex(RuntimeError, "missing_governor_decision"):
                    execute_advisory(
                        runtime_root,
                        advisory=advisory,
                        model="codex",
                        command_override=["codex", "exec", "--json-out", "{response_path}"],
                        dry_run=False,
                    )
            run_mock.assert_not_called()
            self.assertFalse((runtime_root / "artifacts" / "advisory" / "requests").exists())

    def test_execute_advisory_allows_native_governor_authorized_subprocess(self) -> None:
        advisory = {"trace_id": "trace-1", "adapter_request": {"system_prompt": "system", "user_prompt": "user"}}
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp)
            completed = subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="provider ok", stderr="")
            with patch("spark_researcher.adapters.exec.subprocess.run", return_value=completed) as run_mock:
                result = execute_advisory(
                    runtime_root,
                    advisory=advisory,
                    model="codex",
                    command_override=["codex", "exec", "--json-out", "{response_path}"],
                    dry_run=False,
                    governor_decision=_governor_decision(),
                )
            run_mock.assert_called_once()
            self.assertEqual(result["returncode"], 0)
            self.assertEqual(result["response"], {"raw_response": "provider ok"})
            self.assertEqual(Path(result["system_prompt_path"]).read_text(encoding="utf-8"), "system")


if __name__ == "__main__":
    unittest.main()
