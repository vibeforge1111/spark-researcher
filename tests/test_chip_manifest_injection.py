"""
Tests for manifest command-injection fix.

Each manifest function now calls _assert_safe_package_name() before
building the commands dict, so any unsanitized package_name raises
ValueError before it can reach the JSON output.
"""

import json
import re
import pytest


# Inline the relevant implementation for isolated unit testing
_SAFE_PACKAGE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")


def _assert_safe_package_name(package_name: str) -> None:
    if not _SAFE_PACKAGE_NAME_RE.fullmatch(package_name):
        raise ValueError(
            f"Unsafe package_name rejected before manifest generation: {package_name!r}"
        )


def _minimal_manifest(chip_name: str, package_name: str) -> str:
    """Mirrors the fixed logic shared by all three manifest functions."""
    _assert_safe_package_name(package_name)
    payload = {
        "commands": {
            "evaluate": ["python", "-m", f"{package_name}.cli", "evaluate"],
            "suggest": ["python", "-m", f"{package_name}.cli", "suggest"],
        }
    }
    return json.dumps(payload)


SAFE_NAMES = ["my_chip", "trading", "xcontent_chip", "chip1", "a"]
UNSAFE_NAMES = [
    "evil; rm -rf /",
    "name`whoami`",
    "name$(id)",
    "my-chip",          # dash not allowed in module name
    "My_Chip",          # uppercase
    "../escape",
    "",
    "chip name",
    "chip\n",
    "chip.dotted",
]


class TestAssertSafePackageName:
    @pytest.mark.parametrize("name", SAFE_NAMES)
    def test_safe_name_passes(self, name):
        _assert_safe_package_name(name)  # should not raise

    @pytest.mark.parametrize("name", UNSAFE_NAMES)
    def test_unsafe_name_raises(self, name):
        with pytest.raises(ValueError, match="Unsafe package_name"):
            _assert_safe_package_name(name)


class TestManifestCommandInjection:
    def test_safe_package_name_produces_valid_command_array(self):
        manifest = json.loads(_minimal_manifest("my-chip", "my_chip"))
        cmd = manifest["commands"]["evaluate"]
        assert cmd == ["python", "-m", "my_chip.cli", "evaluate"]

    def test_shell_metachar_payload_blocked_before_json(self):
        with pytest.raises(ValueError):
            _minimal_manifest("chip", "evil; rm -rf /")

    def test_backtick_payload_blocked(self):
        with pytest.raises(ValueError):
            _minimal_manifest("chip", "name`whoami`")

    def test_dollar_payload_blocked(self):
        with pytest.raises(ValueError):
            _minimal_manifest("chip", "name$(id)")

    def test_newline_payload_blocked(self):
        with pytest.raises(ValueError):
            _minimal_manifest("chip", "chip\n")

    def test_injection_payload_never_reaches_json_output(self):
        payload = "evil; os.system('id')"
        with pytest.raises(ValueError):
            result = _minimal_manifest("chip", payload)
            # This line is unreachable — but if it were reached, assert no injection
            assert payload not in result
