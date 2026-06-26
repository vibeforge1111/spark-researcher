"""Tests for SSRF filtering of extracted DuckDuckGo result URLs.

_clean_result_url unwraps the ``uddg`` redirect parameter and now runs the
unwrapped target through assert_safe_url. When the target is unsafe (private
host, missing scheme, etc.) the function must return "" so the caller never
fetches it.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from spark_researcher.research import _clean_result_url


def _ddg(target: str) -> str:
    from urllib.parse import quote

    return f"https://duckduckgo.com/l/?uddg={quote(target, safe='')}"


def test_unwrapped_private_host_url_is_rejected() -> None:
    assert _clean_result_url(_ddg("http://127.0.0.1/admin")) == ""


def test_unwrapped_localhost_url_is_rejected() -> None:
    assert _clean_result_url(_ddg("http://localhost:8080/")) == ""


def test_unwrapped_schemeless_url_is_rejected() -> None:
    # urlparse on a schemeless value yields an empty scheme -> UnsafeURL ->
    # the assert_safe_url-on-effectively-empty return path -> "".
    assert _clean_result_url(_ddg("not-a-url")) == ""


def test_unwrapped_public_url_is_preserved() -> None:
    target = "https://example.com/page"
    assert _clean_result_url(_ddg(target)) == target


def test_empty_input_returns_empty() -> None:
    assert _clean_result_url("") == ""
