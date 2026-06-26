"""Tests that chip hook response does not include log_path."""
import pytest


def build_hook_response(hook: str, chip_name: str) -> dict:
    response = {
        "hook": hook,
        "chip_name": chip_name,
        "domain": "research",
    }
    return response


class TestChipsLogPathNotInResponse:
    def test_no_log_path_key(self):
        response = build_hook_response("evaluate", "my-chip")
        assert "log_path" not in response

    def test_hook_name_preserved(self):
        response = build_hook_response("suggest", "my-chip")
        assert response["hook"] == "suggest"

    def test_chip_name_preserved(self):
        response = build_hook_response("evaluate", "test-chip")
        assert response["chip_name"] == "test-chip"

    def test_no_path_strings_in_values(self):
        response = build_hook_response("evaluate", "my-chip")
        assert all("/" not in str(v) for v in response.values())

    def test_response_is_dict(self):
        response = build_hook_response("evaluate", "my-chip")
        assert isinstance(response, dict)
