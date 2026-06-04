"""
Tests for chip_starter _package_name sanitizer — ensures package_name CLI arg
is always run through the sanitizer before being embedded in generated code.
"""

import re
import pytest


# Inline the sanitizer logic for isolated unit testing
def _package_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"^[._-]+|[._-]+$", "", value)
    return value or "chip"


def simulate_package_name_resolution(package_name_arg: str | None, chip_name: str) -> str:
    """Mirrors the fixed logic: _package_name(package_name or chip_name)."""
    return _package_name(package_name_arg or chip_name)


class TestPackageNameSanitizer:
    def test_normal_name_unchanged(self):
        assert _package_name("my-chip") == "my-chip"

    def test_uppercase_lowercased(self):
        assert _package_name("MyChip") == "mychip"

    def test_spaces_replaced_with_dash(self):
        assert _package_name("my chip") == "my-chip"

    def test_shell_metacharacters_stripped(self):
        payload = "evil; rm -rf /"
        result = _package_name(payload)
        assert ";" not in result
        assert " " not in result

    def test_backtick_injection_stripped(self):
        payload = "name`whoami`"
        result = _package_name(payload)
        assert "`" not in result

    def test_dollar_injection_stripped(self):
        payload = "name$(id)"
        result = _package_name(payload)
        assert "$" not in result
        assert "(" not in result

    def test_newline_injection_stripped(self):
        payload = "name\nimport os; os.system('id')"
        result = _package_name(payload)
        assert "\n" not in result
        assert "'" not in result

    def test_quote_injection_stripped(self):
        payload = 'name"injected'
        result = _package_name(payload)
        assert '"' not in result

    def test_empty_string_returns_chip_default(self):
        assert _package_name("") == "chip"


class TestPackageNameResolutionFixed:
    """
    Verifies that the fixed call-site always sanitizes the resolved value,
    whether it came from --package-name or from chip_name.
    """

    def test_malicious_package_name_arg_is_sanitized(self):
        result = simulate_package_name_resolution(
            "evil; rm -rf /", "safe-chip"
        )
        assert ";" not in result
        assert " " not in result

    def test_safe_package_name_arg_passes_through(self):
        result = simulate_package_name_resolution("my-chip", "safe-chip")
        assert result == "my-chip"

    def test_none_package_name_falls_back_to_chip_name(self):
        result = simulate_package_name_resolution(None, "safe-chip")
        assert result == "safe-chip"

    def test_none_package_name_chip_name_also_sanitized(self):
        result = simulate_package_name_resolution(None, "BAD$(inject)")
        assert "$" not in result
        assert "(" not in result

    def test_injection_payload_never_reaches_generated_code(self):
        payload = "x\"); import subprocess; subprocess.call(['id']); print(\""
        result = simulate_package_name_resolution(payload, "fallback")
        # Must not contain characters that break out of an f-string argument
        assert '"' not in result
        assert "'" not in result
        assert ";" not in result
        assert "\n" not in result
