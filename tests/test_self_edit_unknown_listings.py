from __future__ import annotations

import pytest

from spark_researcher.self_edit import BUILTIN_BACKEND_PROFILES, _resolve_backend_profile


def test_resolve_backend_profile_unknown_name_lists_known_profiles() -> None:
    with pytest.raises(RuntimeError) as excinfo:
        _resolve_backend_profile("codez-exec")

    message = str(excinfo.value)
    assert "Unknown backend profile: codez-exec" in message
    assert "Known backend profiles:" in message
    for known in BUILTIN_BACKEND_PROFILES:
        assert known in message


def test_resolve_backend_profile_empty_input_returns_none() -> None:
    assert _resolve_backend_profile(None) is None
    assert _resolve_backend_profile("") is None
