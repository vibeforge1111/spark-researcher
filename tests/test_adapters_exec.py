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
from spark_researcher.adapters.exec import _default_command, _expand_command_template, _resolve_command, execute_advisory, execution_status
from spark_researcher.authority import ADVISORY_EXECUTE_ACTION_TYPE, ADVISORY_EXECUTE_CAPABILITY_ID, ADVISORY_EXECUTE_TOOL_NAME


def _governor_decision() -> dict:
    kernel = HarnessKernel(surface="cli")
    action = kernel.proposed_action(
        capability_id=ADVISORY_EXECUTE_CAPABILITY_ID,
        action_type=ADVISORY_EXECUTE_ACTION_TYPE,
        risk_tier="medium",
        summary="Execute a Spark Researcher advisory through a provider adapter.",
        args_path="advisory:test",
        requires_confirmation=True,
    )
    fresh_intent = evidence_ref(
        "fresh_user_intent",
        "test",
        "Fresh owner request for Researcher advisory execution.",
        confidence=1.0,
    )
    approval = evidence_ref(
        "human_confirmation",
        "test",
        "Owner approved Researcher advisory execution.",
        confidence=1.0,
    )
    envelope = kernel.create_envelope(
        selected_move="execute_action",
        intent_summary="Execute Spark Researcher advisory.",
        raw_turn_summary="Owner requested provider execution for this advisory.",
        evidence=[fresh_intent, approval],
        proposed_actions=[action],
        authority_state="executable",
        risk_tier="medium",
        confidence=1.0,
    )
    authorization = kernel.authorize(envelope, action, approval_ref=approval)
    ledger = kernel.record_tool_call(
        envelope=envelope,
        action=action,
        authorization=authorization,
        tool_name=ADVISORY_EXECUTE_TOOL_NAME,
        status="not_started",
        output_path="advisory:test",
        summary="Researcher advisory execution is authorized but not started.",
    )
    return kernel.governor_decision(
        envelope,
        authorizations=[authorization],
        tool_ledgers=[ledger],
        reply_style="compact_status",
        reply_instruction="Execute the advisory.",
    )


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

    def test_execute_advisory_times_out_with_bounded_config_and_error_trace(self) -> None:
        advisory = {"trace_id": "trace-1", "adapter_request": {"system_prompt": "system", "user_prompt": "user"}}
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp)
            with patch.dict(os.environ, {"SPARK_RESEARCHER_SUBPROCESS_TIMEOUT_SECONDS": "9"}, clear=False):
                with patch(
                    "spark_researcher.adapters.exec.subprocess.run",
                    side_effect=subprocess.TimeoutExpired(cmd=["codex"], timeout=9),
                ) as run_mock:
                    with self.assertRaisesRegex(RuntimeError, "timed out after 9 seconds"):
                        execute_advisory(
                            runtime_root,
                            advisory=advisory,
                            model="codex",
                            command_override=["codex", "exec", "--json-out", "{response_path}"],
                            dry_run=False,
                            governor_decision=_governor_decision(),
                        )
            self.assertEqual(run_mock.call_args.kwargs["timeout"], 9.0)

    def test_execute_advisory_rejects_nonfinite_timeout_before_spawn(self) -> None:
        advisory = {"trace_id": "trace-1", "adapter_request": {"system_prompt": "system", "user_prompt": "user"}}
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp)
            with patch.dict(os.environ, {"SPARK_RESEARCHER_SUBPROCESS_TIMEOUT_SECONDS": "nan"}, clear=False):
                with patch("spark_researcher.adapters.exec.subprocess.run") as run_mock:
                    with self.assertRaisesRegex(RuntimeError, "subprocess timeout configuration is invalid"):
                        execute_advisory(
                            runtime_root,
                            advisory=advisory,
                            model="codex",
                            command_override=["codex", "exec", "--json-out", "{response_path}"],
                            dry_run=False,
                            governor_decision=_governor_decision(),
                        )
            run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
